from pathlib import Path
import csv,json
r=Path('/home/lzz/tare_native_campus_20261118/runs/native_campus_01');p=r/'observations/metrics.csv'
if p.exists():
 rows=list(csv.DictReader(p.open()));print('LATEST',json.dumps({k:rows[-1][k] for k in ['elapsed_s','distance_m','x','y','cmd_linear','cmd_angular','finish','ht_age_s']}) if rows else 'waiting for readiness')
else:print('waiting for readiness')
p=r/'observations/events.jsonl'
if p.exists():
 with p.open('rb') as f:f.seek(max(0,p.stat().st_size-600000));raw=f.read().splitlines()
 latest={}
 for line in raw:
  try:e=json.loads(line)
  except (ValueError,UnicodeError):continue
  if e['kind'] in ['/ht_minimal/recovery','/ht_minimal/local_selection']:latest[e['kind']]=e
 for kind,e in latest.items():
  d=e['data'];keys=['state','active','plans','completed','invalidated','search_failures','exploration_finished','goal_distance_m','search_outcome','search_progress_m','path_found','ht_checked_groups','ht_allowed_groups','rejections'];print(kind,json.dumps({k:d[k] for k in keys if k in d}))
p=r/'ACTUAL_NAVIGATION.json'
if p.exists():print('ACTUAL_NAVIGATION_VERIFIED',len(json.loads(p.read_text())))
p=r/'RESULT.json'
if p.exists():print('RESULT',p.read_text())

p=r/'simulation.log'
if p.exists():
 lines=[x for x in p.read_text(errors='replace').splitlines() if any(k in x for k in ['Exploration finished','exploration finished','Exploration is finished','Returning home'])];print('PLANNER',lines[-1:] if lines else 'not yet')

p=r/'observations/RUN_STATUS.json'
if p.exists():
 try:
  status=json.loads(p.read_text());print('TASK_STATUS',json.dumps({k:status[k] for k in ['outcome','distance_to_initial_m','first_finish_elapsed_s','home_hold_elapsed_s','inputs_fresh']}))
 except json.JSONDecodeError:print('TASK_STATUS updating')
