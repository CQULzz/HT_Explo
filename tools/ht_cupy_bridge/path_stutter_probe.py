#!/usr/bin/env python3
"""Measure whether CMU publishes one-pose stop paths while TARE wants motion."""

import argparse
import csv
import json
import time
from collections import Counter
from pathlib import Path

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Path as RosPath
from rclpy.node import Node
from std_msgs.msg import Float32, String


class Probe(Node):
    def __init__(self):
        super().__init__("cmu_path_stutter_probe")
        self.path_length = None
        self.cmd_speed = None
        self.tare_speed = None
        self.status = "WAITING"
        self.path_count = 0
        self.path_length_counts = Counter()
        self.create_subscription(RosPath, "/path", self.on_path, 10)
        self.create_subscription(TwistStamped, "/cmd_vel", self.on_cmd, 10)
        self.create_subscription(Float32, "/speed", self.on_speed, 10)
        self.create_subscription(String, "/ht_execution_status", self.on_status, 10)

    def on_path(self, msg):
        self.path_length = len(msg.poses)
        self.path_count += 1
        self.path_length_counts[self.path_length] += 1

    def on_cmd(self, msg):
        self.cmd_speed = msg.twist.linear.x

    def on_speed(self, msg):
        self.tare_speed = msg.data

    def on_status(self, msg):
        self.status = msg.data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--duration", type=float, default=300)
    parser.add_argument("--wait-healthy", action="store_true")
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Probe()
    rows = []
    if args.wait_healthy:
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
            if node.status == "HT_ASSISTED" and node.path_length is not None:
                break
        else:
            raise RuntimeError("No healthy HT/path state before timeout")
    start = time.monotonic()
    next_tick = start
    try:
        with args.output.open("w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["t_s", "path_length", "cmd_speed_mps", "tare_speed_mps", "ht_status"])
            while time.monotonic() - start < args.duration:
                rclpy.spin_once(node, timeout_sec=.05)
                now = time.monotonic()
                if now >= next_tick:
                    row = [round(now - start, 3), node.path_length, node.cmd_speed,
                           node.tare_speed, node.status]
                    writer.writerow(row)
                    rows.append(row)
                    next_tick += .5
            file.flush()
        assisted = [r for r in rows if r[4] == "HT_ASSISTED" and r[1] is not None]
        stalled = [r for r in assisted if r[1] <= 1]
        summary = {"duration_s": args.duration, "path_messages": node.path_count,
                   "path_length_message_counts": dict(node.path_length_counts),
                   "ht_assisted_samples": len(assisted),
                   "one_pose_fraction_while_assisted": len(stalled) / len(assisted) if assisted else None,
                   "zero_cmd_given_one_pose":
                       sum(r[2] is not None and abs(r[2]) < .01 for r in stalled) / len(stalled)
                       if stalled else None}
        args.output.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary), flush=True)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
