#!/usr/bin/env python3
"""Read-only health sampling and bounded evidence capture for an HT endurance run.

The only publications are sampled copies under /endurance, never vehicle commands.
Source stamps are retained. Callback age and source age are reported separately.
"""
import argparse
import collections
import csv
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Path as RosPath
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import String

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools/ht_cupy_bridge'))
from capture_replay_maps import Capture, stamp


class EnduranceProbe(Capture):
    def __init__(self, output):
        self.counts = collections.Counter()
        self.last_rx = {}
        self.last_stamp = {}
        self.last_relay = {}
        self.snapshot_after = -math.inf
        self.command = (math.nan, math.nan)
        self.status = {}
        self.output = output
        (output / 'snapshots').mkdir(parents=True, exist_ok=True)
        super().__init__(output / 'snapshots')
        self.publishers_by_name = {}
        self.scan_pub = self.create_publisher(PointCloud2, '/endurance/registered_scan', 2)
        self.create_subscription(PointCloud2, '/registered_scan', self.scan, 10)
        self.create_subscription(TwistStamped, '/cmd_vel', self.cmd, 40)
        self.create_subscription(RosPath, '/ht_xytheta_path', self.path, 10)
        for topic in ['ht_follower_status', 'ht_execution_status', 'mission_state']:
            self.create_subscription(String, '/' + topic,
                                     lambda msg, key=topic: self.status_update(key, msg), 20)
        self.created = time.monotonic()
        self.last_video = self.created
        self.writer = cv2.VideoWriter(str(output / 'camera_2fps.mp4'),
                                     cv2.VideoWriter_fourcc(*'mp4v'), 2, (960, 600))
        if not self.writer.isOpened():
            raise RuntimeError('Cannot open camera video writer')
        self.video_frames = 0
        self.csv_file = (output / 'health.csv').open('w', newline='')
        names = ['wall_time', 'probe_elapsed_s', 'scan_count', 'map_count',
                 'scan_source_age_s', 'map_source_age_s', 'map_callback_age_s',
                 'odom_callback_age_s', 'cmd_callback_age_s', 'path_callback_age_s',
                 'cmd_v', 'cmd_w', 'follower_status', 'execution_status', 'mission']
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=names, lineterminator='\n')
        self.csv_writer.writeheader()
        self.create_timer(1.0, self.sample)
        self.create_timer(.5, self.video)

    def seen(self, key, msg=None):
        self.counts[key] += 1
        self.last_rx[key] = time.monotonic()
        if msg is not None:
            self.last_stamp[key] = stamp(msg)

    def scan(self, msg):
        self.seen('scan', msg)
        # One original-stamped scan per source-second, not a generated cloud.
        bucket = math.floor(stamp(msg))
        if bucket != self.last_relay.get('scan'):
            self.scan_pub.publish(msg)
            self.last_relay['scan'] = bucket
            self.counts['recorded_scan'] += 1

    def grid(self, msg, kind):
        self.seen(kind, msg)
        # Exact-stamp triplets are saved every ten seconds. The base decoder
        # runs only during that capture window, reducing observer overhead.
        if stamp(msg) >= self.snapshot_after:
            super().grid(msg, kind)

    def try_save(self, key):
        previous = self.saved
        super().try_save(key)
        if self.saved != previous:
            self.snapshot_after = self.saved + 10.0

    def camera(self, msg):
        self.seen('camera')
        super().camera(msg)

    def odom(self, msg):
        self.seen('odom', msg)
        super().odom(msg)

    def cmd(self, msg):
        self.seen('cmd', msg)
        self.command = (msg.twist.linear.x, msg.twist.angular.z)

    def path(self, msg):
        self.seen('path', msg)

    def status_update(self, key, msg):
        self.status[key] = msg.data

    def sample(self):
        mono = time.monotonic()
        wall = time.time()
        age = lambda key: mono - self.last_rx[key] if key in self.last_rx else ''
        source_age = lambda key: wall - self.last_stamp[key] if key in self.last_stamp else ''
        row = dict(wall_time=wall, probe_elapsed_s=mono - self.created,
                   scan_count=self.counts['scan'], map_count=self.counts['ht'],
                   scan_source_age_s=source_age('scan'), map_source_age_s=source_age('ht'),
                   map_callback_age_s=age('ht'), odom_callback_age_s=age('odom'),
                   cmd_callback_age_s=age('cmd'), path_callback_age_s=age('path'),
                   cmd_v=self.command[0], cmd_w=self.command[1],
                   follower_status=self.status.get('ht_follower_status', ''),
                   execution_status=self.status.get('ht_execution_status', ''),
                   mission=self.status.get('mission_state', ''))
        self.csv_writer.writerow(row)
        self.csv_file.flush()
        self.last_health = row

    def video(self):
        now = time.monotonic()
        # Account for delayed callbacks with repeated frames, preserving a
        # wall-time timeline. Overlay includes age of the actual received image.
        while now - self.last_video >= .5:
            self.last_video += .5
            frame = np.zeros((600, 960, 3), np.uint8)
            if 'camera' in self.latest:
                frame[:540] = cv2.resize(self.latest['camera'], (960, 540))
            elapsed = self.last_video - self.created
            origin = self.output / 'current/measurement_started.json'
            if not hasattr(self, 'measurement_origin') and origin.exists():
                self.measurement_origin = json.loads(origin.read_text())['wall_time']
            label = ('trial t=%.1fs' % (time.time() - self.measurement_origin)
                     if hasattr(self, 'measurement_origin') else 'INITIALIZATION')
            image_age = now - self.last_rx.get('camera', now)
            cv2.putText(frame, f'HT endurance | {label} | camera age={image_age:.2f}s',
                        (12, 560), cv2.FONT_HERSHEY_SIMPLEX, .62, (230, 230, 230), 1)
            text = self.status.get('ht_follower_status', 'WAITING')
            cv2.putText(frame, text[:105], (12, 586), cv2.FONT_HERSHEY_SIMPLEX,
                        .55, (120, 230, 240), 1)
            self.writer.write(frame)
            self.video_frames += 1

    def close(self):
        self.writer.release()
        self.csv_file.close()
        (self.out / 'index.json').write_text(json.dumps({
            'frames': self.frames, 'ht_count': self.counts['ht'],
            'elevation_count': self.counts['cupy'],
            'sampling': 'exact-source-stamp map triplets, minimum ten seconds apart'}, indent=2))
        (self.output / 'probe_summary.json').write_text(json.dumps({
            'counts': dict(self.counts), 'duration_including_initialization_s': time.monotonic()-self.created,
            'video_frames': self.video_frames, 'video_fps': 2, 'snapshot_count': len(self.frames)}, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    rclpy.init()
    node = EnduranceProbe(args.output)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.close()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
