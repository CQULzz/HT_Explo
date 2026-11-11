from pathlib import Path
import json,math,csv,collections
ROOT=Path('/home/lzz/ht_recovery_20261111');all_results={}
for name in ['cmu_recovery_300s_01','cmu_recovery_300s_02']:
 run=ROOT/'runs'/name;start=json.loads((run/'observations/START.json').read_text())['clock'];events=[];counts=collections.Counter()
 for line in (run/'observations/events.jsonl').open():
  try:x=json.loads(line)
  except json.JSONDecodeError:continue
  if x['kind']=='/ht_minimal/recovery':events.append(x['data']);counts[x['data']['state']]+=1
 episodes={}
 for e in events:
  if not e['plans']:continue
  i=e['plans']
  if e['state']=='EXECUTING' and i not in episodes:episodes[i]={'start':e,'end':None}
  if i in episodes and e['state']=='COMPLETED' and episodes[i]['end'] is None:episodes[i]['end']=e
 results=[]
 for i,pair in episodes.items():
  a,b=pair['start'],pair['end'];r={'plan':i,'start_elapsed_s':a['time']-start,'start':a,'completed':b is not None,'end':b}
  if b:
   goal=(a['goal_x'],a['goal_y']);r.update(end_elapsed_s=b['time']-start,duration_s=b['time']-a['time'],net_displacement_m=math.dist((a['x'],a['y']),(b['x'],b['y'])),fixed_initial_goal_distance_reduction_m=math.dist((a['x'],a['y']),goal)-math.dist((b['x'],b['y']),goal))
  else:r['limitation']='Candidate01 omitted an exit event; source and waypoint timestamps show the incorrect 3s goal-expiry path. Not counted as completed.'
  results.append(r)
 rows=list(csv.DictReader((run/'observations/metrics.csv').open()));moving=[r for r in rows if abs(float(r['cmd_linear']))+abs(float(r['cmd_angular']))>1e-8]
 all_results[name]={'state_counts':counts,'episodes':results,'last_moving_command_elapsed_s':float(moving[-1]['elapsed_s']) if moving else None,'scope':'progress_m is distance from the last recovery origin and can grow after handover. Episode movement uses only its EXECUTING start and its own first COMPLETED event, excluding later normal driving and invalid-start diagnostics.'}
(ROOT/'analysis/RECOVERY_EPISODES.json').write_text(json.dumps(all_results,indent=2));print(json.dumps(all_results,indent=2))
