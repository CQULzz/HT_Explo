#!/usr/bin/env python3
"""Analyze complete fixed-duration trials; never include unfinished pilots."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from coverage_metrics import decode_keys


def low_motion_intervals(samples, duration, finish_time=None):
    """At least five consecutive 1 s bins with planar travel below 0.05 m/s.

    Ignore the first 5 s and bins after a completion signal. This includes
    intentional rotation/planning waits and must not be called a collision count.
    """
    end = min(duration, finish_time) if finish_time is not None else duration
    grid = np.arange(5, int(np.floor(end))+1, dtype=float)
    if len(grid) < 2:
        return []
    t = [s['t'] for s in samples]
    distance = np.interp(grid, t, [s['planar_distance_m'] for s in samples])
    slow = np.diff(distance) < 0.05
    intervals = []
    start = None
    for i, flag in enumerate(np.r_[slow, False]):
        if flag and start is None:
            start = i
        if not flag and start is not None:
            if i-start >= 5:
                intervals.append(dict(start_s=float(grid[start]), end_s=float(grid[i]),
                                      duration_s=float(i-start)))
            start = None
    return intervals


def summarize(data, condition, repetition):
    samples = data['samples']
    duration = data['duration_requested_s']
    if not data['final'] or samples[-1]['t'] < duration-0.5:
        raise ValueError('Incomplete trial must not be summarized')
    first, last = samples[0], samples[-1]
    t = np.array([s['t'] for s in samples])
    hits = np.array([s['new_reference_hits'] for s in samples])
    runtime = np.array([c['overall_ms'] for c in data['planning_cycles']])
    if not len(runtime):
        raise ValueError('Missing overall planning runtime measurements')
    slow = low_motion_intervals(samples, duration, data['finish_time_s'])
    distances = np.array([s['planar_distance_m'] for s in samples])
    steps = np.diff(t)
    allowed = [s['allowed'] for s in samples[:-1]]
    denied_time = sum(dt for dt, flag in zip(steps, allowed) if flag is False)
    positions = np.array([s['position'] for s in samples])
    return dict(
        condition=condition, repetition=repetition, duration_s=last['t'],
        initial_reference_hits=first['reference_hits'],
        reference_hits=last['reference_hits'], new_reference_hits=last['new_reference_hits'],
        reference_hit_pct=last['reference_hit_pct'],
        mean_new_reference_hits_over_time=float(np.trapz(hits, t)/duration),
        new_hits_last_60s=float(hits[-1]-np.interp(max(0,duration-60),t,hits)),
        observed_voxels=last['observed_voxels'], new_observed_voxels=last['new_observed_voxels'],
        cmu_hit_voxel_volume_m3=last['cmu_hit_voxel_volume_m3'],
        distance_m=last['distance_m'], planar_distance_m=last['planar_distance_m'],
        new_reference_hits_per_planar_m=last['new_reference_hits']/max(distances[-1],1e-9),
        low_motion_intervals=slow, low_motion_total_s=sum(s['duration_s'] for s in slow),
        longest_low_motion_s=max([s['duration_s'] for s in slow],default=0),
        ht_denied_time_s=float(denied_time) if any(a is not None for a in allowed) else None,
        planning_cycles=len(runtime), runtime_median_ms=float(np.median(runtime)),
        runtime_p95_ms=float(np.percentile(runtime,95)), runtime_max_ms=float(max(runtime)),
        scan_rate_hz=last['scans']/last['t'],
        scan_age_p95_s=float(np.percentile([s['scan_age_s'] for s in samples if s['scan_age_s'] is not None],95)),
        max_sample_gap_s=float(max(steps)),
        sim_clock_rate=((last['sim_clock']-first['sim_clock'])/(last['t']-first['t'])
                        if last['sim_clock'] is not None and first['sim_clock'] is not None else None),
        finished=data['finished'], finish_time_s=data['finish_time_s'],
        min_sensor_z_m=float(min(positions[:,2])), max_sensor_z_m=float(max(positions[:,2])),
        final_position_m=last['position'])


GROUP_METRICS = [
    'new_reference_hits','reference_hit_pct','mean_new_reference_hits_over_time',
    'new_hits_last_60s','new_observed_voxels','cmu_hit_voxel_volume_m3',
    'planar_distance_m','new_reference_hits_per_planar_m','low_motion_total_s',
    'longest_low_motion_s','runtime_median_ms','runtime_p95_ms',
    'scan_rate_hz','scan_age_p95_s','sim_clock_rate']


def audit_trial(root, data, reference, duration):
    """Recount archived voxel sets independently of the online counters."""
    rows=data['samples']
    if data['duration_requested_s'] != duration or rows[-1]['scans'] < duration*4:
        raise ValueError(f'{root.name}: duration or scan throughput mismatch')
    if data['reference_voxels'] != len(reference):
        raise ValueError(f'{root.name}: inconsistent reference denominator')
    for key in ('t','reference_hits','new_reference_hits','observed_voxels',
                'new_observed_voxels','planar_distance_m'):
        if np.any(np.diff([r[key] for r in rows]) < -1e-9):
            raise ValueError(f'{root.name}: non-monotonic {key}')
    observed=np.load(root/'observed_voxels.npz')['keys']
    unique_count=len(np.unique(observed))
    matched=len(np.intersect1d(observed,reference,assume_unique=True))
    if unique_count != len(observed) or unique_count != rows[-1]['observed_voxels']:
        raise ValueError(f'{root.name}: archived observed voxel mismatch')
    if matched != rows[-1]['reference_hits']:
        raise ValueError(f'{root.name}: archived reference intersection mismatch')
    for row in rows:
        if row['reference_hits']-row['new_reference_hits'] != rows[0]['reference_hits']:
            raise ValueError(f'{root.name}: inconsistent initial coverage subtraction')
    return dict(archived_observed_voxels=unique_count,archived_reference_hits=matched,
                coverage_counters_match=True,monotonic_samples=True)


def aggregate(trials):
    groups = {}
    for condition in ('baseline','ht'):
        selected = [s for s in trials if s['condition'] == condition]
        groups[condition] = dict(n=len(selected))
        for key in GROUP_METRICS:
            values = [s[key] for s in selected if s[key] is not None]
            groups[condition][key] = dict(
                mean=float(np.mean(values)),
                sample_sd=float(np.std(values,ddof=1)) if len(values)>1 else None,
                min=float(min(values)),max=float(max(values)))
    differences = {}
    for key in GROUP_METRICS:
        base, ht = (groups[c][key]['mean'] for c in ('baseline','ht'))
        differences[key] = dict(absolute=ht-base,
                               percent=100*(ht/base-1) if base else None)
    return groups,differences


def plots(root, protocol, all_data):
    plt.rcParams.update({'font.size':10,'figure.dpi':150})
    fig, axes = plt.subplots(2,2,figsize=(12,10),constrained_layout=True)
    colors = {'baseline':'#2274a5','ht':'#dc762c'}
    for axis, key, ylabel in (
            (axes[0,0],'new_reference_hits','New reference surface voxels (0.5 m)'),
            (axes[0,1],'planar_distance_m','Planar travel (m)')):
        for condition in ('baseline','ht'):
            grid = np.arange(0,protocol['duration_s']+0.001,1)
            curves = []
            for (cond,rep), data in all_data.items():
                if cond != condition:
                    continue
                rows=data['samples']
                curve=np.interp(grid,[r['t'] for r in rows],[r[key] for r in rows])
                curves.append(curve)
                axis.plot(grid,curve,color=colors[condition],alpha=.18,lw=.8)
            curves=np.array(curves)
            axis.fill_between(grid,curves.min(axis=0),curves.max(axis=0),
                              color=colors[condition],alpha=.12)
            axis.plot(grid,curves.mean(axis=0),color=colors[condition],lw=2,
                      label=f'{condition.upper()} (n={len(curves)})')
        axis.set(xlabel='Time since start (wall s)',ylabel=ylabel)
        axis.grid(alpha=.2)
        axis.legend()
    reference=decode_keys(np.load(root/'reference_voxels.npz')['keys'])
    positions=np.concatenate([np.array([r['position'] for r in d['samples']]) for d in all_data.values()])
    lo,hi=positions[:,:2].min(axis=0)-10,positions[:,:2].max(axis=0)+10
    within=np.all((reference[:,:2]>=lo)&(reference[:,:2]<=hi),axis=1)
    backdrop=reference[within]
    backdrop=backdrop[::max(1,len(backdrop)//30000)]
    for axis, condition in zip(axes[1],('baseline','ht')):
        axis.scatter(backdrop[:,0],backdrop[:,1],s=.3,c='#c9cdd0',rasterized=True)
        for (cond,rep),data in all_data.items():
            if cond != condition:
                continue
            p=np.array([r['position'] for r in data['samples']])
            axis.plot(p[:,0],p[:,1],lw=1.5,label=f'Run {rep}')
            axis.scatter(p[-1,0],p[-1,1],s=22,marker='s')
        axis.scatter(0,0,c='black',s=60,marker='*',label='Start')
        axis.set(xlim=(lo[0],hi[0]),ylim=(lo[1],hi[1]),xlabel='World X (m)',ylabel='World Y (m)',
                 title=f'{condition.upper()}: XY paths, reference surface projection')
        axis.set_aspect('equal',adjustable='box')
        axis.legend(fontsize=8)
    fig.suptitle('CMU Garage exploration: HT off vs uniform synthetic HT\n'
                 'Curves: mean and observed min-max; coverage is surface hits, not free-space completion')
    fig.savefig(root/'exploration_comparison.png')
    fig.savefig(root/'exploration_comparison.pdf')
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('results',type=Path)
    parser.add_argument('--baseline-results',type=Path,
                        help='Reuse separately archived HT-off trials for a follow-up comparison')
    args=parser.parse_args()
    root=args.results.resolve()
    protocol=json.loads((root/'protocol.json').read_text())
    reference=np.load(root/'reference_voxels.npz')['keys']
    if len(reference) != protocol['reference_voxels'] or len(np.unique(reference)) != len(reference):
        raise ValueError('Reference archive does not match protocol')
    all_data={}
    trials=[]
    audit={}
    baseline_provenance=None
    if args.baseline_results:
        if any(condition=='baseline' for condition,_ in protocol['order']):
            raise ValueError('Current cohort already has baseline trials')
        baseline_root=args.baseline_results.resolve()
        baseline_protocol=json.loads((baseline_root/'protocol.json').read_text())
        for key in ('duration_s','reference_ply_sha256','reference_voxels','speed_limit_m_s','ht_map'):
            if protocol[key] != baseline_protocol[key]:
                raise ValueError(f'Historical baseline protocol differs: {key}')
        baseline_provenance=dict(path=str(baseline_root),protocol=baseline_protocol,
                                 note='Reused historical baseline; follow-up trials were not interleaved with it.')
        for condition,repetition in baseline_protocol['order']:
            if condition != 'baseline':
                continue
            case=baseline_root/f'{condition}_{repetition}'
            data=json.loads((case/'metrics.json').read_text())
            all_data[(condition,repetition)]=data
            trials.append(summarize(data,condition,repetition))
            audit[case.name]=audit_trial(case,data,reference,protocol['duration_s'])
    for condition,repetition in protocol['order']:
        case=root/f'{condition}_{repetition}'
        data=json.loads((case/'metrics.json').read_text())
        all_data[(condition,repetition)]=data
        trials.append(summarize(data,condition,repetition))
        audit[case.name]=audit_trial(case,data,reference,protocol['duration_s'])
    if set(condition for condition,_ in all_data) != {'baseline','ht'}:
        raise ValueError('Need both conditions; use --baseline-results for an HT-only follow-up')
    groups,differences=aggregate(trials)
    result=dict(protocol=protocol,trials=trials,groups=groups,ht_minus_baseline=differences,audit=audit,
                historical_baseline=baseline_provenance,
                interpretation='Reference surface voxel hits, not accessible free-space coverage. '
                               'Independent stochastic runs; group n is explicit; no significance inference.')
    (root/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    fields=[key for key,value in trials[0].items() if not isinstance(value,(list,dict))]
    with (root/'summary.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,extrasaction='ignore')
        writer.writeheader()
        writer.writerows(trials)
    plots(root,protocol,all_data)
    print(json.dumps(dict(groups=groups,ht_minus_baseline=differences),indent=2))


if __name__=='__main__':
    main()
