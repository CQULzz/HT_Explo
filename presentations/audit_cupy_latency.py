#!/usr/bin/env python3
"""Audit observed mapper lock/callback timing without attributing wait to GPU compute."""
import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from std_msgs.msg import Int32MultiArray


def distribution(values):
    a=np.asarray(values,dtype=float)
    return dict(count=len(a),p50=float(np.median(a)),p95=float(np.quantile(a,.95)),max=float(a.max())) if len(a) else dict(count=0)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trial',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();trial=args.trial;out=args.output
    out.mkdir(parents=True,exist_ok=False)
    origin=json.loads((trial/'current/measurement_started.json').read_text())['wall_time']
    duration=json.loads((trial/'summary.json').read_text())['duration_s']
    trace=[json.loads(line) for line in (trial/'current/cupy_timing.jsonl').read_text().splitlines()]
    trace=[r for r in trace if 0<=r['wall_time']-origin<duration]
    lock=[r for r in trace if r['kind']=='map_lock'];callbacks=[r for r in trace if r['kind']=='callback']
    profiles=defaultdict(list)
    for r in lock:
        profiles[('map_lock',r['operation'])].append(r)
    for r in callbacks:
        profiles[('callback',r['operation'])].append(r)
    summary={}
    for (kind,name),records in profiles.items():
        keys=['wait_s','hold_s','cpu_s'] if kind=='map_lock' else ['elapsed_s','cpu_s']
        summary[kind+'/'+name]={key:distribution([r[key] for r in records]) for key in keys}
    # Pair contended acquisitions with overlapping observed critical sections.
    contenders=[]
    for r in lock:
        if r['wait_s']<.1:continue
        blockers=[]
        for s in lock:
            if s['thread']==r['thread']:continue
            overlap=min(r['acquired_monotonic'],s['released_monotonic'])-max(r['started_monotonic'],s['acquired_monotonic'])
            if overlap>0:
                blockers.append(dict(operation=s['operation'],overlap_s=overlap,hold_s=s['hold_s'],cpu_s=s['cpu_s']))
        contenders.append(dict(time_s=r['wall_time']-origin,operation=r['operation'],wait_s=r['wait_s'],overlapping_holders=blockers))
    with (trial/'health.csv').open() as stream:health=list(csv.DictReader(stream))
    health=[r for r in health if 0<=float(r['wall_time'])-origin<duration and r['map_source_age_s']]
    ht=json.loads((trial/'current/ht_diagnostics.json').read_text())
    ht=[r for r in ht if 0<=r['stamp_s']-origin<duration]
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(trial/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/runtime_breakdown']))
    runtime=[]
    while reader.has_next():
        _,data,ns=reader.read_next();t=ns/1e9-origin
        if 0<=t<duration:
            runtime.append(dict(time_s=t,ms=list(deserialize_message(data,Int32MultiArray).data)))
    names=['representation','viewpoint_sampling','local_search','global_TSP','trajectory','overall']
    breakdown={name:distribution([r['ms'][i]/1000 for r in runtime]) for i,name in enumerate(names)}
    ht_stats={key:distribution([r[key] for r in ht]) for key in ['source_age_at_callback_s','fusion_and_quality_s','support_and_history_publish_s','network_inference_s','ht_serialize_publish_s','elapsed_s']}
    result=dict(source=str(trial.resolve()),tested_commit=json.loads((trial/'manifest.json').read_text())['git_head'],
                mapper_profiles=summary,ht_profiles=ht_stats,planner_breakdown_s=breakdown,
                largest_lock_waits=sorted(contenders,key=lambda r:r['wait_s'],reverse=True)[:30],
                largest_critical_sections=sorted(lock,key=lambda r:r['hold_s'],reverse=True)[:20],
                stale_health_samples=[dict(time_s=float(r['wall_time'])-origin,age_s=float(r['map_source_age_s']),follower=r['follower_status']) for r in health if float(r['map_source_age_s'])>3],
                limitations='Timing wrapper adds recording overhead. Lock hold includes async GPU synchronization, Python/CPU and scheduling; low thread CPU does not prove GPU compute bottleneck. Overlap proves a holder occupied the same lock, not what caused its long wall time. Runtime breakdown uses existing node integer millisecond counters and may overlap components; bag receipt order is not exact subscriber callback order.')
    (out/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,axes=plt.subplots(4,1,figsize=(14,12),sharex=True,layout='constrained')
    axes[0].plot([float(r['wall_time'])-origin for r in health],[float(r['map_source_age_s']) for r in health],label='HT图年龄（1Hz探针）',lw=.8)
    axes[0].axhline(3,color='r',ls='--',label='3s保护阈值');axes[0].set_ylabel('年龄 / s');axes[0].legend()
    for name in sorted({r['operation'] for r in lock}):
        rows=[r for r in lock if r['operation']==name]
        axes[1].scatter([r['wall_time']-origin for r in rows],[r['hold_s'] for r in rows],s=3,label=name)
        axes[2].scatter([r['wall_time']-origin for r in rows],[r['wait_s'] for r in rows],s=3,label=name)
    axes[1].set_ylabel('地图锁持有 / s');axes[1].legend(ncol=5,fontsize=8)
    axes[2].set_ylabel('地图锁等待 / s')
    for i,name in enumerate(names):
        if i==4:continue
        axes[3].plot([r['time_s'] for r in runtime],[r['ms'][i]/1000 for r in runtime],label=name,lw=.7,alpha=.8)
    axes[3].set_ylabel('规划分项 / s');axes[3].set_xlabel('测量时间 / s');axes[3].legend(ncol=5)
    fig.suptitle('同一轮的HT年龄、CuPy地图锁与规划耗时；计时重合不能独立证明全部因果')
    fig.savefig(out/'latency.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(mapper_profiles=summary,ht_profiles=ht_stats,planner_breakdown_s=breakdown,stale_health_samples=result['stale_health_samples']),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
