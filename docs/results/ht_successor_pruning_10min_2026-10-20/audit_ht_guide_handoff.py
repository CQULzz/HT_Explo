#!/usr/bin/env python3
"""Read-only guide/task audit; old logs infer cells, new logs report task IDs."""
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path


def audit(trial):
    origin=json.loads((trial/'current/measurement_started.json').read_text())['wall_time']
    path=trial/'current/tare.log'
    cells={};previous=None;switches=[];states=[];plan_count=zero_gain=0
    for line in path.read_text(errors='replace').splitlines():
        stamp=re.search(r'\[(?:INFO|WARN)\] \[([\d.]+)\]',line)
        if not stamp:continue
        t=float(stamp[1])-origin
        if t>600:continue
        if 'HT_CELL_AUDIT ' in line:
            fields=dict(re.findall(r'(\w+)=([^ ]+)',line.split('HT_CELL_AUDIT ',1)[1]))
            cid=int(fields['cell']);xy=tuple(map(float,fields['xy'].strip('()').split(',')))
            cells[cid]=dict(t_s=t,xy=xy,status=int(fields['new']),reason=fields['reason'],
                            candidates=int(fields['candidates']),pending_gain=int(fields['pending_gain']))
        if t<0:continue
        if 'HT_GUIDE_TASK ' in line:
            fields=dict(re.findall(r'(\w+)=([^ ]+)',line.split('HT_GUIDE_TASK ',1)[1]))
            states.append(dict(t_s=t,task=int(fields['task']),in_tour=int(fields['in_tour']),
                               pending=int(fields['pending']),idle_s=float(fields['idle'])))
        if 'XYtheta exploration target=' in line:
            plan_count+=1
            zero_gain+=bool(re.search(r'gain=0\.0 ',line))
        selected=re.search(r'HT guide selected: \(([^)]+)\) global=(\d).*?(?: task=(-?\d+))?$',line)
        if not selected:continue
        task=re.search(r' task=(-?\d+)',line)
        goal=tuple(map(float,selected[1].split(',')))
        current=dict(t_s=t,goal=goal,global_guide=bool(int(selected[2])),
                     task=int(task[1]) if task else None)
        if previous:
            cid=previous['task']
            inferred=cid is None
            if inferred and cells:cid=min(cells,key=lambda k:math.dist(cells[k]['xy'],previous['goal']))
            state=cells.get(cid)
            switches.append(dict(t_s=t,old=previous,new=current,previous_task_cell=cid,
                                 inferred_cell_from_nearest_center=inferred,
                                 last_cell_evidence=state,
                                 evidence_age_s=t-state['t_s'] if state else None))
        previous=current
    pending=[s for s in switches if s['old']['global_guide'] and s['last_cell_evidence'] and
             s['last_cell_evidence']['status']==1]
    return dict(source=str(trial.resolve()),log_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                guide_switches=len(switches),global_switches_last_known_pending=len(pending),
                late_300_540_switches=sum(300<=s['t_s']<=540 for s in switches),
                delegated_pending_cycles=sum(not s['in_tour'] and s['pending'] for s in states),
                global_state_rows=len(states),logged_plan_rows=plan_count,zero_gain_plan_rows=zero_gain,
                switches=switches,task_states=states,
                limitations='Old task assignment inferred from nearest logged cell center; not exact internal tour replay. '
                'Last cell status is historical evidence, not physical coverage truth. Pending-goal switches may be '
                'legitimate stalls/completion or bootstrap promotion; counts alone do not establish a bug. '
                'New task rows are per planning callback, old plan rows throttled. '
                'The cumulative source-second free-voxel union must be audited separately.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('trial',type=Path)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=audit(args.trial);args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['switches','task_states']},indent=2))


if __name__=='__main__':main()
