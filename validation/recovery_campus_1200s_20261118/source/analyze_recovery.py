from pathlib import Path
import collections, json, math
root=Path('/home/lzz/ht_recovery_campus_1200s_20261118')
run=root/'runs/recovery_campus_1200s_01'
start=json.loads((run/'observations/START.json').read_text())['clock']
events=[];finish=None;plans={};completed=[];last_completed=0;states=collections.Counter()
with (run/'observations/events.jsonl').open() as f:
 for line in f:
  e=json.loads(line)
  if e['time']<start:continue
  if e['kind']=='finish_transition' and e['data'].get('finish') and finish is None:finish=e['time']-start
  if e['kind']!='/ht_minimal/recovery':continue
  d=e['data'];events.append(e);states[d['state']]+=1
  if d['active'] and d['plans'] not in plans:plans[d['plans']]={'begin_elapsed_s':e['time']-start,'start_xy':[d['x'],d['y']],'finish_phase':d.get('exploration_finished'),'search_outcome':d.get('search_outcome'),'search_progress_m':d.get('search_progress_m'),'initial_goal_xy':[d['goal_x'],d['goal_y']]}
  if d['completed']>last_completed:
   number=d['plans'];item=plans.get(number,{}).copy();item.update(plan=number,end_elapsed_s=e['time']-start,end_xy=[d['x'],d['y']],reported_progress_m=d.get('progress_m'),finish_phase_at_end=d.get('exploration_finished'))
   if 'start_xy' in item:
    item['net_displacement_m']=math.hypot(d['x']-item['start_xy'][0],d['y']-item['start_xy'][1]);item['duration_s']=item['end_elapsed_s']-item['begin_elapsed_s']
   completed.append(item);last_completed=d['completed']
last=events[-1]['data'] if events else None
result={'first_finish_elapsed_s':finish,'recovery_messages':len(events),'diagnostic_states':dict(states),'plans_observed':len(plans),'completed_plans':completed,'completed_after_finish':sum(p['end_elapsed_s']>=finish for p in completed) if finish is not None else 0,'partial_progress_plans_observed':sum(p.get('search_outcome')=='PARTIAL_PROGRESS' for p in plans.values()),'plans':plans,'last_recovery':last,'scope':'Plan/completion events from online recovery diagnostics; a completed prefix is not full return or ground-truth coverage.'}
(run/'RECOVERY_ANALYSIS.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['plans','completed_plans','last_recovery']},indent=2))
