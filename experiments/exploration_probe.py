#!/usr/bin/env python3
"""Record exploration progress while publishing a controlled synthetic HT map."""
import argparse
import json
import math
from pathlib import Path
import sys
import time

import numpy as np
import rclpy
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Bool, Float32, Int32MultiArray
from rosgraph_msgs.msg import Clock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'validation'))
from sim_probe import Probe
from coverage_metrics import voxel_keys


class ExplorationProbe(Probe):
    def __init__(self, args):
        self.reference = set(np.load(args.reference)['keys'].tolist())
        self.observed = set()
        self.reference_hits = set()
        self.planar_distance = 0.0
        self.finished = False
        self.finish_time = None
        self.cycles = []
        self.official_volume = 0.0
        self.sim_clock = None
        self.measurement_started = False
        self.first_reference_hits = self.first_observed = 0
        self.baseline_distance = self.baseline_planar = 0.0
        self.scans_at_start = 0
        self.scan_times = []
        self.last_scan_stamp = None
        super().__init__(args)
        self.begin = self.start+args.warmup
        self.start_pub = self.create_publisher(Bool, '/start_exploration', 5)
        self.create_subscription(Int32MultiArray, '/runtime_breakdown', self.cycle, 10)
        self.create_subscription(Bool, '/exploration_finish', self.finish, 10)
        self.create_subscription(Float32, '/explored_volume', self.volume, 10)
        self.create_subscription(Clock, '/clock', self.clock, 10)
        self.create_timer(0.1, self.trigger)

    def elapsed(self):
        return time.monotonic()-self.begin

    def phase(self):
        return 'valid' if not hasattr(self, 'begin') or self.elapsed()<self.args.duration else 'done'

    def trigger(self):
        if 0 <= self.elapsed() < 2:
            self.start_pub.publish(Bool(data=True))

    def odom(self, msg):
        p=msg.pose.pose.position
        if self.position:
            self.planar_distance += math.hypot(p.x-self.position[0], p.y-self.position[1])
        super().odom(msg)

    def scan(self, msg):
        super().scan(msg)
        xyz = point_cloud2.read_points_numpy(msg, field_names=('x', 'y', 'z'), skip_nans=True)
        new = set(voxel_keys(xyz).tolist())-self.observed
        self.observed.update(new)
        self.reference_hits.update(new & self.reference)
        self.last_scan_stamp = msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        if hasattr(self, 'begin') and self.elapsed() >= 0:
            self.scan_times.append(self.elapsed())

    def cycle(self, msg):
        if self.elapsed() >= 0 and len(msg.data) == 6:
            self.cycles.append(dict(t=self.elapsed(), overall_ms=msg.data[-1], breakdown=list(msg.data)))

    def finish(self, msg):
        self.finished = msg.data
        if msg.data and self.finish_time is None and self.elapsed() >= 0:
            self.finish_time = self.elapsed()

    def volume(self, msg):
        self.official_volume = msg.data

    def clock(self, msg):
        self.sim_clock = msg.clock.sec+msg.clock.nanosec*1e-9

    def record(self):
        if not hasattr(self, 'begin') or self.elapsed() < 0:
            return
        if not self.measurement_started:
            if self.position is None or self.scan_count < 5:
                raise RuntimeError('Benchmark started without valid odometry/scans')
            self.first_reference_hits = len(self.reference_hits)
            self.first_observed = len(self.observed)
            self.baseline_distance = self.distance
            self.baseline_planar = self.planar_distance
            self.scans_at_start = self.scan_count
            self.measurement_started = True
        row=dict(t=round(self.elapsed(),3), position=self.position, waypoint=self.waypoint,
                 distance_m=self.distance-self.baseline_distance,
                 planar_distance_m=self.planar_distance-self.baseline_planar,
                 observed_voxels=len(self.observed),
                 new_observed_voxels=len(self.observed)-self.first_observed,
                 reference_hits=len(self.reference_hits),
                 new_reference_hits=len(self.reference_hits)-self.first_reference_hits,
                 reference_hit_pct=100*len(self.reference_hits)/len(self.reference),
                 cmu_hit_voxel_volume_m3=self.official_volume,
                 allowed=self.allowed, speed_command=self.speed,
                 scans=self.scan_count-self.scans_at_start,
                 sim_clock=self.sim_clock, finished=self.finished,
                 local_path_nodes=self.path_nodes,
                 scan_age_s=(self.get_clock().now().nanoseconds*1e-9-self.last_scan_stamp
                             if self.last_scan_stamp is not None else None))
        self.rows.append(row)
        if len(self.rows)%50 == 0:
            print(json.dumps(row), flush=True)
            self.save(final=False)

    def save(self, final):
        out = Path(self.args.output)
        out.mkdir(parents=True,exist_ok=True)
        data=dict(reference_voxels=len(self.reference), voxel_resolution_m=0.5,
                  synthetic_ht=True, ht_map_length_m=self.args.map_length,
                  ht_probability=0.9, ht_map_rate_hz=self.args.map_rate,
                  duration_requested_s=self.args.duration, finished=self.finished,
                  finish_time_s=self.finish_time, final=final,
                  samples=self.rows, planning_cycles=self.cycles, scan_times=self.scan_times)
        tmp=out/'metrics.tmp'
        tmp.write_text(json.dumps(data,indent=2))
        tmp.replace(out/'metrics.json')
        if final:
            np.savez_compressed(out/'observed_voxels.npz',
                                keys=np.fromiter(self.observed,dtype=np.int64))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--reference',required=True)
    parser.add_argument('--duration',type=float,default=300)
    parser.add_argument('--warmup',type=float,default=5)
    args=parser.parse_args()
    args.probabilities=[0.9]*8
    args.map_length=80.0  # Fully contains the 48 m square local planning horizon.
    args.map_rate=5.0
    rclpy.init()
    node=ExplorationProbe(args)
    success=False
    try:
        while rclpy.ok() and node.elapsed()<args.duration:
            rclpy.spin_once(node,timeout_sec=0.1)
        node.record()
        success=True
    finally:
        node.save(final=success)
        print(json.dumps(dict(final=success,last=node.rows[-1] if node.rows else None)),flush=True)
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__=='__main__':
    main()
