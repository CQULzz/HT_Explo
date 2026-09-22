#!/usr/bin/env python3
"""Assert integration behavior from recorded trials; never assert an HT performance gain."""
import argparse
import json
import math
from pathlib import Path


def check(root, require_completion=False, require_outage=False):
    protocol=json.loads((root/'protocol.json').read_text())
    findings=[]
    for condition,rep in protocol['order']:
        case=root/f'{condition}_{rep}'
        data=json.loads((case/'metrics.json').read_text())
        rows=data['samples']
        assert data['final'] and rows[-1]['t']>=protocol['duration_s']-.5, f'{case}: incomplete recording'
        assert rows[-1]['scans']>=protocol['duration_s']*3, f'{case}: insufficient scans'
        if require_completion:
            assert data.get('mission_completed') is True, f'{case}: mission not completed'
            home=protocol['terrain']['spawn_ground_xyz']
            distance=math.dist(rows[-1]['position'][:2],home[:2])
            assert distance<=.55, f'{case}: completion away from home ({distance:.3f} m)'
            assert abs(rows[-1]['speed_command'])<.05, f'{case}: still moving'
        degraded=[r for r in rows if r.get('execution_status')=='GEOMETRIC_FALLBACK']
        assert all(r.get('requested_speed_m_s') is not None and r['requested_speed_m_s']<=.20001
                   for r in degraded), f'{case}: excessive or unrecorded fallback speed request'
        held=[r for r in rows if r.get('execution_status','').startswith(('HT_MAP_', 'HT_UNCALIBRATED', 'BASE_SENSOR_FAULT', 'FALLBACK_BUDGET_EXHAUSTED'))]
        assert all(r.get('requested_speed_m_s')==0 for r in held), f'{case}: nonzero speed during hold'
        if condition=='ht':
            assert all(r['allowed'] is False for r in held), f'{case}: navigation allowed during fault'
            assert rows[-1]['planar_distance_m']>1, f'{case}: failed to leave startup area'
        if require_outage and condition=='ht':
            events=json.loads((case/'fault_injection.json').read_text())
            assert [e['event'] for e in events]==['pause_ht','resume_ht']
            stale=[r for r in rows if r.get('execution_status')=='HT_MAP_STALE']
            assert stale, f'{case}: did not hold on stale map'
            assert any(r['allowed'] is True and r['t']>max(v['t'] for v in stale) for r in rows), f'{case}: no recovery'
        findings.append({'case':case.name,'completed':data.get('mission_completed'),
                         'distance_m':rows[-1]['planar_distance_m'],'fallback_samples':len(degraded),
                         'fault_hold_samples':len(held)})
    return findings


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    parser.add_argument('--require-completion',action='store_true')
    parser.add_argument('--require-outage',action='store_true')
    args=parser.parse_args()
    result={'passed':True,'checks':check(args.results,args.require_completion,args.require_outage)}
    (args.results/'regression_checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
