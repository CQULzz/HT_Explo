#!/usr/bin/env python3
"""Check saved motion/fault-injection records and write portable evidence."""
import json
from pathlib import Path
import statistics


def summarize(path):
    data = json.loads(path.read_text())
    rows = data['samples']
    result = dict(duration_s=rows[-1]['t'], distance_m=rows[-1]['distance'],
                  scans=rows[-1]['scans'], waypoint_messages=rows[-1]['waypoints'],
                  allowed_messages=rows[-1]['allowed_messages'], phases=[])
    start = 0.0
    for name, duration in data['phases']:
        phase = [r for r in rows if start <= r['t'] < start+duration]
        settled = [r for r in phase if r['t'] >= start+3.0]
        detail = dict(name=name, start_s=start, duration_s=duration,
                      distance_m=phase[-1]['distance']-phase[0]['distance'],
                      max_settled_speed=max((abs(r['speed']) for r in settled), default=0),
                      allowed_after_settling=any(r['allowed'] is True for r in settled))
        if name not in ('valid', 'off'):
            denied = [r for r in phase if r['allowed'] is False]
            detail['first_denial_s'] = denied[0]['t']-start if denied else None
            detail['all_settled_denied'] = bool(settled) and all(r['allowed'] is False for r in settled)
            detail['max_settled_goal_distance_m'] = max(r['waypoint_distance'] or 0 for r in settled)
        result['phases'].append(detail)
        start += duration
    timings = [r['runtime'] for r in rows if r['runtime'] is not None]
    result['reported_runtime_median_s'] = statistics.median(timings) if timings else None
    return result


def main():
    root = Path(__file__).resolve().parent/'results'
    results = {p.parent.name: summarize(p) for p in sorted(root.glob('*/metrics.json'))}
    assert results['baseline']['distance_m'] > 10, 'Baseline did not move'
    fixed = results['ht_fixed']
    assert fixed['phases'][0]['distance_m'] > 5, 'HT still stalls in the initial valid phase'
    for phase in fixed['phases']:
        if phase['name'] == 'valid':
            assert phase['distance_m'] > 0.1, f'No recovery in {phase}'
        else:
            assert phase['all_settled_denied'], f'Permission not revoked: {phase}'
            assert phase['max_settled_speed'] < 0.01, f'Controller did not stop: {phase}'
            assert phase['max_settled_goal_distance_m'] < 0.1, f'Goal not held: {phase}'
    if 'uncalibrated' in results:
        held=results['uncalibrated']
        assert held['distance_m'] < 0.01 and held['allowed_messages'] == 0
    if 'packaged_smoke' in results:
        assert results['packaged_smoke']['distance_m'] > 3, 'Installed node did not move'
    (root/'summary.json').write_text(json.dumps(results, indent=2)+'\n')
    print(json.dumps(results, indent=2))


if __name__ == '__main__':
    main()
