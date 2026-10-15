#!/usr/bin/env python3
"""Record common ROS 2 outputs for an upstream-vs-HT Campus comparison."""

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
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Bool, Float32, String


HEADER = ["t_s", "x_m", "y_m", "yaw_rad", "distance_m", "odom_speed_mps",
          "cmd_speed_mps", "cmd_yaw_rate_rps", "waypoint_distance_m",
          "path_length", "planner_runtime_s", "scan_count", "finished", "ht_status",
          "ht_map_age_s"]


class Probe(Node):
    def __init__(self):
        super().__init__("tare_comparison_probe")
        self.xy = None
        self.start_xy = None
        self.previous_xy = None
        self.yaw = math.nan
        self.distance = 0.0
        self.odom_speed = math.nan
        self.cmd_speed = math.nan
        self.cmd_yaw = math.nan
        self.waypoint_distance = math.nan
        self.path_length = None
        self.runtime = math.nan
        self.runtime_values = []
        self.scan_count = 0
        self.scan_times = []
        self.finished = False
        self.ht_status = ""
        self.status_counts = Counter()
        self.ht_map_count = 0
        self.ht_map_times = []
        self.ht_map_ages = []
        self.ht_map_age = math.nan
        self.odom_count = 0
        self.cmd_count = 0
        self.waypoint_count = 0
        self.path_count = 0
        self.create_subscription(Odometry, "/state_estimation", self.on_odom, 20)
        self.create_subscription(TwistStamped, "/cmd_vel", self.on_cmd, 20)
        self.create_subscription(PointStamped, "/way_point", self.on_waypoint, 10)
        self.create_subscription(RosPath, "/path", self.on_path, 10)
        self.create_subscription(Float32, "/runtime", self.on_runtime, 10)
        self.create_subscription(PointCloud2, "/registered_scan", self.on_scan, 10)
        self.create_subscription(Bool, "/exploration_finish", self.on_finish, 10)
        self.create_subscription(String, "/ht_execution_status", self.on_status, 10)
        self.create_subscription(GridMap, "/ht_traversability/global_local", self.on_ht_map, 1)

    def on_odom(self, message):
        p = message.pose.pose.position
        q = message.pose.pose.orientation
        xy = (p.x, p.y)
        if self.start_xy is None:
            self.start_xy = xy
        if self.previous_xy is not None:
            step = math.dist(xy, self.previous_xy)
            if step < 1.0:
                self.distance += step
        self.previous_xy = xy
        self.xy = xy
        self.yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                              1 - 2 * (q.y * q.y + q.z * q.z))
        v = message.twist.twist.linear
        self.odom_speed = math.hypot(v.x, v.y)
        self.odom_count += 1

    def on_cmd(self, message):
        self.cmd_speed = message.twist.linear.x
        self.cmd_yaw = message.twist.angular.z
        self.cmd_count += 1

    def on_waypoint(self, message):
        if self.xy is not None:
            self.waypoint_distance = math.dist(
                self.xy, (message.point.x, message.point.y))
        self.waypoint_count += 1

    def on_path(self, message):
        self.path_length = len(message.poses)
        self.path_count += 1

    def on_runtime(self, message):
        self.runtime = message.data
        if math.isfinite(self.runtime):
            self.runtime_values.append(self.runtime)

    def on_scan(self, _):
        self.scan_count += 1
        self.scan_times.append(time.monotonic())

    def on_finish(self, message):
        self.finished = message.data

    def on_status(self, message):
        self.ht_status = message.data
        self.status_counts[message.data] += 1

    def on_ht_map(self, message):
        self.ht_map_count += 1
        self.ht_map_times.append(time.monotonic())
        stamp = message.header.stamp
        age = time.time() - stamp.sec - stamp.nanosec * 1e-9
        if 0 <= age < 10000:
            self.ht_map_age = age
            self.ht_map_ages.append(age)

    def sample(self, t):
        return [round(t, 3),
                round(self.xy[0], 3) if self.xy else "",
                round(self.xy[1], 3) if self.xy else "",
                round(self.yaw, 3) if math.isfinite(self.yaw) else "",
                round(self.distance, 3),
                round(self.odom_speed, 3) if math.isfinite(self.odom_speed) else "",
                round(self.cmd_speed, 3) if math.isfinite(self.cmd_speed) else "",
                round(self.cmd_yaw, 3) if math.isfinite(self.cmd_yaw) else "",
                round(self.waypoint_distance, 3) if math.isfinite(self.waypoint_distance) else "",
                self.path_length if self.path_length is not None else "",
                round(self.runtime, 4) if math.isfinite(self.runtime) else "",
                self.scan_count, int(self.finished), self.ht_status,
                round(self.ht_map_age, 3) if math.isfinite(self.ht_map_age) else ""]


def summarize(rows, probe, duration, warmup_s):
    def values(key):
        return [float(row[key]) for row in rows if row[key] != ""]
    speed = values("odom_speed_mps")
    commands = values("cmd_speed_mps")
    waypoints = values("waypoint_distance_m")
    path_lengths = values("path_length")
    visited = {(math.floor(float(r["x_m"])), math.floor(float(r["y_m"])))
               for r in rows if r["x_m"] != "" and r["y_m"] != ""}
    endpoint = (float(rows[-1]["x_m"]), float(rows[-1]["y_m"])) if rows[-1]["x_m"] else None
    gaps = [b - a for a, b in zip(probe.scan_times, probe.scan_times[1:])]
    runtimes = sorted(probe.runtime_values)
    map_gaps = [b - a for a, b in zip(probe.ht_map_times, probe.ht_map_times[1:])]
    return {
        "duration_s": duration, "startup_wait_s": round(warmup_s, 2),
        "sample_count": len(rows), "odom_count": probe.odom_count,
        "cmd_count": probe.cmd_count, "waypoint_count": probe.waypoint_count,
        "path_count": probe.path_count, "registered_scans": probe.scan_count,
        "scan_gap_max_s": max(gaps, default=None),
        "distance_m": round(float(rows[-1]["distance_m"]) - float(rows[0]["distance_m"]), 2),
        "net_displacement_m": round(math.dist(probe.start_xy, endpoint), 2) if probe.start_xy and endpoint else None,
        "visited_1m_xy_cells": len(visited),
        "mean_odom_speed_mps": statistics.mean(speed) if speed else None,
        "moving_fraction": sum(v > .05 for v in speed) / len(speed) if speed else None,
        "zero_cmd_fraction": sum(abs(v) < .01 for v in commands) / len(commands) if commands else None,
        "forward_cmd_fraction": sum(v > .05 for v in commands) / len(commands) if commands else None,
        "reverse_cmd_fraction": sum(v < -.05 for v in commands) / len(commands) if commands else None,
        "median_waypoint_distance_m": statistics.median(waypoints) if waypoints else None,
        "short_path_fraction": sum(v <= 25 for v in path_lengths) / len(path_lengths) if path_lengths else None,
        "planner_runtime_median_s": statistics.median(runtimes) if runtimes else None,
        "planner_runtime_p95_s": runtimes[int(.95 * (len(runtimes) - 1))] if runtimes else None,
        "planner_runtime_max_s": max(runtimes, default=None),
        "planner_runtime_count": len(runtimes),
        "exploration_finished": probe.finished,
        "ht_status_callbacks": dict(probe.status_counts),
        "ht_map_count": probe.ht_map_count,
        "ht_map_gap_max_s": max(map_gaps, default=None),
        "ht_map_age_max_s": max(probe.ht_map_ages, default=None),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=300)
    parser.add_argument("--warmup", type=float, default=180)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    probe = Probe()
    try:
        waiting = time.monotonic()
        while time.monotonic() - waiting < args.warmup:
            rclpy.spin_once(probe, timeout_sec=.05)
            if (probe.xy is not None and probe.scan_count > 0 and probe.path_count > 0
                    and probe.runtime_values and math.isfinite(probe.cmd_speed)
                    and abs(probe.cmd_speed) > .05):
                break
        else:
            raise RuntimeError("No complete planning and motion chain during warmup")
        started = time.monotonic()
        probe.start_xy = probe.xy
        probe.runtime_values.clear()
        probe.scan_count = probe.odom_count = probe.cmd_count = 0
        probe.waypoint_count = probe.path_count = 0
        probe.scan_times.clear()
        probe.status_counts.clear()
        probe.ht_map_count = 0
        probe.ht_map_times.clear()
        probe.ht_map_ages.clear()
        rows = []
        with (args.output / "timeseries.csv").open("w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=HEADER, lineterminator="\n")
            writer.writeheader()
            next_tick = started
            while time.monotonic() - started < args.duration:
                rclpy.spin_once(probe, timeout_sec=.05)
                now = time.monotonic()
                if now >= next_tick:
                    row = dict(zip(HEADER, probe.sample(now - started)))
                    rows.append(row)
                    writer.writerow(row)
                    next_tick += .5
                    if len(rows) % 120 == 0:
                        file.flush()
            file.flush()
        summary = summarize(rows, probe, args.duration, started - waiting)
        (args.output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary), flush=True)
    finally:
        probe.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
