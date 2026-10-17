#!/usr/bin/env python3
"""Audit double sampling of source-second evidence in measurement-second bins."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path

import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trial',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--topic',default='/endurance/registered_scan')
    args=ap.parse_args()
    origin=json.loads((args.trial/'current/measurement_started.json').read_text())['wall_time']
    duration=json.loads((args.trial/'summary.json').read_text())['duration_s']
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(args.trial/'evidence_bag'),storage_id='mcap'),
                rosbag2_py.ConverterOptions('',''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=[args.topic]))
    timestamps=[]
    while reader.has_next():
        _,data,_=reader.read_next()
        m=deserialize_message(data,PointCloud2)
        stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
        if 0<=stamp-origin<duration:timestamps.append(stamp)
    if not timestamps:raise RuntimeError('No source-stamped scans in the measurement window')
    absolute=Counter(math.floor(t) for t in timestamps)
    relative=Counter(math.floor(t-origin) for t in timestamps)
    result=dict(source=str(args.trial.resolve()),origin=origin,duration_s=duration,
        recorded_scans=len(timestamps),absolute_source_second_bins=len(absolute),
        measurement_second_bins=len(relative),
        discarded_by_additional_measurement_binning=sum(n-1 for n in relative.values()),
        duplicated_measurement_bins={str(k):n for k,n in relative.items() if n>1},
        unrepresented_measurement_bins=[k for k in range(math.ceil(duration)) if k not in relative],
        source_stamps=timestamps,
        interpretation='If source-second bins are unique but measurement-second bins collide, the second binning discards already recorded scans. This is an evaluation-selection effect, not evidence of simulator or mapper packet loss.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_stamps','duplicated_measurement_bins','unrepresented_measurement_bins')},indent=2))


if __name__=='__main__':main()
