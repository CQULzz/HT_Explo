#!/usr/bin/env python3
"""Readable closed-loop comparison, including marginal gain and motion composition."""
import argparse,csv,json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def load(spec):
 label,folder=spec.split('=',1);p=Path(folder)
 def rows(name):
  f=p/name if (p/name).exists() else p/'current'/name
  with f.open() as stream:return list(csv.DictReader(stream))
 v=rows('observation_volume.csv');m=rows('timeseries.csv');e=json.loads((p/'endurance_audit.json').read_text());s=json.loads((p/'summary.json').read_text())
 return dict(label=label,folder=str(p),t=np.array([float(x['t_s']) for x in m]),vt=np.array([float(x['time_s']) for x in v]),v=np.array([float(x['observed_free_volume_m3']) for x in v]),
  d=np.array([float(x['distance_m']) for x in m]),speed=np.array([float(x['odom_speed_mps']) for x in m]),x=np.array([float(x['x_m']) for x in m]),y=np.array([float(x['y_m']) for x in m]),e=e['external_metrics'],s=s,age=e['sampled_map_age_s'])
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',action='append',required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args();a.output.mkdir(exist_ok=True,parents=True)
 data=[load(v) for v in a.run];colors=plt.get_cmap('tab10')(np.arange(len(data))%10);plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False,'axes.spines.top':False,'axes.spines.right':False})
 fig,axes=plt.subplots(2,3,figsize=(17,9),layout='constrained');minute=np.arange(0,601,60)
 for i,(r,c) in enumerate(zip(data,colors)):
  axes[0,0].plot(r['vt']/60,r['v'],color=c,label=r['label'],lw=2);axes[0,0].annotate(f"{r['v'][-1]:.0f}",(10,r['v'][-1]),xytext=(-5,-12 if i==1 else 5),textcoords='offset points',ha='right',color=c)
  marginal=np.diff(np.interp(minute,r['vt'],r['v']));bar_width=min(.24,.8/len(data));axes[0,1].bar(np.arange(1,11)+(i-(len(data)-1)/2)*bar_width,marginal,width=bar_width*.95,color=c,label=r['label'])
  axes[0,2].plot(r['t']/60,r['d'],color=c,label=r['label'],lw=2)
  bins=np.arange(0,601,10);values=[np.mean(r['speed'][(r['t']>=lo)&(r['t']<hi)]) for lo,hi in zip(bins,bins[1:])]
  axes[1,0].plot((bins[:-1]+5)/60,values,color=c,label=r['label'],lw=1.5)
  ev=r['e'];fractions=[1-ev['fully_stopped_fraction']-ev['stationary_turn_fraction']-ev['reverse_command_fraction'],ev['reverse_command_fraction'],ev['stationary_turn_fraction'],ev['fully_stopped_fraction']];bottom=0
  for value,label,color in zip(fractions,['前进','倒车','原地转向/对齐','完全停车'],['#187e78','#718eb5','#e5ab42','#bb514f']):
   axes[1,1].bar(i,value,bottom=bottom,color=color,label=label if i==0 else None);bottom+=value
  sampled=np.interp(r['vt'],r['t'],r['d']);initial=r['v'][np.flatnonzero(r['v']>0)[0]];axes[1,2].plot(sampled,np.maximum(0,r['v']-initial),lw=2,color=c,label=r['label'])
 for ax,title,xlabel,ylabel in [(axes[0,0],'累计观测自由体积','时间 / 分钟','m³'),(axes[0,1],'每分钟新增观测','第几分钟','m³'),(axes[0,2],'实际累计里程','时间 / 分钟','m'),(axes[1,0],'平均平移速度（每10秒）','时间 / 分钟','m/s'),(axes[1,2],'扣除首个观测帧后的新增量','实际里程 / m','m³')]:
  ax.set(title=title,xlabel=xlabel,ylabel=ylabel);ax.grid(alpha=.2);ax.legend(fontsize=8)
 axes[1,1].set(title='全部控制指令的运动组成',xticks=range(len(data)),xticklabels=[r['label'] for r in data],ylim=(0,1.08),ylabel='比例');axes[1,1].legend(fontsize=8,loc='upper center')
 fig.suptitle('同车库、同运动上限、完整600秒：原TARE访问顺序与HT局部路由\n每版本一次闭环；近似观测量，不是物理覆盖真值或单项因果收益',fontsize=15)
 for ext in ['png','pdf']:fig.savefig(a.output/('tare_architecture_comparison.'+ext),dpi=160)
 plt.close(fig)
 fig,axes=plt.subplots(1,len(data),figsize=(15,6),layout='constrained');xmin=min(r['x'].min() for r in data)-3;xmax=max(r['x'].max() for r in data)+3;ymin=min(r['y'].min() for r in data)-3;ymax=max(r['y'].max() for r in data)+3
 for ax,r,c in zip(np.atleast_1d(axes),data,colors):
  ax.plot(r['x'],r['y'],color=c,lw=1.8);ax.scatter(r['x'][0],r['y'][0],marker='o',c='green',s=35);ax.scatter(r['x'][-1],r['y'][-1],marker='x',c='red',s=55)
  for sec in range(60,601,60):ax.text(np.interp(sec,r['t'],r['x']),np.interp(sec,r['t'],r['y']),str(sec//60),fontsize=8)
  ax.set(title=f"{r['label']}\n{r['s']['distance_m']:.2f}m / {r['v'][-1]:.1f}m³",xlabel='X / m',ylabel='Y / m',xlim=(xmin,xmax),ylim=(ymin,ymax));ax.set_aspect('equal');ax.grid(alpha=.2)
 fig.suptitle('同尺度实际轨迹：绿点起点，红叉终点，数字为经过的分钟\n路线分支与回访需要结合新增观测判断，里程大不一定探索收益高')
 for ext in ['png','pdf']:fig.savefig(a.output/('tare_trajectories.'+ext),dpi=160)
 plt.close(fig)
if __name__=='__main__':main()
