from pathlib import Path
import json,csv
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
root=Path('/home/lzz/ht_campus_repeat_1200s_20261118');run=root/'runs/explicit_labels_campus_repeat_1200s_01';baseline=Path('/home/lzz/ht_campus_1200s_20261118/runs/explicit_labels_campus_1200s_03')
def analyze(path):
 rows=list(csv.DictReader((path/'observations/metrics.csv').open()));arr=lambda k:np.array([float(r[k]) for r in rows]);t=arr('elapsed_s');xy=np.c_[arr('x')-.1725*np.cos(arr('yaw')),arr('y')-.1725*np.sin(arr('yaw'))];d=np.linalg.norm(np.diff(xy,axis=0),axis=1);mid=(xy[:-1]+xy[1:])/2;repeat=np.zeros(len(d),bool);nearest=np.full(len(d),np.inf)
 for i in range(len(d)):
  eligible=np.searchsorted(t,t[i]-30,side='right')
  if eligible>0:nearest[i]=np.linalg.norm(xy[:eligible]-mid[i],axis=1).min();repeat[i]=nearest[i]<=1.
 finish=np.array([r['finish']=='True' for r in rows[:-1]]);reverse=arr('cmd_linear')[:-1]<-.01
 def part(mask):
  length=float(d[mask].sum());repeated=float(d[mask&repeat].sum());return {'base_xy_distance_m':length,'route_revisit_distance_m':repeated,'route_revisit_fraction':repeated/length if length else None,'reverse_command_distance_m':float(d[mask&reverse].sum())}
 summary={'proximity_sensitivity':{str(radius):{'route_revisit_distance_m':float(d[nearest<=radius].sum()),'route_revisit_fraction':float(d[nearest<=radius].sum()/d.sum()) if d.sum() else None} for radius in [1.,3.,5.]},'overall':part(np.ones(len(d),bool)),'before_finish':part(~finish),'after_finish':part(finish),'phases':[]}
 for begin in range(0,1200,300):summary['phases'].append({'begin_s':begin,'end_s':begin+300,**part((t[:-1]>=begin)&(t[:-1]<begin+300))})
 return summary,rows,t,xy,d,repeat,nearest
results={};cur=None
for label,path in [('previous',baseline),('repeat',run)]:
 value,*arrays=analyze(path);results[label]=value
 if label=='repeat':cur=arrays
results['definition']='Distance-weighted base-XY segments; midpoint within1m of any recorded route sample at least30s earlier. This is spatial revisit, not proof of useless travel; necessary transfer/return and new observations from old positions are possible. Reverse velocity is reported separately and is not equivalent to route revisit.'
(run/'BACKTRACKING.json').write_text(json.dumps(results,indent=2));rows,t,xy,d,repeat,nearest=cur
with (run/'backtracking_segments.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['begin_s','end_s','base_segment_m','nearest_route_older30s_m','route_revisit','command_linear','finish'])
 for i in range(len(d)):w.writerow([t[i],t[i+1],d[i],nearest[i] if np.isfinite(nearest[i]) else '',bool(repeat[i]),rows[i]['cmd_linear'],rows[i]['finish']])
fig,ax=plt.subplots(figsize=(10,8));segments=np.stack([xy[:-1],xy[1:]],axis=1);lc=LineCollection(segments,colors=np.where(repeat[:,None],np.array([[.85,.22,.16,1.]]),np.array([[.05,.55,.51,1.]])),linewidth=2);ax.add_collection(lc);ax.autoscale();ax.set_aspect('equal');ax.plot([],[],c='#0d8c82',label='Not within1m of route older30s');ax.plot([],[],c='#d93829',label='Within1m of route older30s');ax.scatter(*xy[0],c='black',s=35,label='Start');ax.scatter(*xy[-1],c='blue',s=35,label='End');ax.set(xlabel='World X (m)',ylabel='World Y (m)',title='Spatial route revisit diagnostic; not an efficiency verdict');ax.legend();ax.grid(alpha=.2);fig.tight_layout();fig.savefig(run/'backtracking.png',dpi=160);plt.close(fig);print(json.dumps(results,indent=2))
