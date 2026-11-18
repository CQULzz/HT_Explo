from pathlib import Path
import collections,csv,hashlib,json,math,re,struct,sys,tarfile
import numpy as np
import yaml
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.append('/home/lzz/ht_real_baseline_20261115/validation_venv/lib/python3.10/site-packages')
from mcap.reader import make_reader
root=Path('/home/lzz/tare_native_campus_20261118');run=root/'runs/native_campus_01'
result=json.loads((run/'RESULT.json').read_text());rows=list(csv.DictReader((run/'observations/metrics.csv').open()));start=json.loads((run/'observations/START.json').read_text())['clock'];end=float(rows[-1]['time']);duration=result['summary']['elapsed_s']
events=[]
for line in (run/'observations/events.jsonl').open():
    event=json.loads(line)
    if start<=event['time']<=end:events.append(event)
finish=[e['time']-start for e in events if e['kind']=='finish_transition' and e['data'].get('finish')]
arr=lambda name:np.array([float(r[name]) for r in rows])
t=arr('elapsed_s');x=arr('x');y=arr('y');v=arr('cmd_linear');w=arr('cmd_angular');distance=arr('distance_m');volume=arr('sampled_free_volume_m3');last=rows[-1]
initial=json.loads((run/'observations/START.json').read_text());moving=np.flatnonzero((abs(v)>1e-5)|(abs(w)>1e-5));near30=int(np.argmin(abs(t-(t[-1]-30))))
analysis={'duration_s':duration,'distance_m':result['summary']['distance_m'],'base_xy_distance_m':float(np.hypot(np.diff(x),np.diff(y)).sum()),'finish':result['summary']['finish'],'finish_signal_elapsed_s':finish[0] if finish else None,'last_nonzero_sample_elapsed_s':float(t[moving[-1]]) if len(moving) else None,'last30_distance_m':float(distance[-1]-distance[near30]),'final_base_xy':[float(x[-1]),float(y[-1])],'final_base_distance_to_initial_m':float(np.hypot(x[-1]-initial['position'][0],y[-1]-initial['position'][1])),'sampled_free_volume_m3':result['summary']['sampled_free_volume_m3'],'wall_scan_rate_hz':(result['summary']['counts']['scans']-initial['counts']['scans'])/duration,'sampled_scan_age_s':{'p95':float(np.percentile(arr('scan_age_s'),95)),'max':float(arr('scan_age_s').max())},'maximum_abs_command_linear_mps':float(abs(v).max()),'mission_outcome':result.get('mission_outcome'),'ht_enabled':False,'scope':'Native TARE/geometry reference; different vehicle/sensor/speed from HT runs, not an HT-only ablation.'}
tail=np.flatnonzero(t>=t[-1]-20);stable=np.hypot(x[tail]-x[tail[0]],y[tail]-y[tail[0]])
returned={'outcome':result.get('mission_outcome'),'terminal_rule_hold_s':result['summary']['terminal_status']['home_hold_elapsed_s'],'samples':len(tail),'max_distance_to_initial_m':float(np.hypot(x[tail]-initial['position'][0],y[tail]-initial['position'][1]).max()),'max_translation_m':float(stable.max()),'all_finish_true':all(rows[i]['finish']=='True' for i in tail),'all_zero_command':bool(np.all(abs(v[tail])<.01)&np.all(abs(w[tail])<.01)),'all_inputs_fresh':all(0<=float(rows[i]['odom_age_s'])<=.2 and 0<=float(rows[i]['scan_age_s'])<=2 for i in tail)}
returned['passed']=bool(result.get('mission_complete') and returned['terminal_rule_hold_s']>=20 and returned['max_distance_to_initial_m']<=.5 and returned['max_translation_m']<=.05 and returned['all_finish_true'] and returned['all_zero_command'] and returned['all_inputs_fresh'])
(run/'RETURN_VERIFICATION.json').write_text(json.dumps(returned,indent=2))
phase=[]
for begin in range(0,int(math.ceil(duration)),300):
    stop=min(begin+300,duration);i=int(np.argmin(abs(t-begin)));j=int(np.argmin(abs(t-stop)))
    phase.append({'begin_s':begin,'end_s':stop,'distance_m':float(distance[j]-distance[i]),'sampled_observation_volume_added_m3':float(volume[j]-volume[i])})
speed=np.hypot(np.diff(x),np.diff(y))/np.diff(t);still=speed<.02;intervals=[];i=0
while i<len(still):
    if not still[i]:i+=1;continue
    j=i
    while j+1<len(still) and still[j+1]:j+=1
    if t[j+1]-t[i]>=10:intervals.append({'begin_s':float(t[i]),'end_s':float(t[j+1]),'duration_s':float(t[j+1]-t[i]),'heading_total_change_rad':float(abs(np.diff(np.unwrap(arr('yaw')[i:j+2]))).sum())})
    i=j+1
(run/'PHASES.json').write_text(json.dumps({'phases':phase,'low_translation_intervals_at_least_10s':intervals},indent=2))
# Full raw-message integrity, actual clock advance, and frozen archive bytes.
recorded=collections.Counter();files=[];clock=[]
for path in sorted((run/'bag').glob('*.mcap')):
    with path.open('rb') as stream:
        for schema,channel,message in make_reader(stream,validate_crcs=True).iter_messages():
            recorded[channel.topic]+=1
            if channel.topic=='/clock' and start<=message.log_time/1e9<=end:
                endian='<' if message.data[1]&1 else '>';sec,ns=struct.unpack_from(endian+'iI',message.data,4);clock.append((message.log_time/1e9,sec+ns*1e-9))
    files.append({'file':path.name,'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
metadata=yaml.safe_load((run/'bag/metadata.yaml').read_text())['rosbag2_bagfile_information'];expected=collections.Counter({e['topic_metadata']['name']:e['message_count'] for e in metadata['topics_with_message_count']});assert recorded==expected
frozen=json.loads((run/'FREEZE.json').read_text());archive_hashes={}
with tarfile.open(run/'frozen_runtime.tar.gz') as archive:
    for member in archive:
        if member.isfile():archive_hashes['/'+member.name]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
assert archive_hashes==frozen
clock.sort()
if len(clock)>1:analysis.update(sim_time_advanced_s=clock[-1][1]-clock[0][1],sim_real_time_factor=(clock[-1][1]-clock[0][1])/(clock[-1][0]-clock[0][0]))
(run/'ANALYSIS.json').write_text(json.dumps(analysis,indent=2))
(run/'RECORDING_VALIDATION.json').write_text(json.dumps({'messages':sum(recorded.values()),'files':files,'topic_counts':dict(recorded),'available_crc_checks_passed':True,'metadata_counts_match':True,'frozen_archive_matches_manifest':True,'frozen_files':len(frozen)},indent=2))
lines=(run/'simulation.log').read_text(errors='replace').splitlines();errors=[line for line in lines if 'process has died' in line];processes=[]
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():continue
    try:
        argv=(proc/'cmdline').read_bytes().split(b'\0');environ=(proc/'environ').read_bytes().split(b'\0')
        if not argv or Path(argv[0].decode()).name not in ['gzserver','gzmaster','vehicleSimulator','localPlanner','pathFollower','tare_planner_node','Xvfb']:continue
        if b'ROS_DOMAIN_ID=205' in environ or b'DISPLAY=:109' in environ:processes.append({'pid':int(proc.name),'argv':[e.decode(errors='replace') for e in argv if e]})
    except (OSError,UnicodeError):pass
(run/'CLEANUP.json').write_text(json.dumps({'clean_child_exit':not errors,'child_errors':errors,'relevant_processes_remaining':processes,'launcher_codes':result['exit_codes']},indent=2))
ledger=json.loads((root/'BUDGET.json').read_text());ledger.update(status='closed' if len(ledger['attempts'])>=ledger.get('planned_reference_runs',1) else 'active',used_attempts=len(ledger['attempts']),result=str(run/'RESULT.json'));(root/'BUDGET.json').write_text(json.dumps(ledger,indent=2))
# Compare trajectories descriptively, with configuration caveats in report.
fig,axes=plt.subplots(1,3,figsize=(15,4.5))
previous=Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01')
for label,path,color,offset in [('HT task-end',previous,'#94a3b8',.1725),('Native reference',run,'#0f766e',0.)]:
    data=list(csv.DictReader((path/'observations/metrics.csv').open()));values=lambda k:np.array([float(r[k]) for r in data]);tt=values('elapsed_s');xx=values('x')-offset*np.cos(values('yaw'));yy=values('y')-offset*np.sin(values('yaw'))
    axes[0].plot(xx,yy,label=label,color=color);axes[1].plot(tt,values('distance_m'),label=label,color=color);axes[2].plot(tt,values('sampled_free_volume_m3'),label=label,color=color)
axes[0].set(xlabel='World X (m)',ylabel='World Y (m)',title='Native configuration differs',aspect='equal');axes[1].set(xlabel='Wall time (s)',ylabel='Recorded distance (m)',title='Actual distance');axes[2].set(xlabel='Wall time (s)',ylabel='Observation proxy (m3)',title='Not ground-truth coverage')
for ax in axes:ax.grid(alpha=.2);ax.legend()
fig.tight_layout();fig.savefig(run/'comparison.png',dpi=150);plt.close(fig)
print(json.dumps({'analysis':analysis,'return':returned,'messages':sum(recorded.values()),'frozen_files':len(frozen),'remaining_processes':processes},indent=2),flush=True)
