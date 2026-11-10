from pathlib import Path
import json,csv,io,subprocess,math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection,PolyCollection
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/home/lzz/pcd_test_20261110');OUT=ROOT/'delivery';RUN=ROOT/'runs/user_pcd_8dir_600s_01'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False})
rows=list(csv.DictReader((RUN/'observations/metrics.csv').open()));d={k:np.array([float(r[k]) if r[k] else np.nan for r in rows]) for k in rows[0] if k!='finish'}
mesh=np.load(ROOT/'source/runtime/scene_meshes.npz');source=np.load(ROOT/'source/runtime/local_map.npy');points=source[(abs(source[:,0])<=15)&(abs(source[:,1])<=15)&(source[:,2]<3)]
snapshot=json.loads((OUT/'STATIONARY_SNAPSHOT.json').read_text());probe=json.loads((OUT/'STATIC_RECOVERY_PROBE.json').read_text())
start=json.loads((RUN/'observations/START.json').read_text())['clock'];finish=json.loads((RUN/'observations/SUMMARY.json').read_text())
last_motion=float(d['elapsed_s'][np.where(d['distance_m']<d['distance_m'][-1]-.01)[0][-1]])
events=[json.loads(line) for line in (RUN/'observations/events.jsonl').read_text().splitlines()]
last={};distinct=[]
for e in events:
 if e['time']<start:continue
 if e['kind'] in ['/ht_minimal/localPlanner','/ht_minimal/pathFollower','waypoint']:last[e['kind']]=e['data']
 if e['kind']=='/ht_minimal/path_rejection' and e['data']['score']<.5<=e['data']['best_direction_score']:distinct.append(e['data'])
analysis={'summary':finish,'last_observed_motion_elapsed_s_approx':last_motion,'distance_during_last_30s_m':float(d['distance_m'][-1]-np.interp(d['elapsed_s'][-1]-30,d['elapsed_s'],d['distance_m'])),
 'stationary_duration_s_approx':float(d['elapsed_s'][-1]-last_motion),'latest_diagnostics':last,'direction_distinct_rejection_records':len(distinct),
 'representative_stationary_rejection':next((e for e in distinct if e['time']-start>100),distinct[-1] if distinct else None),
 'source_map_scope':'56849 recorded XYZ points recovered as NPY, original standalone PCD absent; archived 30x30m meshes used. Original full array extends beyond mesh crop.',
 'interpretation':'Run recorded fully but sustained navigation did not pass: current pose can pass while goal-directed primitive paths fail future-heading/occupied checks. Static recovery probe is not a closed-loop recovery validation.'}
(OUT/'ANALYSIS.json').write_text(json.dumps(analysis,indent=2))
def backdrop(ax):
 ax.add_collection(PolyCollection(mesh['ground_top'][:,:,:2],facecolors='#e2e8f0',edgecolors='none',zorder=0))
 ax.scatter(points[:,0],points[:,1],s=.4,c=points[:,2],cmap='copper',vmin=-.9,vmax=1,alpha=.55,rasterized=True)
 ax.plot([-13.5,13.5,13.5,-13.5,-13.5],[-13.5,-13.5,13.5,13.5,-13.5],c='#64748b',ls='--',lw=1,label='声明任务边界')
 ax.set(xlim=(-16,16),ylim=(-16,16),aspect='equal',xlabel='地图 X / m',ylabel='地图 Y / m')
fig,ax=plt.subplots(figsize=(11,10));backdrop(ax)
seg=np.stack([np.c_[d['x'][:-1],d['y'][:-1]],np.c_[d['x'][1:],d['y'][1:]]],axis=1);lc=LineCollection(seg,cmap='viridis',linewidth=2.5);lc.set_array(d['elapsed_s'][:-1]);ax.add_collection(lc);fig.colorbar(lc,ax=ax,label='任务时间 / s')
ax.scatter(d['x'][0],d['y'][0],c='green',s=65,label='原XY起点');ax.scatter(d['x'][-1],d['y'][-1],c='red',s=65,label='停止位置')
g=last['waypoint'];ax.scatter(g['x'],g['y'],marker='x',c='#2563eb',s=100,label='后续TARE目标');ax.annotate('当前车头约152°',xy=(d['x'][-1]+1.3*math.cos(d['yaw'][-1]),d['y'][-1]+1.3*math.sin(d['yaw'][-1])),xytext=(d['x'][-1],d['y'][-1]),arrowprops={'arrowstyle':'->','color':'red'},color='red')
ax.legend(loc='upper left');ax.set_title(f'用户录制点云重建场景：600秒 / {finish["distance_m"]:.2f}米\n约{last_motion:.1f}秒后持续停车，结束未完成探索；没有补平缺测地面');fig.tight_layout();fig.savefig(OUT/'trajectory.png',dpi=160);plt.close(fig)
fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
for ax,key,label in zip(axes,['distance_m','sampled_free_volume_m3','ht_age_s'],['实际里程 / m','采样自由体积 / m³','最新HT源龄 / s']):
 ax.plot(d['elapsed_s'],d[key],c='#0f766e',lw=1);ax.axvline(last_motion,c='red',ls='--');ax.set_ylabel(label);ax.grid(alpha=.2)
axes[2].axhline(1,c='black',ls=':');axes[2].set_ylim(0,2);axes[2].set_xlabel('正式采集时间 / s');fig.suptitle('完整记录：里程停止增长，HT继续更新，finish=false\n观测体积为采样代理指标，不是真值覆盖率');fig.tight_layout();fig.savefig(OUT/'progress.png',dpi=150);plt.close(fig)
fig,ax=plt.subplots(figsize=(10,5));scores=snapshot['eight_scores_at_robot'];ax.bar(np.arange(8),scores,color=['#dc2626' if v<.5 else '#0f766e' for v in scores]);ax.axhline(.5,c='black',ls='--');ax.set(ylim=(0,1.05),ylabel='模型通过概率',title=f'停车后的同位置快照：当前152°查方向3={scores[3]:.3f}；候选160°查方向4={scores[4]:.3f}\n当前物理支撑及占据检查通过；快照不代表首次停车时刻');ax.set_xticks(np.arange(8),[f'{i*45}°' for i in range(8)]);fig.tight_layout();fig.savefig(OUT/'direction_scores.png',dpi=160);plt.close(fig)
# Recorded-data visualization; no simulated camera footage is claimed.
fig,ax=plt.subplots(figsize=(8,7),dpi=100);backdrop(ax);ax.axis('off');fig.subplots_adjust(0,0,1,1);fig.canvas.draw();box=ax.get_window_extent();xl=ax.get_xlim();yl=ax.get_ylim();buf=io.BytesIO();fig.savefig(buf,format='png');plt.close(fig);buf.seek(0);base=Image.open(buf).convert('RGB')
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',21);small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',16)
def pixel(x,y):return box.x0+(x-xl[0])/(xl[1]-xl[0])*box.width,700-(box.y0+(y-yl[0])/(yl[1]-yl[0])*box.height)
p=subprocess.Popen(['/home/lzz/cmu_test_20261110/deps/usr/bin/ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','800x830','-r','10','-i','-','-c:v','libx264','-threads','1','-preset','fast','-pix_fmt','yuv420p',str(OUT/'recorded_trajectory_10x.mp4')],stdin=subprocess.PIPE)
for t in range(601):
 im=Image.new('RGB',(800,830),'white');im.paste(base,(0,105));draw=ImageDraw.Draw(im);i=min(len(d['x'])-1,max(0,int(np.searchsorted(d['elapsed_s'],t,side='right'))-1));path=[(x,y+105) for x,y in map(pixel,d['x'][:i+1],d['y'][:i+1])]
 if len(path)>1:draw.line(path,fill='#0f766e',width=3)
 x,y=path[-1];draw.ellipse((x-5,y-5,x+5,y+5),fill='red');draw.line([(x,y),(x+20*math.cos(d['yaw'][i]),y-20*math.sin(d['yaw'][i]))],fill='red',width=3)
 draw.text((12,7),f'用户录制地图 · 当前八方向版 · 10倍速 · {t:03d}/600秒',fill='black',font=font)
 draw.text((12,40),f'里程 {d["distance_m"][i]:.2f}m，采样自由体积 {d["sampled_free_volume_m3"][i]:.1f}m³',fill='black',font=small)
 draw.text((12,66),'状态：HT约束下局部路径阻塞，任务未完成' if t>last_motion+3 else '状态：探索中；视频依据实际采集轨迹绘制',fill='red' if t>last_motion+3 else 'black',font=small)
 draw.text((12,807),'点云/网格底图＋实际遥测可视化；非Gazebo相机录像。',fill='black',font=small);p.stdin.write(im.tobytes())
p.stdin.close();assert p.wait()==0;print(json.dumps(analysis,indent=2))
