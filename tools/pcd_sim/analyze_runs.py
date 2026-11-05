import pathlib,json,csv,collections,argparse,hashlib,shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ap=argparse.ArgumentParser();ap.add_argument('label');ap.add_argument('--root',type=pathlib.Path,default=pathlib.Path('/home/w_lzz/ht-iterations-20261105'));ap.add_argument('--comparison');a=ap.parse_args()
R=a.root.resolve();run=R/a.label;dest=R/'reports'/a.label;dest.mkdir(parents=True,exist_ok=True)
def load(p):
 rows=list(csv.DictReader((p/'metrics.csv').open()))
 valid=[x for x in rows if float(x['elapsed_sim'])>=0]
 return valid
def metrics(p):
 rows=load(p);reasons=collections.Counter();ages=[];callback=[];source_at_callback=[]
 for line in (p/'events.jsonl').open():
  x=json.loads(line)
  try:q=json.loads(x['data'])
  except (TypeError,KeyError,json.JSONDecodeError):continue
  if x['topic']=='runtime_status':reasons[q.get('reason','?')]+=1
  if x['topic']=='ht_performance':
   ages.append(q['source_age_at_publish_s']);callback.append(q['callback_service_s']);source_at_callback.append(q['source_age_at_callback_s'])
 def quant(v):return dict(zip(['p50','p95','max'],map(float,np.percentile(v,[50,95,100])))) if v else None
 done=json.loads((p/'DONE.json').read_text());m=json.loads((p/'manifest.json').read_text())
 return {'label':p.name,'tested_commit':m['project_head'],'done':done,'run_result':json.loads((p/'RUN_RESULT.json').read_text()),'runtime_reason_event_counts':dict(reasons),'map_source_age_at_publish_s':quant(ages),'map_source_age_at_callback_s':quant(source_at_callback),'ht_callback_service_s':quant(callback),'sampled_zero_command_fraction':sum(abs(float(x['v_cmd']))<1e-6 and abs(float(x['w_cmd']))<1e-6 for x in rows)/len(rows),'distance_before_ready_m':float(rows[0]['distance_m']),'distance_after_first_ready_sample_m':float(rows[-1]['distance_m'])-float(rows[0]['distance_m']),'map_age_sample_count':len(ages),'metric_note':'Distance is cumulative ground-truth XY, includes gravity settling/slip before READY. Free volume is sampled LiDAR ray-voxel union, not ground-truth scene coverage. Runtime reason counts are events, not seconds; zero fraction is ~2Hz telemetry samples.'}
summary=metrics(run);(dest/'SUMMARY.json').write_text(json.dumps(summary,indent=2))
fig,axs=plt.subplots(2,2,figsize=(13,9));runs=[run] if not a.comparison else [R/a.comparison,run]
for p in runs:
 rows=load(p);t=np.array([float(x['elapsed_sim']) for x in rows]);lab=p.name
 axs[0,0].plot([float(x['x']) for x in rows],[float(x['y']) for x in rows],label=lab)
 axs[0,1].plot(t,[float(x['distance_m']) for x in rows],label=lab)
 axs[1,0].plot(t,[float(x['observed_free_volume_m3']) for x in rows],label=lab)
 tt=[];aa=[]
 for line in (p/'events.jsonl').open():
  q=json.loads(line)
  if q['topic']=='ht_performance':
   z=json.loads(q['data']);tt.append(q['time']-(float(rows[0]['sim_time'])-float(rows[0]['elapsed_sim'])));aa.append(z['source_age_at_publish_s'])
 axs[1,1].plot(tt,aa,label=lab,alpha=.7)
axs[0,0].set(xlabel='World x (m)',ylabel='World y (m)',title='Actual ground-truth trajectory');axs[0,0].axis('equal')
axs[0,1].set(xlabel='Elapsed simulation (s)',ylabel='Cumulative XY distance (m)',title='Includes initial settling')
axs[1,0].set(xlabel='Elapsed simulation (s)',ylabel='Observed free volume (m3)',title='Source-second sampled ray-voxel union')
axs[1,1].axhline(1,color='red',linestyle='--',label='Unchanged 1 s age gate');axs[1,1].set(xlabel='Elapsed simulation (s)',ylabel='Source age at HT publication (s)',title='Measured source stamps, no restamping')
for ax in axs.flat:ax.grid(alpha=.25);ax.legend(fontsize=8)
fig.suptitle('WSL Scout PCD - full 120 second trials');fig.tight_layout();fig.savefig(dest/'comparison.png',dpi=160);plt.close(fig)
if a.comparison:(dest/'COMPARISON.json').write_text(json.dumps({'baseline':metrics(R/a.comparison),'candidate':summary},indent=2))
print(json.dumps(summary,indent=2));print(dest)
