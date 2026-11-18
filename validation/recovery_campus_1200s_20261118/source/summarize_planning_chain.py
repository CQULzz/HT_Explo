from pathlib import Path
import json,csv,collections
r=Path('/home/lzz/ht_recovery_campus_1200s_20261118/runs/recovery_campus_1200s_01');rows=list(csv.DictReader((r/'observations/metrics.csv').open()));start=json.loads((r/'observations/START.json').read_text())['clock'];end=float(rows[-1]['time']);latest={};selection=[]
for line in (r/'observations/events.jsonl').open():
 e=json.loads(line)
 if not start<=e['time']<=end:continue
 if e['kind'] in ['/ht_minimal/local_selection','/ht_minimal/localPlanner','/ht_minimal/pathFollower','/ht_minimal/command_audit','waypoint','local_path','/ht_minimal/recovery']:latest[e['kind']]=e
 if e['kind']=='/ht_minimal/local_selection' and e['time']>=end-30:selection.append(e)
rejections=collections.Counter()
for e in selection:rejections.update(e['data'].get('rejections',{}))
result={'window_end_elapsed_s':float(rows[-1]['elapsed_s']),'last30s_local_selection_messages':len(selection),'last30s_local_no_path_messages':sum(not e['data'].get('path_found',False) for e in selection),'last30s_sum_candidate_rejections_not_unique_poses':dict(rejections),'latest_records':latest,'interpretation':'Distinguish localPlanner candidate rejection from pathFollower gate approval of a zero velocity command; HT_ALLOWED on zero output does not establish route feasibility.'};(r/'PLANNING_CHAIN_DIAGNOSIS.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='latest_records'},indent=2))
