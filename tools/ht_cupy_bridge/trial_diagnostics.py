#!/usr/bin/env python3
"""Summarize one live Garage/Campus trial without changing the ROS graph."""

import argparse
import json
import math
import time

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import String
from grid_map_msgs.msg import GridMap


class Diagnostics(Node):
    def __init__(self):
        super().__init__("ht_trial_diagnostics")
        self.xy = []
        self.status = {}
        self.mission = {}
        self.scans = {}
        self.map_ages = []
        self.map_times = []
        self.center_valid = []
        self.create_subscription(PointCloud2, "/velodyne_points", lambda m: self.scan("raw", m), 10)
        self.create_subscription(PointCloud2, "/registered_scan", lambda m: self.scan("registered", m), 10)
        self.create_subscription(Odometry, "/state_estimation", self.odom, 10)
        self.create_subscription(String, "/ht_execution_status", lambda m: self.count(self.status, m.data), 10)
        self.create_subscription(String, "/mission_state", lambda m: self.count(self.mission, m.data), 10)
        self.create_subscription(GridMap, "/ht_traversability/global_local", self.ht_map, 1)

    @staticmethod
    def count(table, value):
        table[value] = table.get(value, 0) + 1

    def scan(self, name, message):
        if name in self.scans:
            return
        xyz = point_cloud2.read_points_numpy(message, field_names=("x", "y", "z"), skip_nans=True)
        radius = np.hypot(xyz[:, 0], xyz[:, 1])
        self.scans[name] = {
            "points": len(xyz),
            "min_xy_m": float(radius.min()) if len(radius) else None,
            "within_1m": int((radius < 1).sum()),
            "within_2m": int((radius < 2).sum()),
        }

    def odom(self, message):
        p = message.pose.pose.position
        self.xy.append((p.x, p.y))

    def ht_map(self, message):
        stamp = message.header.stamp.sec + message.header.stamp.nanosec * 1e-9
        self.map_ages.append(time.time() - stamp)
        self.map_times.append(time.time())
        if "ht_valid" in message.layers:
            data = message.data[message.layers.index("ht_valid")].data
            side = round(math.sqrt(len(data)))
            self.center_valid.append(bool(data[(side // 2) * (side + 1)] >= 0.5))

    def report(self):
        path = sum(math.dist(a, b) for a, b in zip(self.xy, self.xy[1:]))
        gap = max((b - a for a, b in zip(self.map_times, self.map_times[1:])), default=None)
        return {
            "raw": self.scans.get("raw"),
            "registered": self.scans.get("registered"),
            "odom_samples": len(self.xy),
            "path_m": round(path, 2),
            "net_m": round(math.dist(self.xy[0], self.xy[-1]), 2) if self.xy else None,
            "ht_maps": len(self.map_times),
            "ht_center_valid_fraction": round(sum(self.center_valid) / len(self.center_valid), 3) if self.center_valid else None,
            "ht_map_max_gap_s": round(gap, 3) if gap else None,
            "ht_map_max_age_s": round(max(self.map_ages), 3) if self.map_ages else None,
            "status": self.status,
            "mission": self.mission,
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=60)
    args = parser.parse_args()
    rclpy.init()
    node = Diagnostics()
    try:
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=0.2)
        print(json.dumps(node.report(), ensure_ascii=False))
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
