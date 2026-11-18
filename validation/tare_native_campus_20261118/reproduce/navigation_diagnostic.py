from pathlib import Path
import json,csv,math
roots=[Path('/home/lzz/tare_native_campus_20261118/runs/native_campus_01'),Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02')]
for run in roots:
 latest={};counts={};nonfinite=[]
 for line in (run/'observations/events.jsonl').open():
  e=json.loads(line);k=e['kind'];counts[k]=counts.get(k,0)+1
  if k in ['waypoint','local_path','finish_transition']:latest[k]=e
  if k=='waypoint' and any(not math.isfinite(v) for v in e['data'].values() if isinstance(v,(int,float))):nonfinite.append(e)
 result={'case':run.name,'latest':latest,'event_counts':counts,'nonfinite_waypoints':nonfinite}
 (run/'NATIVE_NAVIGATION_DIAGNOSTIC.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
