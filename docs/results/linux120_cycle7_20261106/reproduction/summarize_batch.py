from pathlib import Path
import json,csv,collections,re,shutil,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import argparse
parser=argparse.ArgumentParser();parser.add_argument('batch_root',type=Path);args=parser.parse_args()
R=args.batch_root.resolve();D=R/'repo/docs/results/linux120_cycle7_20261106';B=json.loads((R/'BUDGET.json').read_text());summaries=[]
colors={'b01_single42':'#93a6cc','b02_single42':'#2455a4','b03_single99':'#4fa580','b04_tare42':'#e5b27e','b05_tare99':'#b26928','b06_tare42_repeat':'#bd403c'}
fig,axs=plt.subplots(2,2,figsize=(14,10));maps=np.load(R/'runtime/local_map.npy');maps=maps[(abs(maps[:,0])<15)&(abs(maps[:,1])<15)&(maps[:,2]<3)]
axs[0,0].scatter(maps[::10,0],maps[::10,1],s=.25,color='#cccccc',rasterized=True)
for entry in B['runs']:
 label=entry['label'];run=R/'runs'/label;rows=[x for x in csv.DictReader((run/'metrics.csv').open()) if float(x['elapsed_sim'])>=0]
 done=json.loads((run/'DONE.json').read_text());result=json.loads((run/'RUN_RESULT.json').read_text());manifest=json.loads((run/'manifest.json').read_text());source=[];transitions=[];last={};reason=collections.Counter();low=[];first_context=None
 for line in (run/'events.jsonl').open():
  q=json.loads(line);k=q['topic'];v=q['data']
  if k in ['mission_state','ht_execution_status'] and v!=last.get(k):transitions.append([q['time'],k,v]);last[k]=v
  if k=='runtime_status':
   d=json.loads(v);reason[d.get('reason')]+=1
   if d.get('execution_footprint',{}).get('current_heading_low'):low.append(q['time'])
  if k=='ht_performance':source.append(json.loads(v)['source_age_at_publish_s'])
 files=sorted((run/'contexts').glob('*.npz'),key=lambda p:float(p.stem.replace('_','.')))
 if files:first_context=float(np.load(files[0])['source_stamp'])
 random_calls=re.findall(r'TARE_RANDOM_CALL[^\n]+',(run/'navigation.log').read_text())
 m={'label':label,'arm':manifest.get('navigation','ht'),'seed':entry['seed'],'tested_commit':manifest['project_head'],'state':entry['state'],'duration_s':done['elapsed_sim'],'distance_m':done['distance'],'distance_before_first_ready_sample_m':float(rows[0]['distance_m']),'sampled_free_volume_m3':done['free_volume'],'completed':done['mission_completed'],'completed_at_sim_s':next((t for t,k,v in transitions if k=='mission_state' and v=='COMPLETED'),None),'final_mission_state':last.get('mission_state'),'final_execution_status':last.get('ht_execution_status'),'map_source_age_p95_s':float(np.percentile(source,95)) if source else None,'map_source_age_samples':len(source),'current_heading_low_runtime_samples':len(low),'zero_command_sample_fraction':sum(abs(float(x['v_cmd']))<1e-6 and abs(float(x['w_cmd']))<1e-6 for x in rows)/len(rows),'first_context_source_s':first_context,'first_random_calls':random_calls[:5],'runtime_reason_events':dict(reason),'state_transitions':transitions,'run_result':result,'bag_messages':sum(json.loads((run/'BAG_VERIFICATION.json').read_text())['counts'].values()),'all_video_frames_decoded':json.loads((run/'VIDEO_VERIFICATION.json').read_text())['all_frames_decoded'],'final_xy':[float(rows[-1]['x']),float(rows[-1]['y'])]}
 summaries.append(m);style='--' if entry['state']=='FAILED' else '-';lab=f"{label}"+(' [FAILED teardown]' if entry['state']=='FAILED' else '')
 t=np.array([float(x['elapsed_sim']) for x in rows]);color=colors[label]
 axs[0,0].plot([float(x['x']) for x in rows],[float(x['y']) for x in rows],color=color,linestyle=style,label=lab)
 axs[0,1].plot(t,[float(x['distance_m']) for x in rows],color=color,linestyle=style,label=lab)
 axs[1,0].plot(t,[float(x['observed_free_volume_m3']) for x in rows],color=color,linestyle=style,label=lab)
 tt=[];aa=[]
 for line in (run/'events.jsonl').open():
  q=json.loads(line)
  if q['topic']=='ht_performance':tt.append(q['time']-.2);aa.append(json.loads(q['data'])['source_age_at_publish_s'])
 if aa:axs[1,1].plot(tt,aa,color=color,linestyle=style,label=lab)
axs[0,0].set(xlabel='World x (m)',ylabel='World y (m)',title='Recorded-PCD scene and actual simulated routes',xlim=(-16,16),ylim=(-16,16));axs[0,0].set_aspect('equal')
axs[0,1].set(xlabel='Elapsed simulation (s)',ylabel='Cumulative XY distance (m)',title='Ground truth; initial settling/slip included')
axs[1,0].set(xlabel='Elapsed simulation (s)',ylabel='Sampled observed free volume (m3)',title='Common ray/voxel metric; not scene coverage %')
axs[1,1].axhline(1,color='red',linestyle=':',label='Unchanged age gate 1 s');axs[1,1].set(xlabel='Elapsed simulation (s)',ylabel='Producer source age (s)',title='1Hz producer metrics; TARE has no HT inference')
for ax in axs.flat:ax.grid(alpha=.2);ax.legend(fontsize=7)
fig.suptitle('Native Linux / Gazebo8 / Scout / 120s each — six attempts, failures retained');fig.tight_layout();fig.savefig(D/'FINAL_COMPARISON.png',dpi=160);plt.close(fig)
res={'simulations_used':B['used'],'maximum':6,'summaries':summaries,'comparison_type':'Current-fork TARE geometric+CMU vs HT-assisted native TARE, end-to-end, not untouched-upstream baseline or neural-only ablation','metric_note':'Observed free volume is the common source-second sampled LiDAR ray/voxel union inside the +/-15m crop, not physical coverage truth; tiny stationary pose/ray changes may increase it. No externally certified reachable task set is available. Failed teardown runs are shown and retained, not counted as all-checks-passed. Source-age metric remains producer1Hz.'}
by={x['label']:x for x in summaries};pairs=[]
for ht,tare in [('b02_single42','b06_tare42_repeat'),('b03_single99','b05_tare99')]:
 h=by[ht];t=by[tare];pairs.append({'seed':h['seed'],'ht':ht,'tare':tare,'ht_free_volume_m3':h['sampled_free_volume_m3'],'tare_free_volume_m3':t['sampled_free_volume_m3'],'ht_vs_tare_volume_percent':100*(h['sampled_free_volume_m3']/t['sampled_free_volume_m3']-1),'ht_distance_m':h['distance_m'],'tare_distance_m':t['distance_m'],'both_clean':h['state']==t['state']=='RECORDED','note':'One pair per seed; fixed run order and asynchronous inputs; lifecycle-only differences recorded. No statistical superiority claim.'})
res['clean_pairs']=pairs
(D/'FINAL_COMPARISON.json').write_text(json.dumps(res,indent=2));shutil.copy2(R/'BUDGET.json',D/'BUDGET.json');print(json.dumps({'used':B['used'],'pairs':pairs},indent=2))
