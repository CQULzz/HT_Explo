#!/usr/bin/env python3
"""Plot recorded Garage diagnostics for the illustrated meeting deck."""
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import binary_dilation

HERE=Path(__file__).resolve().parent
OUT=HERE/'diagnostic_assets';OUT.mkdir(exist_ok=True)
RESULTS=HERE/'scheduled_results'
plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False,'font.size':12})
RUNS=[('原版 TARE（10:10）','2026-10-12_10-10-47/original','#2876bb'),
      ('旧 HT＋XYθ（10:10）','2026-10-12_10-10-47/current','#d07535'),
      ('历史融合（13:36）','2026-10-12_13-36-45/current','#8b69aa'),
      ('历史＋独立回调（13:43）','history_executor_2026-10-12_13-43-58/current','#999999'),
      ('历史＋回调＋前瞻修正（13:47）','history_lookahead_2026-10-12_13-47-51/current','#009b91'),
      ('停滞复现（14:00）','stop_ht_2026-10-12_14-00-05/current','#bc4545')]
data=[]
for label,path,color in RUNS:
    root=RESULTS/path
    rows=list(csv.DictReader((root/'timeseries.csv').open()))
    data.append((label,color,rows,json.loads((root/'summary.json').read_text())))

def save(fig,name):
    fig.savefig(OUT/name,dpi=180,bbox_inches='tight');plt.close(fig)

fig,ax=plt.subplots(figsize=(12,5.5),constrained_layout=True)
for label,color,rows,_ in data:
    rows=[r for r in rows if float(r['t_s'])<=90.1]
    ax.plot([float(r['t_s']) for r in rows],[float(r['distance_m']) for r in rows],label=label,color=color,lw=2.4)
ax.set(xlabel='记录开始后的时间（s）',ylabel='累计行驶距离（m）',title='相同前 90 秒窗口：累计里程对照')
ax.legend(ncol=2,fontsize=10);ax.grid(alpha=.2)
save(fig,'distance_90s.png')

fig,axes=plt.subplots(1,3,figsize=(14,5),constrained_layout=True)
for ax,index in zip(axes,[1,4,5]):
    label,color,rows,summary=data[index]
    ax.plot([float(r['x_m']) for r in rows],[float(r['y_m']) for r in rows],color=color,lw=2)
    ax.scatter(float(rows[0]['x_m']),float(rows[0]['y_m']),s=70,c='#009b91',label='起点')
    ax.scatter(float(rows[-1]['x_m']),float(rows[-1]['y_m']),s=90,c='#bc4545',marker='X',label='停滞点')
    ax.set(title=f'{label}\n{summary["duration_s"]:.0f} s / {summary["distance_m"]:.2f} m',xlabel='Map X（m）',ylabel='Map Y（m）',xlim=(-4,5),ylim=(2,16))
    ax.set_aspect('equal');ax.grid(alpha=.2);ax.legend(fontsize=9)
save(fig,'trajectories.png')

fig,axes=plt.subplots(3,1,figsize=(12,7),sharex=True,constrained_layout=True)
label,color,rows,summary=data[-1]
t=np.array([float(r['t_s']) for r in rows])
axes[0].plot(t,[float(r['distance_m']) for r in rows],color='#009b91',lw=2);axes[0].set_ylabel('累计里程（m）')
axes[1].plot(t,[float(r['cmd_speed_mps']) for r in rows],label='线速度指令',color='#2876bb');axes[1].set_ylabel('指令速度（m/s）')
axes[2].plot(t,[float(r['ht_map_age_s']) if r['ht_map_age_s'] else np.nan for r in rows],color='#d07535')
axes[2].axhline(3,color='#bc4545',ls='--',label='3 s 新鲜度阈值');axes[2].legend();axes[2].set(ylabel='外部地图年龄（s）',xlabel='记录时间（s）',ylim=(0,3.5))
for ax in axes:ax.grid(alpha=.2)
fig.suptitle('14:00 停滞复现：里程、运动指令与 HT 地图更新')
save(fig,'stop_timeline.png')

fig,axes=plt.subplots(1,2,figsize=(12,5.5),constrained_layout=True)
names=['历史融合','＋独立回调','＋前瞻修正','停滞复现']
summaries=[data[i][3] for i in [2,3,4,5]]
axes[0].bar(names,[s['ht_status_callbacks'].get('HT_MAP_STALE',0) for s in summaries],color='#d07535')
axes[0].set(title='内部地图过期状态次数',ylabel='状态回调次数')
axes[1].bar(names,[100*s['zero_cmd_fraction'] for s in summaries],color='#2876bb')
axes[1].set(title='零速指令占比',ylabel='%',ylim=(0,100))
for ax in axes:ax.tick_params(axis='x',labelrotation=15);ax.grid(axis='y',alpha=.2)
fig.suptitle('故障定位复测（90/120 s；单次运行，不能作统计归因）')
save(fig,'diagnostic_bars.png')

stop=RESULTS/RUNS[-1][1]
with np.load(stop/'stopped_ht.npz') as d:
    p=d['probabilities'];valid=d['valid'].astype(bool);center=d['center'];res=float(d['resolution']);robot=d['robot']
n,m=valid.shape
extent=[center[0]-n*res/2,center[0]+n*res/2,center[1]-m*res/2,center[1]+m*res/2]
radius=int(np.ceil(.6/res)+1);dx,dy=np.mgrid[-radius:radius+1,-radius:radius+1]
kernel=np.hypot(dx*res,dy*res)<=.6+np.sqrt(2)*res
unknown=binary_dilation(~valid,structure=kernel,border_value=1)
gates=np.stack([np.where(binary_dilation(valid&(layer<.5),structure=kernel),0,np.where(unknown,1,2)) for layer in p])
from matplotlib.colors import ListedColormap
from matplotlib.patches import Circle
for kind in ['probability','gate']:
    for first in [0,4]:
        fig,axes=plt.subplots(1,4,figsize=(16,4.6),constrained_layout=True)
        for k,ax in enumerate(axes,first):
            plane=np.where(valid,p[k],np.nan) if kind=='probability' else gates[k]
            cmap=plt.get_cmap('RdYlGn').copy();cmap.set_bad('#bfc3c6')
            im=ax.imshow(plane[::-1,::-1].T,origin='lower',extent=extent,interpolation='nearest',
                         cmap=cmap if kind=='probability' else ListedColormap(['#c9453f','#bfc3c6','#4b985a']),vmin=0,vmax=1 if kind=='probability' else 2)
            ax.add_patch(Circle(robot[:2],.6,fill=False,color='#1457c4',lw=1.7))
            ax.arrow(*robot[:2],.7*np.cos(robot[2]),.7*np.sin(robot[2]),head_width=.15,color='#1457c4')
            ax.set(title=f'θ = {45*k}°',xlabel='Map X（m）',ylabel='Map Y（m）');ax.grid(alpha=.15)
        if kind=='probability':fig.colorbar(im,ax=axes,shrink=.8,label='HT 可通过概率')
        save(fig,f'ht_{kind}_{first}.png')

fig,ax=plt.subplots(figsize=(7,6),constrained_layout=True)
im=ax.imshow(np.ptp(p,axis=0)[::-1,::-1].T,extent=extent,origin='lower',cmap='magma',vmin=0,vmax=1,interpolation='nearest')
ax.plot(*robot[:2],'o',color='cyan');ax.set(xlabel='Map X（m）',ylabel='Map Y（m）',title='方向差异：max T − min T')
fig.colorbar(im,ax=ax,label='八方向概率差');save(fig,'direction_difference.png')
print(OUT)
