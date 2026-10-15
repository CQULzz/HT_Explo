#!/usr/bin/env python3
"""Record identical ROS metrics for original TARE and current XYtheta trials."""
import argparse
import csv
import json
import math
import sys
import time
from pathlib import Path

from benchmark_probe import HEADER, Probe, summarize  # noqa:E402
import rclpy  # noqa:E402
from nav_msgs.msg import Path as RosPath  # noqa:E402

class PairedProbe(Probe):
    def __init__(self):
        super().__init__()
        self.create_subscription(RosPath,'/ht_xytheta_path',self.on_path,10)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--duration',type=float,default=180)
    ap.add_argument('--warmup',type=float,default=100)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    rclpy.init();probe=PairedProbe();rows=[]
    try:
        waiting=time.monotonic()
        while time.monotonic()-waiting<args.warmup:
            rclpy.spin_once(probe,timeout_sec=.05)
            # The first TARE planning cycle is the common measurement origin.
            # A blocked XYtheta trial must still be recorded, not discarded for lack of motion.
            if probe.xy is not None and probe.scan_count>0 and probe.runtime_values:break
        else:raise RuntimeError('missing odometry, registered scan, or TARE runtime')
        started=time.monotonic();start_pose=(probe.xy[0],probe.xy[1],probe.yaw)
        (args.output/'measurement_started.json').write_text(json.dumps({
            'start_pose_xyyaw':start_pose,'wall_time':time.time()},indent=2)+'\n')
        probe.start_xy=probe.xy;probe.previous_xy=probe.xy;probe.distance=0
        probe.runtime_values.clear();probe.scan_count=probe.odom_count=probe.cmd_count=0
        probe.waypoint_count=probe.path_count=0;probe.scan_times.clear()
        probe.status_counts.clear();probe.ht_map_count=0;probe.ht_map_times.clear()
        probe.ht_map_ages.clear()
        with (args.output/'timeseries.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=HEADER,lineterminator='\n');writer.writeheader()
            tick=started
            while time.monotonic()-started<args.duration:
                rclpy.spin_once(probe,timeout_sec=.05)
                now=time.monotonic()
                if now>=tick:
                    row=dict(zip(HEADER,probe.sample(now-started)))
                    rows.append(row);writer.writerow(row);tick+=.5
                    if len(rows)%120==0:f.flush()
        result=summarize(rows,probe,args.duration,started-waiting)
        result['start_pose_xyyaw']=list(start_pose)
        result['measurement_origin']='first TARE /runtime after odometry and registered scan'
        result['registered_scans_total_in_window']=rows[-1]['scan_count'] if rows else 0
        (args.output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(result,ensure_ascii=False),flush=True)
    finally:
        probe.destroy_node();rclpy.try_shutdown()

if __name__=='__main__':main()
