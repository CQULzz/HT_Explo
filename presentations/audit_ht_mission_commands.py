#!/usr/bin/env python3
"""Separate commanded pauses during a mission from deliberate completed parking."""
import argparse
import csv
import json
from pathlib import Path

import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String


def pause_metrics(commands,start,end):
    rows=[r for r in commands if start<=r[0]<end]
    longest=0.;begin=None;last=None;zero_count=0
    for t,v,w in rows:
        zero=abs(v)<.01 and abs(w)<.05
        if last is not None and t-last>.2:
            if begin is not None:longest=max(longest,last-begin+.05)
            begin=None
        if zero:
            zero_count+=1
            if begin is None:begin=t
        elif begin is not None:
            longest=max(longest,t-begin);begin=None
        last=t
    if begin is not None:longest=max(longest,min(end,last+.05)-begin)
    return dict(duration_s=end-start,command_samples=len(rows),longest_zero_command_s=longest,
        fully_stopped_sample_fraction=zero_count/max(1,len(rows)),
        max_abs_v=max((abs(r[1]) for r in rows),default=None),
        max_abs_w=max((abs(r[2]) for r in rows),default=None),
        max_command_gap_s=max((b[0]-a[0] for a,b in zip(rows,rows[1:])),default=None))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trial',type=Path,help='Raw trial folder containing evidence_bag and current/')
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--comparison-end',type=float,help='Also audit an equal-duration prefix shared by two trials')
    args=ap.parse_args();p=args.trial
    origin=json.loads((p/'current/measurement_started.json').read_text())['wall_time']
    duration=json.loads((p/'summary.json').read_text())['duration_s']
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(p/'evidence_bag'),storage_id='mcap'),
                rosbag2_py.ConverterOptions('',''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/cmd_vel','/mission_state']))
    commands=[];transitions=[]
    while reader.has_next():
        topic,data,ns=reader.read_next();t=ns/1e9-origin
        if not 0<=t<duration:continue
        if topic=='/cmd_vel':
            m=deserialize_message(data,TwistStamped);commands.append((t,m.twist.linear.x,m.twist.angular.z))
        else:
            state=deserialize_message(data,String).data
            if not transitions or transitions[-1]['state']!=state:
                transitions.append(dict(time_s=t,state=state))
    completed=next((r['time_s'] for r in transitions if r['state']=='COMPLETED'),None)
    cutoff=duration if completed is None else completed
    result=dict(source=str(p.resolve()),measurement_origin=origin,first_completed_message_s=completed,
        active_mission=pause_metrics(commands,0,cutoff),transitions=transitions,
        threshold='|v|<0.01m/s and |w|<0.05rad/s; split intervals if command gap exceeds 0.2s',
        meaning='Mission COMPLETED confirms home settling, not ground-truth complete coverage')
    if args.comparison_end is not None:
        if not 0<args.comparison_end<=duration:raise ValueError('comparison-end outside measured window')
        result['matched_window']=pause_metrics(commands,0,args.comparison_end)
    if completed is not None:
        result['completed_parking']=pause_metrics(commands,completed,duration)
        with (p/'current/timeseries.csv').open() as f:rows=list(csv.DictReader(f))
        xy=np.asarray([[float(r['x_m']),float(r['y_m'])] for r in rows if float(r['t_s'])>=completed])
        result['completed_parking']['max_sampled_xy_displacement_from_first_parked_pose_m']=float(
            np.linalg.norm(xy-xy[0],axis=1).max()) if len(xy) else None
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='transitions'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
