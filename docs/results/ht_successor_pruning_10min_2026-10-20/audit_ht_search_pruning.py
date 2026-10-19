from pathlib import Path
import argparse,re,json,collections,csv
import numpy as np
p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
start=json.loads((a.trial/'current/measurement_started.json').read_text())['wall_time']
rows=[]
for line in (a.trial/'current/tare.log').read_text(errors='replace').splitlines():
 if 'HT_SEARCH_AUDIT ' not in line:continue
 m=re.search(r'\[INFO\] \[([\d.]+)\]',line)
 if not m:continue
 stamp=float(m[1]);d=dict(re.findall(r'(\w+)=([^ ]+)',line.split('HT_SEARCH_AUDIT ',1)[1]));d.update(wall_time=stamp,t_s=stamp-start)
 for k,v in list(d.items()):
  try:d[k]=float(v)
  except (ValueError,TypeError):pass
 if 0<=d['t_s']<=600:rows.append(d)
def stats(x):
 return dict(count=len(x),termination=dict(collections.Counter(r['termination'] for r in x)),direct_connections=sum(bool(r.get('direct',0)) for r in x),dominated_edges_pruned=sum(r.get('dominated_pruned',0) for r in x),geometry_queries=sum(r.get('geometry_queries',0) for r in x),elapsed_s=dict(p50=float(np.median([r['elapsed_s'] for r in x])),p95=float(np.quantile([r['elapsed_s'] for r in x],.95)),max=max(r['elapsed_s'] for r in x)) if x else {},expanded_max=max((r['expanded'] for r in x),default=0),geometry_cpu_wall_fraction=sum(r['geometry_s'] for r in x)/max(1e-9,sum(r['elapsed_s'] for r in x)),rejection_counts={k:sum(r.get(k,0) for r in x) for k in ['geometry_reject','ht_reject','memory_reject','reserve_reject']})
a.output.mkdir(parents=True,exist_ok=True)
with (a.output/'searches.csv').open('w') as f:
 if rows:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
result=dict(measurement_origin=start,all=stats(rows),last60=stats([r for r in rows if r['t_s']>=540]),windows=[dict(start_s=t,end_s=t+60,**stats([r for r in rows if t<=r['t_s']<t+60])) for t in range(0,600,60)],limitations='Post-search wall log timestamps; geometry count includes local-horizon rejections before collision query. Callback sequence and complete memory snapshot are not reconstructed; categories distinguish search termination, not physical ground truth.')
(a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
if rows:
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt
 fig,ax=plt.subplots(3,1,figsize=(11,8),sharex=True)
 for term in sorted(set(r['termination'] for r in rows)):
  subset=[r for r in rows if r['termination']==term];ax[0].scatter([r['t_s'] for r in subset],[r['elapsed_s'] for r in subset],s=6,label=term)
 ax[0].set_ylabel('Search seconds');ax[0].legend(ncol=3)
 ax[1].scatter([r['t_s'] for r in rows],[r['expanded'] for r in rows],s=4);ax[1].set_ylabel('Expanded states')
 for k in ['geometry_reject','ht_reject','memory_reject','reserve_reject']:ax[2].plot([r['t_s'] for r in rows],[r[k] for r in rows],'.',ms=2,label=k)
 ax[2].set_ylabel('Rejected transitions');ax[2].legend(ncol=2);ax[2].set_xlabel('Measurement seconds')
 for x in ax:x.grid(alpha=.2)
 fig.tight_layout();fig.savefig(a.output/'searches.png',dpi=180)
print(json.dumps(result,indent=2))
