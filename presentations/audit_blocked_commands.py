#!/usr/bin/env python3
"""Check the actual outgoing Twist at late HT command rejections in a bag."""
import argparse
from collections import Counter
import json
from pathlib import Path

import rosbag2_py
from rclpy.serialization import deserialize_message
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trial',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    origin=json.loads((args.trial/'current/measurement_started.json').read_text())['wall_time']
    duration=json.loads((args.trial/'summary.json').read_text())['duration_s']
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(args.trial/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/cmd_vel','/ht_follower_status']))
    last=None;bad=[];counts=Counter();paired=Counter()
    while reader.has_next():
        topic,data,ns=reader.read_next();t=ns/1e9-origin
        if not 0<=t<duration:continue
        if topic=='/cmd_vel':
            m=deserialize_message(data,TwistStamped);v,w=m.twist.linear,m.twist.angular
            last=dict(cmd_time_s=t,v=v.x,w=w.z,twist=[v.x,v.y,v.z,w.x,w.y,w.z])
        else:
            status=deserialize_message(data,String).data;counts[status]+=1
            if last is not None and 0<=t-last['cmd_time_s']<.02:
                paired[status]+=1
                if status=='HT_COMMAND_BLOCKED' and any(abs(v)>1e-9 for v in last['twist']):
                    bad.append(dict(last,status_time_s=t))
    result=dict(source=str(args.trial.resolve()),status_counts=dict(counts),paired_status_counts=dict(paired),
        unmatched_command_rejections=counts['HT_COMMAND_BLOCKED']-paired['HT_COMMAND_BLOCKED'],
        blocked_nonzero_count=len(bad),events=bad,
        caveat='Matches each late hold to its preceding command within20ms in publication order; reports unmatched events separately. Single-follower runs only. Does not infer internal map/odom callback ordering.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='events'},indent=2))


if __name__=='__main__':main()
