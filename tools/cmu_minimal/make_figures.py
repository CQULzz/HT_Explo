from pathlib import Path
import csv,json,io,subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/home/lzz/cmu_test_20261110');out=ROOT/'delivery';out.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False})
def load(name):
 rows=list(csv.DictReader((ROOT/'runs'/name/'observations/metrics.csv').open()))
 return {k:np.array([float(r[k]) if k!='finish' and r[k] else np.nan for r in rows]) for k in rows[0] if k!='finish'}
def cloud():
 p=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/indoor/preview/pointcloud.ply')
 with p.open('rb') as f:
  while f.readline().strip()!=b'end_header':pass
  return np.frombuffer(f.read(),dtype='<f4').reshape(-1,3)
a=load('native_600s_02');b=load('ht_600s_06');points=cloud();points=points[::6];points=points[points[:,2]<2.]
fig,ax=plt.subplots(figsize=(12,8));ax.scatter(points[:,0],points[:,1],s=.08,c='#cbd5e1',rasterized=True)
ax.plot(a['x'],a['y'],c='#64748b',lw=1.5,alpha=.65,label=f"原 TARE：{a['elapsed_s'][-1]:.0f}s，{a['distance_m'][-1]:.1f}m（按用户要求结束基线）")
segments=np.stack([np.c_[b['x'][:-1],b['y'][:-1]],np.c_[b['x'][1:],b['y'][1:]]],axis=1)
line=LineCollection(segments,cmap='viridis',linewidth=2.5);line.set_array(b['elapsed_s'][:-1]);ax.add_collection(line);fig.colorbar(line,ax=ax,label='八方向版运行时间（秒）')
ax.scatter(b['x'][0],b['y'][0],c='green',s=55,label='起点');ax.scatter(b['x'][-1],b['y'][-1],c='red',s=55,label='八方向版终点')
ax.set(aspect='equal',xlabel='世界 X / m',ylabel='世界 Y / m',title='CMU 官方室内场景：真实仿真轨迹记录');ax.legend(loc='upper right');fig.tight_layout();fig.savefig(out/'trajectory.png',dpi=180);plt.close(fig)
fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
axes[0].plot(b['elapsed_s'],b['distance_m'],c='#0f766e');axes[0].set_ylabel('实际积分里程 / m')
axes[1].plot(b['elapsed_s'],b['sampled_free_volume_m3'],c='#2563eb');axes[1].set_ylabel('采样射线自由体素并集 / m³')
axes[2].plot(b['elapsed_s'],b['ht_age_s'],c='#6d28d9',lw=.8,label='收到的最新 HT 源龄');axes[2].axhline(1,c='red',ls='--',label='1 秒门限');axes[2].set_ylabel('源龄 / s');axes[2].set_xlabel('任务时间 / s');axes[2].legend()
for ax in axes:ax.grid(alpha=.2)
fig.suptitle('八方向版完整运行记录（观测体积为统一采样指标，不是真值）');fig.tight_layout();fig.savefig(out/'ht_progress.png',dpi=180);plt.close(fig)
audit=json.loads((ROOT/'runs/ht_600s_06/COMMAND_AUDIT.json').read_text());examples=[e for e in audit['examples'] if 'recorded_eight_scores' in e]
if examples:
 fig,axes=plt.subplots(min(3,len(examples)),1,figsize=(10,8),squeeze=False)
 for ax,e in zip(axes[:,0],examples[:3]):
  bars=ax.bar(np.arange(8),e['recorded_eight_scores'],color=['#dc2626' if i==e['channel'] else '#0d9488' for i in range(8)])
  ax.axhline(.5,c='black',ls='--');ax.set_ylim(0,1.05);ax.set_xticks(np.arange(8),['0°','45°','90°','135°','180°','225°','270°','315°']);ax.set_ylabel('模型通过概率')
  ax.set_title(f"实际候选查询 ({e['x']:.2f}, {e['y']:.2f})，车头 {np.degrees(e['yaw']):.1f}°：方向{e['channel']}={e['score']:.3f} 被拒绝，最佳方向={e['best_direction_score']:.3f}")
 fig.suptitle('约束生效证据：同位置有高分方向，当前车头方向仍被拒绝');fig.tight_layout();fig.savefig(out/'direction_effect.png',dpi=180);plt.close(fig)
print('figures saved',out)
# Video is a labelled visualization of recorded data, not synthesized RViz footage.
fig,ax=plt.subplots(figsize=(10,7),dpi=100);ax.scatter(points[:,0],points[:,1],s=.1,c='#cbd5e1');ax.set_aspect('equal');ax.axis('off');fig.subplots_adjust(0,0,1,1)
xlim=ax.get_xlim();ylim=ax.get_ylim();buf=io.BytesIO();fig.savefig(buf,format='png',dpi=100);plt.close(fig);buf.seek(0);base=Image.open(buf).convert('RGB')
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22);small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',17)
# Axes aspect adjustment can add margins; use its actual pixel extent.
fig,ax=plt.subplots(figsize=(10,7),dpi=100);ax.set(xlim=xlim,ylim=ylim,aspect='equal');fig.subplots_adjust(0,0,1,1);fig.canvas.draw();box=ax.get_window_extent();plt.close(fig)
def pixel(x,y):return (box.x0+(x-xlim[0])/(xlim[1]-xlim[0])*box.width,700-(box.y0+(y-ylim[0])/(ylim[1]-ylim[0])*box.height))
ffmpeg='/home/lzz/cmu_test_20261110/deps/usr/bin/ffmpeg'
cmd=[ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1000x800','-r','10','-i','-','-c:v','libx264','-threads','1','-preset','fast','-pix_fmt','yuv420p',str(out/'ht_recorded_trajectory_10x.mp4')]
process=subprocess.Popen(cmd,stdin=subprocess.PIPE)
for second in range(int(b['elapsed_s'][-1])+1):
 i=min(int(np.searchsorted(b['elapsed_s'],second)),len(b['x'])-1);image=Image.new('RGB',(1000,800),'white');image.paste(base,(0,90));draw=ImageDraw.Draw(image)
 draw.text((22,10),'CMU 室内仿真｜原 TARE + 八方向通过性',font=font,fill='#0f172a')
 draw.text((22,43),f"记录轨迹回放（10倍速，非RViz视频）  t={b['elapsed_s'][i]:.1f}s  里程={b['distance_m'][i]:.1f}m",font=small,fill='#334155')
 coords=[(u,v+90) for u,v in [pixel(x,y) for x,y in zip(b['x'][:i+1:2],b['y'][:i+1:2])]]
 if len(coords)>1:draw.line(coords,fill='#0d9488',width=3)
 x,y=pixel(b['x'][i],b['y'][i]);y+=90;tip=(x+15*np.cos(b['yaw'][i]),y-15*np.sin(b['yaw'][i]));draw.ellipse((x-4,y-4,x+4,y+4),fill='#dc2626');draw.line((x,y,*tip),fill='#dc2626',width=3)
 draw.text((22,765),f"采样观测体积={b['sampled_free_volume_m3'][i]:.1f}m³  v={b['cmd_linear'][i]:.2f}m/s  ω={b['cmd_angular'][i]:.2f}rad/s",font=small,fill='#0f172a');process.stdin.write(image.tobytes())
process.stdin.close();code=process.wait();assert code==0
print('video saved')
