from pathlib import Path
import json,collections,csv
r=Path('/home/lzz/ht_campus_repeat_1200s_20261118/runs/explicit_labels_campus_repeat_1200s_01');rows=list(csv.DictReader((r/'observations/metrics.csv').open()));end=float(rows[-1]['time']);latest={};malformed=[]
for line in (r/'observations/events.jsonl').open():
 e=json.loads(line)
 if e['kind'] in ['/ht_minimal/local_selection','/ht_minimal/localPlanner','/ht_minimal/pathFollower','/ht_minimal/command_audit','waypoint','local_path','/ht_minimal/recovery']:latest[e['kind']]=e
 if e['kind']=='malformed_diagnostic' and e['time']>end-30:malformed.append(e)
print(json.dumps(latest,indent=2));print('RECENT_MALFORMED',json.dumps(malformed[-1:]))
