#!/usr/bin/env python3
"""Long-run ROS timing and motion probe for Campus HT exploration."""

import argparse
import csv
import json
import math
import statistics
import time
from collections import Counter
from pathlib import Path

import rclpy
from geometry_msgs.msg import PointStamped, TwistStamped
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry, Path as RosPath
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import Float32, String


class Probe(Node):
    def __init__(self):
        super().__init__("ht_long_run_probe")
        self.status = "WAITING"
        self.mission = "WAITING"
        self.robot_xy = None
        self.last_robot_xy = None
        self.distance = 0.0
        self.odom_speed = math.nan
        self.cmd_speed = math.nan
        self.cmd_yaw_rate = math.nan
        self.tare_speed = math.nan
        self.waypoint_distance = math.nan
        self.map_stamp = math.nan
        self.last_map_rx = None
        self.map_gaps = []
        self.map_count = 0
        self.path_count = 0
        self.last_path_rx = None
        self.last_cmd_rx = None
        self.last_odom_rx = None
        self.status_count = Counter()
        self.create_subscription(GridMap, "/ht_traversability/global_local", self.on_map,
                                 QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))
        self.create_subscription(Odometry, "/state_estimation", self.on_odom, 20)
        self.create_subscription(TwistStamped, "/cmd_vel", self.on_cmd, 20)
        self.create_subscription(Float32, "/speed", self.on_speed, 10)
        self.create_subscription(PointStamped, "/way_point", self.on_waypoint, 10)
        self.create_subscription(RosPath, "/local_path", self.on_path, 2)
        self.create_subscription(String, "/ht_execution_status", self.on_status, 10)
        self.create_subscription(String, "/mission_state", self.on_mission, 10)

    def on_map(self, msg):
        now = time.monotonic()
        if self.last_map_rx is not None:
            self.map_gaps.append(now - self.last_map_rx)
        self.last_map_rx = now
        self.map_stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        self.map_count += 1

    def on_odom(self, msg):
        self.last_odom_rx = time.monotonic()
        xy = (msg.pose.pose.position.x, msg.pose.pose.position.y)
        if self.last_robot_xy is not None:
            d = math.dist(xy, self.last_robot_xy)
            if d < 1.0:
                self.distance += d
        self.last_robot_xy = xy
        self.robot_xy = xy
        linear = msg.twist.twist.linear
        self.odom_speed = math.hypot(linear.x, linear.y)

    def on_cmd(self, msg):
        self.last_cmd_rx = time.monotonic()
        self.cmd_speed = msg.twist.linear.x
        self.cmd_yaw_rate = msg.twist.angular.z

    def on_speed(self, msg):
        self.tare_speed = msg.data

    def on_waypoint(self, msg):
        if self.robot_xy is not None:
            self.waypoint_distance = math.hypot(msg.point.x - self.robot_xy[0],
                                                msg.point.y - self.robot_xy[1])

    def on_path(self, _):
        self.path_count += 1
        self.last_path_rx = time.monotonic()

    def on_status(self, msg):
        self.status = msg.data
        self.status_count[msg.data] += 1

    def on_mission(self, msg):
        self.mission = msg.data

    def sample(self, t):
        now = time.monotonic()
        age = self.get_clock().now().nanoseconds * 1e-9 - self.map_stamp
        return [round(t, 3), self.mission, self.status,
                round(age, 3) if math.isfinite(age) else "",
                self.map_count, self.path_count, round(self.distance, 3),
                round(self.odom_speed, 3) if math.isfinite(self.odom_speed) else "",
                round(self.cmd_speed, 3) if math.isfinite(self.cmd_speed) else "",
                round(self.cmd_yaw_rate, 3) if math.isfinite(self.cmd_yaw_rate) else "",
                round(self.tare_speed, 3) if math.isfinite(self.tare_speed) else "",
                round(self.waypoint_distance, 3) if math.isfinite(self.waypoint_distance) else "",
                round(now - self.last_odom_rx, 3) if self.last_odom_rx else "",
                round(now - self.last_cmd_rx, 3) if self.last_cmd_rx else "",
                round(now - self.last_path_rx, 3) if self.last_path_rx else ""]


HEADER = ["t_s", "mission", "ht_status", "ht_map_age_s", "map_count", "path_count",
          "distance_m", "odom_speed_mps", "cmd_speed_mps", "cmd_yaw_rate_rps",
          "tare_speed_mps", "waypoint_distance_m", "odom_callback_age_s",
          "cmd_callback_age_s", "path_callback_age_s"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=900)
    parser.add_argument("--warmup", type=float, default=180)
    parser.add_argument("--sample-period", type=float, default=.5)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Probe()
    rows = []
    started = None
    try:
        warmup_end = time.monotonic() + args.warmup
        while time.monotonic() < warmup_end:
            rclpy.spin_once(node, timeout_sec=.1)
            if node.status == "HT_ASSISTED" and node.mission == "EXPLORING" and node.map_count > 0:
                started = time.monotonic()
                print("long-run clock started", flush=True)
                break
        if started is None:
            raise RuntimeError("No healthy HT exploration state before warmup timeout")
        path = args.output / "timing.csv"
        with path.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(HEADER)
            next_sample = started
            next_progress = 60
            while time.monotonic() - started < args.duration:
                rclpy.spin_once(node, timeout_sec=.05)
                now = time.monotonic()
                if now >= next_sample:
                    row = node.sample(now - started)
                    writer.writerow(row)
                    rows.append(row)
                    next_sample += args.sample_period
                elapsed = now - started
                if elapsed >= next_progress:
                    file.flush()
                    print(f"elapsed={elapsed:.0f}s maps={node.map_count} distance={node.distance:.1f}m status={node.status}", flush=True)
                    next_progress += 60
            file.flush()
        counts = Counter(row[2] for row in rows)
        ages = [float(row[3]) for row in rows if row[3] != ""]
        speed = [float(row[7]) for row in rows if row[7] != ""]
        cmd = [float(row[8]) for row in rows if row[8] != ""]
        summary = {
            "duration_s": round(time.monotonic() - started, 2),
            "sample_period_s": args.sample_period,
            "map_count_including_warmup": node.map_count,
            "map_gap_max_s": max(node.map_gaps, default=None),
            "map_gap_p95_s": float(__import__("numpy").percentile(node.map_gaps, 95)) if node.map_gaps else None,
            "map_age_max_s": max(ages, default=None),
            "sampled_status_counts": dict(counts),
            "status_callbacks_including_warmup": dict(node.status_count),
            "distance_m": round(node.distance, 2),
            "odom_speed_mean_mps": statistics.mean(speed) if speed else None,
            "cmd_speed_mean_mps": statistics.mean(cmd) if cmd else None,
            "moving_fraction": sum(v > .05 for v in speed) / len(speed) if speed else None,
            "zero_cmd_fraction": sum(abs(v) < .01 for v in cmd) / len(cmd) if cmd else None,
            "ending_mission": node.mission,
            "ending_status": node.status,
        }
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary), flush=True)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
