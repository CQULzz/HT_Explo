from pathlib import Path
import json,csv,math,io,subprocess,sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/home/lzz/ht_recovery_20261111');OUT=ROOT/'delivery';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False})
def load(run,limit=None):
 rows=list(csv.DictReader((run/'observations/metrics.csv').open()))
 if limit is not None:rows=[r for r in rows if float(r['elapsed_s'])<=limit]
 return {k:np.array([float(r[k]) if r[k] else np.nan for r in rows]) for k in rows[0] if k!='finish'}
old=load(Path('/home/lzz/ht_only_20261111/runs/a_indoor_600s_03'),300);a=load(ROOT/'runs/cmu_recovery_300s_01');b=load(ROOT/'runs/cmu_recovery_300s_02')
p=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/indoor/preview/pointcloud.ply')
with p.open('rb') as f:
 while f.readline().strip()!=b'end_header':pass
 points=np.frombuffer(f.read(),dtype='<f4').reshape(-1,3)[::8];points=points[points[:,2]<2]
series=[(old,'#94a3b8','历史HT独立，截取前300秒'),(a,'#0f766e','首轮300秒：含目标超时缺陷'),(b,'#ea580c','修正版300秒')]
fig,ax=plt.subplots(figsize=(12,8));ax.scatter(points[:,0],points[:,1],s=.1,c='#cbd5e1')
for d,color,label in series:ax.plot(d['x'],d['y'],c=color,lw=1.5,label=f'{label}，{d["distance_m"][-1]:.2f}m');ax.scatter(d['x'][-1],d['y'][-1],s=30,c=color)
ax.set(aspect='equal',xlabel='世界X / m',ylabel='世界Y / m',title='CMU indoor：TARE＋HT局部恢复，实测轨迹');ax.legend(fontsize=9);fig.tight_layout();fig.savefig(OUT/'trajectory_comparison.png',dpi=160);plt.close(fig)
fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
for d,color,label in series:
 for ax,key in zip(axes,['distance_m','sampled_free_volume_m3','ht_age_s']):ax.plot(d['elapsed_s'],d[key],color=color,lw=1,label=label)
for ax,label in zip(axes,['实际里程 / m','采样观测自由体积 / m³','最新HT源龄 / s']):ax.set_ylabel(label);ax.grid(alpha=.15)
axes[0].legend(fontsize=9);axes[2].axhline(1,c='red',ls='--');axes[2].set_xlabel('任务时间 / s');fig.suptitle('同场景、起点、速度与统计口径；不同轨迹的单轮结果不作普遍优劣归因');fig.tight_layout();fig.savefig(OUT/'progress_comparison.png',dpi=160);plt.close(fig)
# Offline closed-loop fixture: original recorded HT map, not live observations.
sys.path.insert(0,'/home/lzz/HT_Explo_recovery_20261111/tools/cmu_minimal');from audit_commands import decode
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
m=decode(deserialize_message(Path('/home/lzz/ht_only_20261111/analysis/live_indoor_stop/global_local.cdr').read_bytes(),GridMap));trace=list(csv.DictReader((ROOT/'analysis/fixture_trace.csv').open()));tr={k:np.array([float(r[k]) for r in trace]) for k in trace[0]};rr,cc=np.where(m['occupied']);xx=m['cx']+(m['rows']/2-rr-.5)*m['res'];yy=m['cy']+(m['cols']/2-cc-.5)*m['res']
fig,ax=plt.subplots(figsize=(9,7));ax.scatter(xx,yy,s=1,c='#fecaca',label='HT按车体膨胀的禁行位置');ax.plot(tr['x'],tr['y'],c='#0f766e',lw=2,label='新执行器连续反馈轨迹');ax.scatter(tr['x'][0],tr['y'][0],c='#ea580c',s=55,label='原停车位置');
for i in range(0,len(trace),90):ax.arrow(tr['x'][i],tr['y'][i],.1*np.cos(tr['yaw'][i]),.1*np.sin(tr['yaw'][i]),width=.006,color='#334155')
ax.set(xlim=(13.5,15.2),ylim=(7.4,9.1),aspect='equal',xlabel='地图X / m',ylabel='地图Y / m',title='旧停车现场：连续速度命令完成转向、短移和再转向');ax.legend(fontsize=9);fig.text(.5,.025,'固定记录HT地图下的CMU运动学闭环回归；位移0.868m、向原目标推进0.752m；不是新的传感器观测或接触动力学。',ha='center',fontsize=9);fig.tight_layout(rect=(0,.05,1,1));fig.savefig(OUT/'stalled_pose_execution.png',dpi=170);plt.close(fig)
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22);small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',17);ffmpeg='/home/lzz/cmu_test_20261110/deps/usr/bin/ffmpeg'
def encoder(path,w,h,fps):return subprocess.Popen([ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{w}x{h}','-r',str(fps),'-i','-','-c:v','libx264','-threads','1','-preset','fast','-pix_fmt','yuv420p',str(path)],stdin=subprocess.PIPE)
# Live experiment visualization.
fig,ax=plt.subplots(figsize=(11,7),dpi=100);ax.scatter(points[:,0],points[:,1],s=.1,c='#cbd5e1');ax.set_aspect('equal');ax.axis('off');fig.subplots_adjust(0,0,1,1);fig.canvas.draw();box=ax.get_window_extent();xlim=ax.get_xlim();ylim=ax.get_ylim();buf=io.BytesIO();fig.savefig(buf,format='png',dpi=100);plt.close(fig);buf.seek(0);base=Image.open(buf).convert('RGB')
def pixel(x,y):return(box.x0+(x-xlim[0])/(xlim[1]-xlim[0])*box.width,700-(box.y0+(y-ylim[0])/(ylim[1]-ylim[0])*box.height)+80)
proc=encoder(OUT/'recovery_300s_10x.mp4',1100,900,10)
for second in range(301):
 im=Image.new('RGB',(1100,900),'white');im.paste(base,(0,80));draw=ImageDraw.Draw(im);draw.text((20,8),'CMU indoor｜原TARE＋HT局部搜索与动作执行',font=font,fill='#0f172a');draw.text((20,40),f'实测轨迹可视化（非相机/RViz录像），10倍速  t={second}s',font=small,fill='#475569')
 for row,(d,color,label) in enumerate(series):
  i=min(int(np.searchsorted(d['elapsed_s'],second)),len(d['x'])-1);xy=[pixel(x,y) for x,y in zip(d['x'][:i+1:2],d['y'][:i+1:2])]
  if len(xy)>1:draw.line(xy,fill=color,width=3)
  u,v=pixel(d['x'][i],d['y'][i]);draw.ellipse((u-4,v-4,u+4,v+4),fill=color);draw.text((20,790+row*30),f'{label}：{d["distance_m"][i]:.2f}m，观测体积 {d["sampled_free_volume_m3"][i]:.1f}m³',font=small,fill=color)
 proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
# The frozen-scene controller trace at 1x speed.
bg=Image.new('RGB',(1000,750),'white');draw=ImageDraw.Draw(bg)
def pix(x,y):return(200+(x-13.5)/1.7*540,650-(y-7.4)/1.7*540)
for x,y in zip(xx,yy):
 if 13.5<x<15.2 and 7.4<y<9.1:draw.point(pix(x,y),fill='#fecaca')
proc=encoder(OUT/'stalled_pose_execution.mp4',1000,750,20)
for second in np.arange(0,tr['time'][-1]+.049,.05):
 i=min(int(np.searchsorted(tr['time'],second)),len(trace)-1);im=bg.copy();draw=ImageDraw.Draw(im);draw.text((20,10),'旧停车现场｜新HT动作执行器闭环回归',font=font,fill='#0f172a');draw.text((20,45),'固定原始HT地图，非新的传感器观测；1倍速',font=small,fill='#475569');xy=[pix(x,y) for x,y in zip(tr['x'][:i+1],tr['y'][:i+1])]
 if len(xy)>1:draw.line(xy,fill='#0f766e',width=4)
 u,v=pix(tr['x'][i],tr['y'][i]);draw.ellipse((u-5,v-5,u+5,v+5),fill='#ea580c');draw.line((u,v,u+25*np.cos(tr['yaw'][i]),v-25*np.sin(tr['yaw'][i])),fill='#334155',width=4);draw.text((20,690),f't={tr["time"][i]:.2f}s  v={tr["linear"][i]:.3f}m/s  w={tr["angular"][i]:.3f}rad/s',font=small,fill='#0f172a');proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
print('delivery plots/video written',OUT)
