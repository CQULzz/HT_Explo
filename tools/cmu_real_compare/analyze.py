from pathlib import Path
import json,csv,collections,re,io,subprocess,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/home/lzz/cmu_real_compare_20261110');OUT=ROOT/'delivery';OUT.mkdir(exist_ok=True)
OLD=ROOT/'runs/old_real_600s_01';NEW=Path('/home/lzz/cmu_test_20261110/runs/ht_600s_06')
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False})
def read(run):
 rows=list(csv.DictReader((run/'observations/metrics.csv').open()))
 return {k:np.array([float(r[k]) if r[k] else np.nan for r in rows]) for k in rows[0] if k!='finish'}
a=read(OLD);b=read(NEW);start=json.loads((OLD/'observations/START.json').read_text())['clock'];end=float(a['time'][-1])
events=[json.loads(l) for l in (OLD/'observations/events.jsonl').read_text().splitlines()]
def episodes(topic):
 result=[];prev=None
 for e in events:
  if e['kind']!=topic:continue
  s=e['data']['status']
  if s!=prev:
   result.append({'elapsed_s':e['time']-start,'status':s});prev=s
 return result
def durations(topic,ttl):
 records=[e for e in events if e['kind']==topic];sums=collections.Counter()
 for i,e in enumerate(records):
  left=max(start,e['time']);right=min(end,records[i+1]['time'] if i+1<len(records) else end)
  if right<=left:continue
  valid=max(0,min(right,e['time']+ttl)-left)
  sums[e['data']['status']]+=valid;sums['NO_FRESH_STATUS']+=right-left-valid
 return dict(sums)
transitions=episodes('/ht_real/mission_state');ret=next(e['elapsed_s'] for e in transitions if e['status']=='RETURNING_HOME');complete=next(e['elapsed_s'] for e in transitions if e['status']=='COMPLETED')
comparison={}
for t in [60,120,ret,complete,264,600]:
 comparison[str(t)]={}
 for label,series in [('old_real',a),('minimal_8dir',b)]:
  i=int(np.argmin(abs(series['elapsed_s']-t)))
  comparison[str(t)][label]={k:float(series[k][i]) for k in ['elapsed_s','distance_m','sampled_free_volume_m3','x','y']}
result={'old_summary':json.loads((OLD/'observations/SUMMARY.json').read_text()),'new_summary':json.loads((NEW/'observations/SUMMARY.json').read_text()),
 'mission_transitions':transitions,'mission_duration_s':durations('/ht_real/mission_state',2.),
 'follower_duration_s':durations('/ht_real/ht_follower_status',.5),'comparison':comparison,
 'definitions':{'status_duration':'piecewise hold, clipped to experiment; mission freshness 2s, follower freshness 0.5s; missing freshness counted separately',
 'volume':'same recorded sampled-ray union as previous experiment; not ground-truth coverage or a proof of confirmed reachable outstanding tasks'}}
(OUT/'ANALYSIS.json').write_text(json.dumps(result,indent=2))
lines=(OLD/'simulation.log').read_text(errors='replace').splitlines()
for i,l in enumerate(lines):
 if 'TARE_COMPLETION' in l and 'local_complete=1' in l:
  (OUT/'first_completion.log').write_text('\n'.join(lines[max(0,i-6):i+9])+'\n');break
p=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/indoor/preview/pointcloud.ply')
with p.open('rb') as f:
 while f.readline().strip()!=b'end_header':pass
 pts=np.frombuffer(f.read(),dtype='<f4').reshape(-1,3)[::6]
pts=pts[pts[:,2]<2.]
fig,ax=plt.subplots(figsize=(12,9));ax.scatter(pts[:,0],pts[:,1],s=.08,c='#cbd5e1',rasterized=True)
ax.plot(b['x'],b['y'],c='#0f766e',lw=2,label=f"最小八方向版：600s / {b['distance_m'][-1]:.2f}m")
ax.plot(a['x'],a['y'],c='#dc2626',lw=2,label=f"旧实车版：600s / {a['distance_m'][-1]:.2f}m")
i=np.argmin(abs(a['elapsed_s']-ret));ax.scatter(a['x'][i],a['y'][i],marker='x',s=90,c='#dc2626',label=f'旧版 {ret:.2f}s 开始返航')
ax.scatter(0,0,s=60,c='black',label='共同起点');ax.set(aspect='equal',xlabel='世界 X / m',ylabel='世界 Y / m',title='同一 CMU 场景：旧版提前返航，新版继续探索\n速度、半径、采样及 HT 证据配置有差异；不是纯算法性能排名')
ax.legend();fig.tight_layout();fig.savefig(OUT/'trajectory_comparison.png',dpi=170);plt.close(fig)
fig,axes=plt.subplots(4,1,figsize=(12,12),sharex=True)
for label,s,c in [('旧实车版',a,'#dc2626'),('最小八方向版',b,'#0f766e')]:
 axes[0].plot(s['elapsed_s'],s['distance_m'],c=c,label=label)
 axes[1].plot(s['elapsed_s'],s['sampled_free_volume_m3'],c=c,label=label)
 axes[2].plot(s['elapsed_s'],s['ht_age_s'],c=c,lw=.7,alpha=.7,label=label)
axes[0].set_ylabel('实际里程 / m');axes[0].legend();axes[1].set_ylabel('采样自由体积 / m³');axes[2].set_ylabel('最新 HT 源龄 / s');axes[2].axhline(1,c='black',ls='--');axes[2].set_ylim(0,2)
states={'WAIT_START':0,'BLOCKED':1,'EXPLORING':2,'RETURNING_HOME':3,'COMPLETED':4};ts=[];ys=[]
for e in transitions:
 ts.append(max(0,e['elapsed_s']));ys.append(states[e['status']])
ts.append(a['elapsed_s'][-1]);ys.append(ys[-1]);axes[3].step(ts,ys,where='post',c='#dc2626',label='旧实车版状态');axes[3].axhline(2,c='#0f766e',ls='--',label='新版仍探索（finish=false）');axes[3].set_yticks(list(states.values()),list(states));axes[3].set_xlabel('任务时间 / s');axes[3].legend()
for ax in axes:
 ax.axvline(ret,c='#f59e0b',ls=':',label='旧版返航');ax.axvline(complete,c='#7c3aed',ls=':');ax.grid(alpha=.2)
fig.suptitle(f'完整600秒记录：旧版 {ret:.2f}s 返航，{complete:.2f}s 完成后停车');fig.tight_layout();fig.savefig(OUT/'progress_comparison.png',dpi=150);plt.close(fig)
# Video is a visualization of the recorded trajectories, not Gazebo/RViz footage.
fig,ax=plt.subplots(figsize=(10,7),dpi=100);ax.scatter(pts[:,0],pts[:,1],s=.1,c='#cbd5e1');ax.set_aspect('equal');ax.axis('off');fig.subplots_adjust(0,0,1,1);fig.canvas.draw();box=ax.get_window_extent();xlim=ax.get_xlim();ylim=ax.get_ylim();buf=io.BytesIO();fig.savefig(buf,format='png');plt.close(fig);buf.seek(0);base=Image.open(buf).convert('RGB')
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',21)
small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',16)
def pixel(x,y):return box.x0+(x-xlim[0])/(xlim[1]-xlim[0])*box.width,700-(box.y0+(y-ylim[0])/(ylim[1]-ylim[0])*box.height)
ffmpeg='/home/lzz/cmu_test_20261110/deps/usr/bin/ffmpeg'
proc=subprocess.Popen([ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1000x820','-r','10','-i','-','-c:v','libx264','-threads','1','-preset','fast','-pix_fmt','yuv420p',str(OUT/'recorded_comparison_10x.mp4')],stdin=subprocess.PIPE)
for t in range(601):
 im=Image.new('RGB',(1000,820),'white');im.paste(base,(0,100));draw=ImageDraw.Draw(im)
 draw.text((15,8),f'CMU 实际记录轨迹对照 · 10倍速 · {t:03d}/600秒',fill='black',font=font)
 for label,s,c,y in [('旧实车版',a,'#dc2626',38),('最小八方向版',b,'#0f766e',66)]:
  n=max(1,int(np.searchsorted(s['elapsed_s'],t,side='right')));n=min(n,len(s['x']));path=[(px,py+100) for px,py in map(pixel,s['x'][:n],s['y'][:n])]
  if len(path)>1:draw.line(path,fill=c,width=3)
  x,yc=path[-1];draw.ellipse((x-5,yc-5,x+5,yc+5),fill=c)
  state='探索'
  if label=='旧实车版':
   for e in transitions:
    if e['elapsed_s']<=t:state=e['status']
  draw.text((15,y),f'{label}：{s["distance_m"][n-1]:.2f}m，{s["sampled_free_volume_m3"][n-1]:.1f}m³，{state}',fill=c,font=small)
 draw.text((15,796),'记录数据可视化，非 Gazebo/RViz 录屏；两版速度/半径/规划参数不同。',fill='black',font=small)
 proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
print(json.dumps(result,indent=2))
