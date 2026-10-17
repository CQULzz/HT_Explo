#!/usr/bin/env python3
"""Classify recorded completion decisions without interpreting hints as coverage truth."""
import argparse
import csv
import json
from pathlib import Path
import re


def read_rows(trial):
    origin=json.loads((trial/'current/measurement_started.json').read_text())['wall_time']
    rows=[]
    for line in (trial/'current/tare.log').read_text().splitlines():
        if 'COMPLETION_AUDIT ' not in line:continue
        stamp=re.search(r'\[(\d+\.\d+)\]',line)
        if not stamp:continue
        row={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line.split('COMPLETION_AUDIT ',1)[1])}
        row['time_s']=float(stamp[1])-origin
        if row['time_s']<0:continue
        row['valuable_ht_route']=int(row['ht_poses']>1 and (
            row['ht_gain']>=row['min_points'] or row['ht_frontier']>=row['min_frontier']))
        row['completion_trigger']=int(row['global_return'] and row['local_complete'] and row['time_s']>5)
        row['contradictory_local_hint']=int(row['local_complete'] and row['valuable_ht_route'])
        rows.append(row)
    return rows


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trial',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();rows=read_rows(args.trial)
    if not rows:raise RuntimeError('No completion evidence yet')
    for r in rows:
        assert r['global_exploring']==r['local_delegated']+r['eligible']
        assert r['eligible']==r['connected']+r['unreachable']
    triggers=[r for r in rows if r['completion_trigger']]
    result=dict(source=str(args.trial.resolve()),rows=len(rows),
        last_row=rows[-1],first_trigger=triggers[0] if triggers else None,
        local_hint_conflicts_with_valuable_ht_route=sum(r['contradictory_local_hint'] for r in rows),
        premature_trigger_with_proven_valuable_route=any(r['valuable_ht_route'] for r in triggers),
        trigger_with_pending_unconnected_global_cells=any(r['unreachable']>0 for r in triggers),
        trigger_with_locally_delegated_global_cells=any(r['local_delegated']>0 for r in triggers),
        caveat='A valuable_ht_route means a route passed the current planner checks and its selected viewpoint meets the existing coverage threshold. It is not a ground-truth coverage/real-world safety guarantee. Raw candidate counts alone do not establish reachability.')
    args.output.mkdir(parents=True,exist_ok=True)
    (args.output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    with (args.output/'completion_rows.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
