from pathlib import Path
import json,csv,collections,shutil,hashlib
r=Path('/home/lzz/ht_execution_300s_20261113');run=r/'runs/execution_300s_02'
rows=list(csv.DictReader((run/'observations/metrics.csv').open()))
events=[];counts=collections.Counter();reasons=collections.Counter()
for line in (run/'observations/events.jsonl').open():
    e=json.loads(line);counts[e['kind']]+=1
    if e['kind']=='/ht_minimal/recovery':events.append(e)
    if e['kind']=='/ht_minimal/command_audit':reasons[e['data'].get('reason','unknown')]+=1
last=rows[-1];cut=min(rows,key=lambda v:abs(float(v['elapsed_s'])-(float(last['elapsed_s'])-30)))
result={'last_30s_distance_m':float(last['distance_m'])-float(cut['distance_m']),'recovery_events':events,'event_counts':dict(counts),'command_reasons':dict(reasons),'stationary_samples':sum(abs(float(v['cmd_linear']))<.001 and abs(float(v['cmd_angular']))<.001 for v in rows),'total_samples':len(rows),'data_path':str(run)}
(run/'ANALYSIS.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
out=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/execution_300s_20261113')
out.mkdir(exist_ok=True)
for name in ['RESULT.json','ANALYSIS.json','COMMAND_AUDIT.json','FREEZE.json','ENVIRONMENT.json','COMMANDS.json','pathFollower.yaml','localPlanner.yaml','tare_planner_node.yaml','cupy_to_ht_bridge.yaml']:
    if (run/name).exists():shutil.copy2(run/name,out/name)
for name in ['metrics.csv','SUMMARY.json','START.json']:shutil.copy2(run/'observations'/name,out/name)
for name in ['ctest.log','gpu_preflight.log','renderer.txt','RESTORE.json','CANDIDATE_SOURCE.json']:
    if (r/'setup'/name).exists():shutil.copy2(r/'setup'/name,out/name)
shutil.copy2(r/'BUDGET.json',out/'BUDGET.json')
(out/'.gitattributes').write_text('*.csv -text -whitespace\n*.log -text -whitespace\n')
