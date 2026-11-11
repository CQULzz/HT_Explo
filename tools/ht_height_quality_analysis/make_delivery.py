from pathlib import Path
import csv, json, math, io, subprocess
from collections import Counter
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

ROOT=Path('/home/lzz/ht_quality_20261111')
RUN=ROOT/'runs/cmu_quality_300s_01'
OUT=ROOT/'delivery'; OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False})
specs=[
 ('最初几何＋HT','#94a3b8',Path('/home/lzz/cmu_test_20261110/runs/ht_600s_06')),
 ('历史纯HT','#8b5cf6',Path('/home/lzz/ht_only_20261111/runs/a_indoor_600s_03')),
 ('上版纯HT＋恢复','#ea580c',Path('/home/lzz/ht_recovery_20261111/runs/cmu_recovery_300s_02')),
 ('本次质量修复','#0f766e',RUN),
]
series=[]; summary={}
for label,color,path in specs:
 rows=list(csv.DictReader((path/'observations/metrics.csv').open()))
 d={k:np.array([float(r[k]) if r[k] else np.nan for r in rows]) for k in rows[0] if k!='finish'}
 series.append((label,color,d))
 values={key:float(np.interp(300,d['elapsed_s'],d[key])) for key in ['distance_m','sampled_free_volume_m3']}
 values.update(last_30s_distance_m=float(np.interp(300,d['elapsed_s'],d['distance_m'])-np.interp(270,d['elapsed_s'],d['distance_m'])),ht_source_age_p95_s=float(np.nanpercentile(d['ht_age_s'][d['elapsed_s']<=300],95)),source_run=str(path),sampling='Linear interpolation of ~0.5s metrics samples at exactly t=300s; free volume is a sampled observation proxy, not ground-truth exploration coverage.')
 summary[label]=values

fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
for label,color,d in series:
 mask=d['elapsed_s']<=300
 for ax,key in zip(axes,['distance_m','sampled_free_volume_m3','ht_age_s']):ax.plot(d['elapsed_s'][mask],d[key][mask],c=color,lw=1,label=label)
for ax,label in zip(axes,['实际里程 / m','采样观测自由体积 / m³','最新HT源龄 / s']):ax.set_ylabel(label);ax.grid(alpha=.2)
axes[0].legend(fontsize=9);axes[-1].axhline(1,color='red',ls='--');axes[-1].set_xlabel('任务时间 / s');axes[-1].set_xlim(0,300)
fig.suptitle('CMU indoor：同场景、起点、限速与统计口径的单轮对照')
fig.tight_layout();fig.savefig(OUT/'progress_comparison.png',dpi=160);plt.close(fig)

p=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/indoor/preview/pointcloud.ply')
with p.open('rb') as f:
 while f.readline().strip()!=b'end_header':pass
 points=np.frombuffer(f.read(),dtype='<f4').reshape(-1,3)[::8];points=points[points[:,2]<2]
fig,ax=plt.subplots(figsize=(12,8));ax.scatter(points[:,0],points[:,1],s=.1,c='#cbd5e1')
for label,color,d in series:
 use=d['elapsed_s']<=300;xx=d['x'][use];yy=d['y'][use]
 ax.plot(xx,yy,color=color,lw=1.5,label=f'{label}，{summary[label]["distance_m"]:.2f}m');ax.scatter(xx[-1],yy[-1],s=25,c=color)
ax.set(aspect='equal',xlabel='世界X / m',ylabel='世界Y / m',title='录制里程计轨迹（各版本前300秒）');ax.legend(fontsize=9);fig.tight_layout();fig.savefig(OUT/'trajectory_comparison.png',dpi=160);plt.close(fig)

start=json.loads((RUN/'observations/START.json').read_text())['clock']
events=[json.loads(line) for line in (RUN/'observations/events.jsonl').open()]
end=float(series[-1][2]['time'][-1]);filtered=[e for e in events if start<=e['time']<=end]
last={e['kind']:e['data'] for e in filtered}
recoveries=[e['data'] for e in filtered if e['kind']=='/ht_minimal/recovery'];counts=Counter(e['state'] for e in recoveries);episodes={}
for e in recoveries:
 i=e['plans']
 if i and e['state']=='EXECUTING' and i not in episodes:episodes[i]={'start':e,'end':None}
 if i in episodes and e['state']=='COMPLETED' and episodes[i]['end'] is None:episodes[i]['end']=e
ep=[]
for i,pair in episodes.items():
 a,b=pair['start'],pair['end'];item={'plan':i,'start_elapsed_s':a['time']-start,'completed':b is not None,'start':a,'end':b}
 if b:item.update(end_elapsed_s=b['time']-start,duration_s=b['time']-a['time'],net_displacement_m=math.dist((a['x'],a['y']),(b['x'],b['y'])))
 ep.append(item)
summary['new_run_diagnostics']={'last_events':last,'recovery_states':counts,'episodes':ep,'scope':'Recovery displacement is measured only between each EXECUTING start and first COMPLETED event.'}
(OUT/'COMPARISON.json').write_text(json.dumps(summary,indent=2))

font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22);small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',17)
fig,ax=plt.subplots(figsize=(11,7),dpi=100);ax.scatter(points[:,0],points[:,1],s=.1,c='#cbd5e1');ax.set_aspect('equal');ax.axis('off');fig.subplots_adjust(0,0,1,1);fig.canvas.draw();box=ax.get_window_extent();xlim=ax.get_xlim();ylim=ax.get_ylim();buf=io.BytesIO();fig.savefig(buf,format='png',dpi=100);plt.close(fig);buf.seek(0);base=Image.open(buf).convert('RGB')
def pixel(x,y):return(box.x0+(x-xlim[0])/(xlim[1]-xlim[0])*box.width,700-(box.y0+(y-ylim[0])/(ylim[1]-ylim[0])*box.height)+80)
ffmpeg='/home/lzz/cmu_test_20261110/deps/usr/bin/ffmpeg'
proc=subprocess.Popen([ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1100x940','-r','10','-i','-','-c:v','libx264','-threads','1','-preset','fast','-pix_fmt','yuv420p',str(OUT/'quality_300s_10x.mp4')],stdin=subprocess.PIPE)
for second in range(301):
 im=Image.new('RGB',(1100,940),'white');im.paste(base,(0,80));draw=ImageDraw.Draw(im);draw.text((20,8),'CMU indoor｜原TARE＋八方向HT｜高程质量修复',font=font,fill='#0f172a');draw.text((20,40),f'录制轨迹可视化（非相机/RViz录像），10倍速  t={second}s',font=small,fill='#475569')
 for row,(label,color,d) in enumerate(series):
  i=max(0,min(int(np.searchsorted(d['elapsed_s'],second,side='right')-1),len(d['x'])-1));xy=[pixel(x,y) for x,y in zip(d['x'][:i+1:2],d['y'][:i+1:2])]
  if len(xy)>1:draw.line(xy,fill=color,width=3)
  u,v=pixel(d['x'][i],d['y'][i]);draw.ellipse((u-4,v-4,u+4,v+4),fill=color);draw.text((20,795+row*32),f'{label}：{d["distance_m"][i]:.2f}m，观测体积 {d["sampled_free_volume_m3"][i]:.1f}m³',font=small,fill=color)
 proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0
subprocess.run([ffmpeg,'-v','error','-i',str(OUT/'quality_300s_10x.mp4'),'-f','null','-'],check=True)
print(json.dumps({k:v for k,v in summary.items() if k!='new_run_diagnostics'},indent=2))
