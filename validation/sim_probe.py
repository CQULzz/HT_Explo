#!/usr/bin/env python3
"""Publish explicitly synthetic HT data and record a running CMU simulation.

This is an interface/fault-injection fixture, not an HT inference model.
All times in the output are wall seconds; ROS messages use the node's clock.
"""
import argparse
import json
import math
import time
from pathlib import Path

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from geometry_msgs.msg import PointStamped, TwistStamped
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry, Path as RosPath
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Bool, Float32, Float32MultiArray, MultiArrayDimension


class Probe(Node):
    def __init__(self, args):
        super().__init__('ht_simulation_probe')
        self.args = args
        self.start = time.monotonic()
        self.position = self.waypoint = None
        self.allowed = None
        self.speed = 0.0
        self.scan_count = self.waypoint_count = self.allow_count = 0
        self.path_nodes = 0
        self.runtime = None
        self.distance = 0.0
        self.rows = []
        self.pub = self.create_publisher(GridMap, '/ht_traversability/global_local', 1)
        self.create_subscription(Odometry, '/state_estimation', self.odom, qos_profile_sensor_data)
        self.create_subscription(PointStamped, '/way_point', self.goal, 10)
        self.create_subscription(Bool, '/ht_navigation_allowed', self.permission, 10)
        self.create_subscription(TwistStamped, '/cmd_vel', self.velocity, qos_profile_sensor_data)
        self.create_subscription(PointCloud2, '/registered_scan', self.scan, qos_profile_sensor_data)
        self.create_subscription(Float32, '/runtime', self.timing, 10)
        self.create_subscription(RosPath, '/local_path', self.path, 10)
        self.create_timer(1.0/getattr(args, 'map_rate', 10.0), self.publish_map)
        self.create_timer(0.2, self.record)

    def odom(self, msg):
        p = msg.pose.pose.position
        new = [p.x, p.y, p.z]
        if self.position is not None:
            self.distance += math.dist(new, self.position)
        self.position = new

    def goal(self, msg):
        self.waypoint = [msg.point.x, msg.point.y, msg.point.z]
        self.waypoint_count += 1

    def permission(self, msg):
        self.allowed = msg.data
        self.allow_count += int(msg.data)

    def velocity(self, msg):
        self.speed = msg.twist.linear.x

    def scan(self, msg):
        self.scan_count += int(msg.width * msg.height > 0)

    def timing(self, msg):
        self.runtime = msg.data

    def path(self, msg):
        self.path_nodes = len(msg.poses)

    def phase(self):
        elapsed = time.monotonic() - self.start
        total = 0
        for name, duration in self.args.phases:
            total += duration
            if elapsed < total:
                return name
        return 'done'

    def publish_map(self):
        mode = self.phase()
        if mode in ('off', 'dropout', 'done') or self.position is None:
            return
        msg = GridMap()
        msg.header.frame_id = 'missing_ht_frame' if mode == 'missing_tf' else 'map'
        stamp = self.get_clock().now().nanoseconds
        if mode == 'stale':
            stamp -= 5_000_000_000
        msg.header.stamp.sec, msg.header.stamp.nanosec = divmod(stamp, 1_000_000_000)
        msg.info.resolution = 0.5
        msg.info.length_x = msg.info.length_y = getattr(self.args, 'map_length', 40.0)
        cells = round(msg.info.length_x / msg.info.resolution)
        msg.info.pose.position.x, msg.info.pose.position.y = self.position[:2]
        msg.info.pose.orientation.w = 1.0
        msg.layers = [f'ht_dir_{k}' for k in range(8)] + ['ht_valid']
        for k in range(9):
            data = Float32MultiArray()
            data.layout.dim = [
                MultiArrayDimension(label='column_index', size=cells, stride=cells*cells),
                MultiArrayDimension(label='row_index', size=cells, stride=cells)]
            probability = 1.0 if k == 8 else self.args.probabilities[k]
            if mode == 'nan' and k == 3:
                probability = float('nan')
            data.data = [probability] * (cells*cells)
            msg.data.append(data)
        if mode == 'missing_layer':
            msg.layers.pop(7)
            msg.data.pop(7)
        self.pub.publish(msg)

    def record(self):
        self.rows.append(dict(
            t=round(time.monotonic()-self.start, 3), phase=self.phase(),
            position=self.position, waypoint=self.waypoint, allowed=self.allowed,
            waypoint_distance=(math.dist(self.position, self.waypoint)
                               if self.position and self.waypoint else None),
            speed=self.speed, distance=self.distance, scans=self.scan_count,
            waypoints=self.waypoint_count, allowed_messages=self.allow_count,
            runtime=self.runtime, local_path_nodes=self.path_nodes))
        if len(self.rows) % 25 == 0:
            print(json.dumps(self.rows[-1]), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phases', default='valid:60')
    parser.add_argument('--probabilities', default='0.9,0.9,0.9,0.9,0.9,0.9,0.9,0.9')
    parser.add_argument('--output', required=True)
    args, ros_args = parser.parse_known_args()
    args.phases = [(name, float(duration)) for name, duration in
                   (phase.split(':') for phase in args.phases.split(','))]
    args.probabilities = [float(x) for x in args.probabilities.split(',')]
    assert len(args.probabilities) == 8
    assert all(0 <= p <= 1 for p in args.probabilities)
    rclpy.init(args=ros_args)
    node = Probe(args)
    try:
        while rclpy.ok() and node.phase() != 'done':
            rclpy.spin_once(node, timeout_sec=0.1)
    finally:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(dict(synthetic_ht=True, phases=args.phases,
                         probabilities=args.probabilities, samples=node.rows), indent=2))
        print(json.dumps(dict(output=str(out), samples=len(node.rows),
                              distance=node.distance, scans=node.scan_count,
                              waypoints=node.waypoint_count, allowed_messages=node.allow_count)))
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
