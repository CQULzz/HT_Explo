from pathlib import Path
import csv,json,math,io,subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/home/lzz/ht_only_20261111');out=ROOT/'delivery'
def load(run):
 rows=list(csv.DictReader((run/'observations/metrics.csv').open()));return {k:np.array([float(r[k]) if r[k] else np.nan for r in rows]) for k in rows[0] if k!='finish'}
a=load(Path('/home/lzz/cmu_test_20261110/runs/ht_600s_06'));b=load(ROOT/'runs/a_indoor_600s_03');p=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/indoor/preview/pointcloud.ply')
with p.open('rb') as f:
 while f.readline().strip()!=b'end_header':pass
 points=np.frombuffer(f.read(),dtype='<f4').reshape(-1,3)[::8];points=points[points[:,2]<2]
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False})
fig,ax=plt.subplots(figsize=(10,9));ax.scatter(points[:,0],points[:,1],s=.1,c='#cbd5e1')
for d,color,label in [(a,'#64748b','历史几何＋HT'),(b,'#ea580c','本次HT独立')]:ax.plot(d['x'],d['y'],color=color,lw=1.6,label=f'{label}：{d["distance_m"][-1]:.2f}m');ax.scatter(d['x'][-1],d['y'][-1],c=color,s=35)
ax.set(aspect='equal',xlabel='世界X / m',ylabel='世界Y / m',title='CMU indoor：两种局部判定模式完整600秒记录');ax.legend();fig.tight_layout();fig.savefig(out/'indoor_trajectory_comparison.png',dpi=160);plt.close(fig)
fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
for d,color,label in [(a,'#64748b','历史几何＋HT'),(b,'#ea580c','本次HT独立')]:
 for ax,key in zip(axes,['distance_m','sampled_free_volume_m3','ht_age_s']):ax.plot(d['elapsed_s'],d[key],color=color,label=label,lw=1)
for ax,label in zip(axes,['实际里程 / m','采样观测自由体积 / m³','HT地图源龄 / s']):ax.set_ylabel(label);ax.grid(alpha=.15)
axes[0].legend();axes[2].axhline(1,c='red',ls='--');axes[2].set_xlabel('任务时间 / s');fig.suptitle('同场景、起点、速度和指标；单轮结果不作普遍优劣结论');fig.tight_layout();fig.savefig(out/'indoor_progress_comparison.png',dpi=160);plt.close(fig)
W,H=1100,850;fig,ax=plt.subplots(figsize=(11,7),dpi=100);ax.scatter(points[:,0],points[:,1],s=.1,c='#cbd5e1');ax.set_aspect('equal');ax.axis('off');fig.subplots_adjust(0,0,1,1);fig.canvas.draw();box=ax.get_window_extent();xlim=ax.get_xlim();ylim=ax.get_ylim();buf=io.BytesIO();fig.savefig(buf,format='png',dpi=100);plt.close(fig);buf.seek(0);base=Image.open(buf).convert('RGB')
def pixel(x,y):return(box.x0+(x-xlim[0])/(xlim[1]-xlim[0])*box.width,700-(box.y0+(y-ylim[0])/(ylim[1]-ylim[0])*box.height)+80)
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',23);small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',18)
proc=subprocess.Popen(['/home/lzz/cmu_test_20261110/deps/usr/bin/ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','10','-i','-','-c:v','libx264','-threads','1','-preset','fast','-pix_fmt','yuv420p',str(out/'indoor_recorded_comparison_10x.mp4')],stdin=subprocess.PIPE)
for second in range(601):
 im=Image.new('RGB',(W,H),'white');im.paste(base,(0,80));d=ImageDraw.Draw(im);d.text((20,8),'CMU indoor｜几何＋HT 与 HT独立局部判定',font=font,fill='#0f172a');d.text((20,42),f'记录轨迹可视化（非相机/RViz录像），10倍速  t={second}s',font=small,fill='#475569')
 for data,color,label,row in [(a,'#64748b','历史几何＋HT',0),(b,'#ea580c','本次HT独立',1)]:
  i=min(int(np.searchsorted(data['elapsed_s'],second)),len(data['x'])-1);xy=[pixel(x,y) for x,y in zip(data['x'][:i+1:2],data['y'][:i+1:2])]
  if len(xy)>1:d.line(xy,fill=color,width=3)
  u,v=pixel(data['x'][i],data['y'][i]);d.ellipse((u-4,v-4,u+4,v+4),fill=color);d.text((20,770+row*30),f'{label}：{data["distance_m"][i]:.2f}m，采样观测体积 {data["sampled_free_volume_m3"][i]:.1f}m³',font=small,fill=color)
 proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0;print('indoor delivery saved')
