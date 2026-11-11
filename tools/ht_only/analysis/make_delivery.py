from pathlib import Path
import csv,json,math,io,subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Circle,Rectangle
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/home/lzz/ht_only_20261111');OUT=ROOT/'delivery';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False})
def load(run):
 rows=list(csv.DictReader((run/'observations/metrics.csv').open()));return {k:np.array([float(r[k]) if r[k] else np.nan for r in rows]) for k in rows[0] if k!='finish'}
old=Path('/home/lzz/pcd_test_20261110/runs/user_pcd_8dir_600s_01');new=ROOT/'runs/a_user_pcd_600s_02';a=load(old);b=load(new)
points=np.load('/home/lzz/pcd_test_20261110/source/runtime/local_map.npy');points=points[(np.abs(points[:,0])<14)&(np.abs(points[:,1])<14)&(points[:,2]<1.5)]
fig,ax=plt.subplots(figsize=(10,9));ax.scatter(points[:,0],points[:,1],s=.4,c='#cbd5e1');ax.plot(a['x'],a['y'],c='#64748b',lw=2,label=f"几何＋HT：{a['distance_m'][-1]:.2f}m");ax.plot(b['x'],b['y'],c='#ea580c',lw=2,label=f"HT独立局部判定：{b['distance_m'][-1]:.2f}m")
for data,color,name in [(a,'#64748b','旧停车点'),(b,'#ea580c','新停车点')]:ax.scatter(data['x'][-1],data['y'][-1],c=color,s=55);ax.annotate(name,(data['x'][-1],data['y'][-1]),xytext=(8,8),textcoords='offset points')
ax.add_patch(Rectangle((-13.5,-13.5),27,27,fill=False,ls='--',ec='#334155'));ax.scatter(b['x'][0],b['y'][0],c='green',s=45,label='共同起点');ax.set(xlim=(-14,14),ylim=(-14,14),aspect='equal',xlabel='地图X / m',ylabel='地图Y / m',title='用户地图：关闭CMU几何后改走另一条路线，仍被HT占用层拦停');ax.legend();ax.grid(alpha=.15);fig.tight_layout();fig.savefig(OUT/'pcd_trajectory_comparison.png',dpi=170);plt.close(fig)
fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
for d,color,label in [(a,'#64748b','历史几何＋HT'),(b,'#ea580c','本次HT独立')]:
 for ax,key in zip(axes,['distance_m','sampled_free_volume_m3','ht_age_s']):ax.plot(d['elapsed_s'],d[key],color=color,label=label,lw=1)
for ax,label in zip(axes,['实际里程 / m','采样观测自由体积 / m³','最新HT地图源龄 / s']):ax.set_ylabel(label);ax.grid(alpha=.2)
axes[0].legend();axes[2].axhline(1,c='red',ls='--');axes[2].set_xlabel('任务时间 / s');fig.suptitle('同场景、起点、速度与统计口径；单次轨迹不同，不作普遍性能排名');fig.tight_layout();fig.savefig(OUT/'pcd_progress_comparison.png',dpi=170);plt.close(fig)
r=json.loads((ROOT/'analysis/live_a_stop/TRUTH.json').read_text());fig,axes=plt.subplots(1,2,figsize=(12,6));x,y=r['pose'][:2];ob=np.array(r['occupied_cells_within_nearby_inflation']);near=points[np.linalg.norm(points[:,:2]-[x,y],axis=1)<1.2]
axes[0].scatter(near[:,0],near[:,1],s=12,c='#94a3b8',label='归档地图点云');axes[0].scatter(ob[:,0],ob[:,1],s=35,c='#dc2626',label='HT硬占用层中的邻近格点');axes[0].add_patch(Circle((x,y),.45,fill=False,ec='#0f766e',lw=2,label='有效性半径0.45m（另加栅格余量）'));axes[0].scatter(x,y,s=45,c='#0f766e');axes[0].set(xlim=(x-.8,x+.8),ylim=(y-.8,y+.8),aspect='equal',xlabel='地图X / m',ylabel='地图Y / m',title='新停车点：HT占用层将当前足迹否决');axes[0].legend(fontsize=8)
axes[1].bar(np.arange(8),r['eight_scores'],color='#0f766e');axes[1].axhline(.5,c='#dc2626',ls='--');axes[1].set(ylim=(0,1.12),xticks=np.arange(8),xticklabels=[str(45*k)+'°' for k in range(8)],ylabel='八方向网络分数',title='网络八方向均>0.96，仍被硬占用层拒绝')
fig.suptitle('完整HT输出与“只看八个网络分数”不是同一个判据');fig.text(.5,.015,'来自实际录制/旁路快照；占用不是独立动力学真值。当前CMU车体静态网格检查未见穿透。',ha='center',fontsize=10);fig.tight_layout(rect=(0,.05,1,.94));fig.savefig(OUT/'ht_internal_veto.png',dpi=170);plt.close(fig)
# A 10x labelled visualization of recorded trajectories, not a camera/RViz recording.
W,H=1100,850;BG=Image.new('RGB',(W,H),'white');draw=ImageDraw.Draw(BG);scale=23.;cx=550;cy=465
def pixel(x,y):return(cx+scale*x,cy-scale*y)
for x,y,z in points[::2]:
 u,v=pixel(x,y);draw.point((u,v),fill='#cbd5e1')
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',23);small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',18)
ffmpeg='/home/lzz/cmu_test_20261110/deps/usr/bin/ffmpeg';proc=subprocess.Popen([ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','10','-i','-','-c:v','libx264','-threads','1','-preset','fast','-pix_fmt','yuv420p',str(OUT/'pcd_recorded_comparison_10x.mp4')],stdin=subprocess.PIPE)
for second in range(601):
 im=BG.copy();d=ImageDraw.Draw(im);d.text((20,12),'用户地图｜几何＋HT 与 HT独立局部判定',font=font,fill='#0f172a');d.text((20,46),f'真实记录轨迹可视化，10倍速，非相机/RViz录像  t={second}s',font=small,fill='#475569')
 for data,color,label,row in [(a,'#64748b','历史几何＋HT',0),(b,'#ea580c','本次HT独立',1)]:
  i=min(int(np.searchsorted(data['elapsed_s'],second)),len(data['x'])-1);xy=[pixel(x,y) for x,y in zip(data['x'][:i+1:2],data['y'][:i+1:2])]
  if len(xy)>1:d.line(xy,fill=color,width=3)
  u,v=pixel(data['x'][i],data['y'][i]);d.ellipse((u-4,v-4,u+4,v+4),fill=color);d.line((u,v,u+12*math.cos(data['yaw'][i]),v-12*math.sin(data['yaw'][i])),fill=color,width=3);d.text((20,760+row*32),f'{label}：里程 {data["distance_m"][i]:.2f}m，观测体积 {data["sampled_free_volume_m3"][i]:.1f}m³，v={data["cmd_linear"][i]:.2f}m/s',font=small,fill=color)
 proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
print('figures and video saved',OUT)
