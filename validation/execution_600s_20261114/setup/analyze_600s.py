from pathlib import Path
import json,csv,collections,shutil,hashlib,yaml
root=Path('/home/lzz/ht_600s_20261114');run=root/'runs/execution_600s_01'
out=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/execution_600s_20261114');out.mkdir(exist_ok=True)
rows=list(csv.DictReader((run/'observations/metrics.csv').open()));start=json.loads((run/'observations/START.json').read_text())
end=rows[-1];mid=min(rows,key=lambda r:abs(float(r['elapsed_s'])-300));tail=min(rows,key=lambda r:abs(float(r['elapsed_s'])-(float(end['elapsed_s'])-30)))
recovery=[];finish=[];reasons=collections.Counter();active=None;episodes=[]
for line in (run/'observations/events.jsonl').open():
    e=json.loads(line);d=e['data']
    if e['kind']=='finish_transition':finish.append(dict(elapsed_clock_s=e['time']-start['clock'],**d))
    if e['kind']=='/ht_minimal/command_audit':reasons[d.get('reason','unknown')]+=1
    if e['kind']=='/ht_minimal/recovery':
        recovery.append(e)
        if d['active'] and active is None:active=e
        if not d['active'] and active is not None:
            ad=active['data'];episodes.append({'begin':active,'end':e,'duration_clock_s':d['time']-ad['time'],'completed_increment':d['completed']-ad['completed'],'displacement_m':((d['x']-ad['x'])**2+(d['y']-ad['y'])**2)**.5});active=None
metrics={'duration_s':float(end['elapsed_s']),'distance_m':float(end['distance_m']),'free_volume_proxy_m3':float(end['sampled_free_volume_m3']),'first_300s':{'sample_time_s':float(mid['elapsed_s']),'distance_m':float(mid['distance_m']),'free_volume_proxy_m3':float(mid['sampled_free_volume_m3'])},'second_300s':{'distance_m':float(end['distance_m'])-float(mid['distance_m']),'free_volume_proxy_m3':float(end['sampled_free_volume_m3'])-float(mid['sampled_free_volume_m3'])},'last_30s_distance_m':float(end['distance_m'])-float(tail['distance_m']),'finish_transitions':finish,'command_reasons':dict(reasons),'recovery_events':recovery,'recovery_episodes':episodes,'active_recovery_at_end':active}
(out/'ANALYSIS.json').write_text(json.dumps(metrics,indent=2))
for name in ['RESULT.json','COMMAND_AUDIT.json','FREEZE.json','ENVIRONMENT.json','COMMANDS.json','pathFollower.yaml','localPlanner.yaml','tare_planner_node.yaml','cupy_to_ht_bridge.yaml','simulation.log','mapper.log','model.log','observer.log','bag.log']:
    if (run/name).exists():shutil.copy2(run/name,out/name)
for name in ['SUMMARY.json','START.json','metrics.csv']:shutil.copy2(run/'observations'/name,out/name)
for name in ['env.sh','run.py','simulation.launch.py','BUDGET.json','recording_qos.yaml','mapper_setup_4hz.yaml','mcap.yaml']:shutil.copy2(root/name,out/name)
(out/'setup').mkdir(exist_ok=True)
for name in ['prepare_600s.py','run_600s.sh','analyze_600s.py']:shutil.copy2(Path('/mnt/d/HT-Execution-300s/setup')/name,out/'setup'/name)
for p in (root/'setup').glob('*.log'):shutil.copy2(p,out/'setup'/p.name)
comparison={}
old=Path('/home/lzz/ht_repeat_20261114/runs/repeat_02')
for name in ['pathFollower.yaml','localPlanner.yaml','tare_planner_node.yaml','cupy_to_ht_bridge.yaml']:
    a=yaml.safe_load((old/name).read_text());b=yaml.safe_load((run/name).read_text());comparison[name]={'available':isinstance(b,dict),'equal_to_previous':a==b if isinstance(b,dict) else None}
(out/'PARAMETER_COMPARISON.json').write_text(json.dumps(comparison,indent=2))
(out/'.gitattributes').write_text('*.csv -text -whitespace\n*.log -text -whitespace\n')
print(json.dumps({k:v for k,v in metrics.items() if k not in ['recovery_events','recovery_episodes','active_recovery_at_end']},indent=2))
print('Recovery completed',max([e['data']['completed'] for e in recovery] or [0]),'episodes',len(episodes))
