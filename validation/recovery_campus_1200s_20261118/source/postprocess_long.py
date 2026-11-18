from pathlib import Path
import json,csv,re,hashlib,tarfile,collections,shutil,math,struct
import numpy as np
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import sys
sys.path.append('/home/lzz/ht_real_baseline_20261115/validation_venv/lib/python3.10/site-packages')
from mcap.reader import make_reader
root=Path('/home/lzz/ht_recovery_campus_1200s_20261118');run=root/'runs/recovery_campus_1200s_01';old=Path('/home/lzz/ht_campus_repeat_1200s_20261118/runs/explicit_labels_campus_repeat_1200s_01')
result=json.loads((run/'RESULT.json').read_text());rows=list(csv.DictReader((run/'observations/metrics.csv').open()));start=json.loads((run/'observations/START.json').read_text())['clock'];end=float(rows[-1]['time'])
events=[]
for line in (run/'observations/events.jsonl').open():
 e=json.loads(line)
 if start<=e['time']<=end:events.append(e)
finish=[e['time']-start for e in events if e['kind']=='finish_transition' and e['data'].get('finish')]
moving=[r for r in rows if abs(float(r['cmd_linear']))>1e-5 or abs(float(r['cmd_angular']))>1e-5];last=rows[-1];yaw=float(last['yaw']);base=[float(last['x'])-.1725*math.cos(yaw),float(last['y'])-.1725*math.sin(yaw)]
near30=min(rows,key=lambda r:abs(float(r['elapsed_s'])-(float(last['elapsed_s'])-30)))
counts=collections.Counter(e['data'].get('reason') for e in events if e['kind']=='/ht_minimal/command_audit')
initial_counts=json.loads((run/'observations/START.json').read_text())['counts']
rates={k:(result['summary']['counts'][k]-initial_counts[k])/result['summary']['elapsed_s'] for k in ['scans','ht_maps']}
age=np.array([float(r['ht_age_s']) for r in rows]);age=age[np.isfinite(age)]
analysis={'duration_s':result['summary']['elapsed_s'],'distance_m':result['summary']['distance_m'],'last30_distance_m':float(last['distance_m'])-float(near30['distance_m']),'sampled_free_volume_m3':result['summary']['sampled_free_volume_m3'],'finish':result['summary']['finish'],'finish_signal_elapsed_s':finish[0] if finish else None,'last_nonzero_sample_elapsed_s':float(moving[-1]['elapsed_s']) if moving else None,'final_base_xy':base,'final_base_distance_to_initial_m':math.hypot(*base),'wall_rates':rates,'sampled_ht_age_s':dict(zip(['p50','p95','max'],[float(np.percentile(age,50)),float(np.percentile(age,95)),float(age.max())])),'fraction_sampled_age_over_1s':float((age>1).mean()),'command_audit_reasons':dict(counts)}
lines=(run/'simulation.log').read_text(errors='replace').splitlines();diagnostics=[l for l in lines if 'EXPLORATION_DIAG' in l and (lambda m: m is not None and start<=float(m[1])<=end)(re.search(r'\[([0-9]{10}\.[0-9]+)\]',l))]
if finish:
 target=start+finish[0];analysis['diagnostic_at_finish']=min(diagnostics,key=lambda l:abs(float(re.search(r'\[([0-9]{10}\.[0-9]+)\]',l)[1])-target))
analysis['last_planner_diagnostic']=diagnostics[-1] if diagnostics else None
# Actual parameter equality, separate from output/root address differences.
params={}
for name in ['tare_planner_node.yaml','localPlanner.yaml','pathFollower.yaml','cupy_to_ht_bridge.yaml','vehicleSimulator.yaml']:
 params[name]={'semantic_equal':yaml.safe_load((run/name).read_text())==yaml.safe_load((old/name).read_text()),'byte_equal':(run/name).read_bytes()==(old/name).read_bytes()}
analysis['parameter_comparison_with_previous']=params
(run/'ANALYSIS.json').write_text(json.dumps(analysis,indent=2));print('ANALYSIS',json.dumps(analysis,indent=2),flush=True)
# Validate full raw recording without replay or publishing ROS topics.
clock_samples=[]
metadata=yaml.safe_load((run/'bag/metadata.yaml').read_text())['rosbag2_bagfile_information'];recorded=collections.Counter();files=[]
for path in sorted((run/'bag').glob('*.mcap')):
 with path.open('rb') as stream:
  for schema,channel,msg in make_reader(stream,validate_crcs=True).iter_messages():
   recorded[channel.topic]+=1
   if channel.topic=='/clock' and start<=msg.log_time/1e9<=end:
    endian='<' if msg.data[1]&1 else '>';sec,nsec=struct.unpack_from(endian+'iI',msg.data,4);clock_samples.append([msg.log_time/1e9,sec+nsec*1e-9])
 files.append({'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
expected={t['topic_metadata']['name']:t['message_count'] for t in metadata['topics_with_message_count']};assert recorded==collections.Counter(expected), {'actual':dict(recorded),'metadata':expected}
freeze=json.loads((run/'FREEZE.json').read_text());seen={}
with tarfile.open(run/'frozen_runtime.tar.gz') as archive:
 for member in archive:
  if member.isfile():seen['/'+member.name]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
assert seen==freeze
validation={'available_crc_checks_passed':True,'metadata_counts_match':True,'messages':sum(recorded.values()),'topic_counts':dict(recorded),'files':files,'frozen_archive_matches_manifest':True,'frozen_files':len(freeze)}
clock_samples.sort()
if len(clock_samples)>1:
 analysis['sim_time_advanced_s']=clock_samples[-1][1]-clock_samples[0][1];analysis['sim_real_time_factor']=analysis['sim_time_advanced_s']/(clock_samples[-1][0]-clock_samples[0][0]);(run/'ANALYSIS.json').write_text(json.dumps(analysis,indent=2))
(run/'RECORDING_VALIDATION.json').write_text(json.dumps(validation,indent=2));print('RECORDING validated',len(files),'files',sum(recorded.values()),'messages',flush=True)
child_errors=[]
for l in lines:
 if 'process has died' in l:
  child_errors.append(l)
procs=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  a=(p/'cmdline').read_bytes().split(b'\0')
  if a and Path(a[0].decode()).name in {'gzserver','gzmaster','vehicleSimulator','localPlanner','pathFollower','rviz2','Xvfb'}:
   env=(p/'environ').read_bytes().split(b'\0');own=b'ROS_DOMAIN_ID=209' in env or b'DISPLAY=:107' in env or any(b'/ht_recovery_campus_1200s_20261118/' in x for x in a)
   if own:procs.append({'pid':int(p.name),'argv':[x.decode(errors='replace') for x in a if x]})
 except (OSError,UnicodeDecodeError):pass
(run/'CLEANUP.json').write_text(json.dumps({'child_errors':child_errors,'relevant_processes_remaining':procs,'launcher_codes':result['exit_codes'],'clean_child_exit':not child_errors},indent=2))
ledger=json.loads((root/'BUDGET.json').read_text());ledger.update(status='closed',used_attempts=len(ledger['attempts']),result=str(run/'RESULT.json'));(root/'BUDGET.json').write_text(json.dumps(ledger,indent=2))
fig,axes=plt.subplots(1,3,figsize=(15,4.5))
for label,p,color in [('previous',old,'#94a3b8'),('repeat',run,'#0f766e')]:
 data=list(csv.DictReader((p/'observations/metrics.csv').open()));a=lambda k:np.array([float(r[k]) for r in data]);t=a('elapsed_s');x=a('x')-.1725*np.cos(a('yaw'));y=a('y')-.1725*np.sin(a('yaw'))
 axes[0].plot(x,y,label=label,color=color);axes[1].plot(t,a('distance_m'),label=label,color=color);axes[2].plot(t,a('sampled_free_volume_m3'),label=label,color=color)
axes[0].set(xlabel='World X (m)',ylabel='World Y (m)',title='Base trajectory',aspect='equal');axes[1].set(xlabel='Wall time (s)',ylabel='Recorded distance (m)',title='Distance');axes[2].set(xlabel='Wall time (s)',ylabel='Sampled observation proxy (m3)',title='Observation proxy, not ground-truth coverage')
for ax in axes:ax.grid(alpha=.2);ax.legend()
fig.tight_layout();fig.savefig(run/'comparison.png',dpi=150);plt.close(fig)

# Phase-wise motion, progress and actual clock consistency.
arr=lambda k:np.array([float(r[k]) for r in rows]);t=arr('elapsed_s');distance=arr('distance_m');volume=arr('sampled_free_volume_m3');phases=[]
for begin in range(0,1200,300):
 stop=begin+300;i=int(np.argmin(abs(t-begin)));j=int(np.argmin(abs(t-stop)));mask=(t>=begin)&(t<=stop)
 phases.append({'begin_s':begin,'end_s':stop,'distance_m':float(distance[j]-distance[i]),'sampled_observation_volume_added_m3':float(volume[j]-volume[i]),'reverse_command_samples':int(((arr('cmd_linear')<-.01)&mask).sum()),'zero_linear_and_angular_samples':int(((abs(arr('cmd_linear'))<1e-5)&(abs(arr('cmd_angular'))<1e-5)&mask).sum())})
x=arr('x')-.1725*np.cos(arr('yaw'));y=arr('y')-.1725*np.sin(arr('yaw'));speed=np.hypot(np.diff(x),np.diff(y))/np.diff(t);still=speed<.02;intervals=[];i=0
while i<len(still):
 if not still[i]:i+=1;continue
 j=i
 while j+1<len(still) and still[j+1]:j+=1
 if t[j+1]-t[i]>=10:
  angles=np.unwrap(arr('yaw')[i:j+2]);turn=float(abs(np.diff(angles)).sum())
  intervals.append({'begin_s':float(t[i]),'end_s':float(t[j+1]),'duration_s':float(t[j+1]-t[i]),'heading_total_change_rad':turn,'classification':'turning_in_place' if turn>.3 else 'stationary','finish_at_end':rows[j+1]['finish']})
 i=j+1
clock_error=(arr('time')-arr('time')[0])-(t-t[0]);phase_result={'phases':phases,'low_translation_intervals_at_least_10s':intervals,'clock_elapsed_error_max_abs_s':float(abs(clock_error).max()),'definition':'Motion uses recorded base XY after lidar offset correction; observation volume is a ray-sampling proxy, not complete ground coverage.'}
(run/'PHASES.json').write_text(json.dumps(phase_result,indent=2));print('PHASES',json.dumps(phase_result),flush=True)
print('Postprocess complete',flush=True)
