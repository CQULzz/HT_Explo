#!/usr/bin/env python3
"""Record a full TARE trial and plot observed free volume against time and travel.

Volume is the union of 0.5 m free voxels traversed by lidar rays, not the
volume enclosed by observed surfaces or the local elevation-map window.
"""

import argparse
import csv
import json
import math
import time
from pathlib import Path

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Bool, String


def pack_voxels(cells):
    # Signed 21-bit coordinates in each axis, enough for +/-524 km at 0.5 m.
    bias = 1 << 20
    if np.any(cells < -bias) or np.any(cells >= bias):
        raise ValueError("Observed voxel is outside supported coordinate range")
    shifted = cells.astype(np.int64) + bias
    return (shifted[:, 0] << 42) | (shifted[:, 1] << 21) | shifted[:, 2]


class Recorder(Node):
    def __init__(self, output, voxel_size, sample_period, max_seconds):
        super().__init__("tare_exploration_metrics")
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.voxel_size = voxel_size
        self.sample_period = sample_period
        self.max_seconds = max_seconds
        self.started = None
        self.previous_xy = None
        self.travel_m = 0.0
        self.free_voxels = set()
        self.last_cloud = -math.inf
        self.sensor_pose = None
        self.sensor_stamp = None
        self.mission_state = "WAIT_START"
        self.execution_status = ""
        self.completed = False
        self.terminal_reason = None
        self.scan_count = 0
        self.skipped_scans = 0
        self.csv_file = (self.output / "timeseries.csv").open("w", newline="")
        self.writer = csv.writer(self.csv_file)
        self.writer.writerow(["time_s", "observed_free_volume_m3", "distance_m", "free_voxels", "scans", "mission_state", "execution_status"])
        self.csv_file.flush()
        self.create_subscription(Odometry, "/state_estimation", self.on_odom, 20)
        self.create_subscription(Odometry, "/state_estimation_at_scan", self.on_sensor_pose, 10)
        self.create_subscription(PointCloud2, "/registered_scan", self.on_scan, 1)
        self.create_subscription(String, "/mission_state", self.on_mission, 10)
        self.create_subscription(String, "/ht_execution_status", self.on_status, 10)
        self.create_subscription(Bool, "/mission_completed", self.on_complete, 10)
        self.create_timer(sample_period, self.tick)

    def on_mission(self, message):
        self.mission_state = message.data
        if self.started is None and message.data in ("EXPLORING", "BLOCKED", "RETURNING_HOME", "COMPLETED"):
            self.started = time.monotonic()
            self.get_logger().info("Mission clock started")

    def on_status(self, message):
        self.execution_status = message.data

    def on_complete(self, message):
        if message.data:
            self.completed = True
            self.terminal_reason = "mission_completed"

    def on_odom(self, message):
        if self.started is None:
            return
        p = message.pose.pose.position
        xy = (p.x, p.y)
        if self.previous_xy is not None:
            step = math.dist(xy, self.previous_xy)
            if step <= 1.0:  # Reject simulator pose resets, not ordinary driving.
                self.travel_m += step
        self.previous_xy = xy

    def on_sensor_pose(self, message):
        p = message.pose.pose.position
        self.sensor_pose = np.array([p.x, p.y, p.z], dtype=np.float32)
        s = message.header.stamp
        self.sensor_stamp = s.sec + s.nanosec * 1e-9

    def on_scan(self, message):
        now = time.monotonic()
        if self.started is None or now - self.last_cloud < 1.0:
            return
        self.last_cloud = now
        if self.sensor_pose is None:
            self.skipped_scans += 1
            return
        s = message.header.stamp
        cloud_stamp = s.sec + s.nanosec * 1e-9
        if self.sensor_stamp is None or abs(cloud_stamp - self.sensor_stamp) > 0.5:
            self.skipped_scans += 1
            return
        xyz = point_cloud2.read_points_numpy(message, field_names=("x", "y", "z"), skip_nans=True)
        xyz = np.asarray(xyz, dtype=np.float32)
        if not len(xyz):
            self.skipped_scans += 1
            return
        rays = xyz - self.sensor_pose
        lengths = np.linalg.norm(rays, axis=1)
        usable = np.isfinite(lengths) & (lengths >= self.voxel_size) & (lengths <= 15.0)
        rays, lengths, xyz = rays[usable], lengths[usable], xyz[usable]
        if not len(rays):
            self.skipped_scans += 1
            return
        # One ray per endpoint voxel avoids repeated work on dense returns.
        _, unique = np.unique(pack_voxels(np.floor(xyz / self.voxel_size).astype(np.int64)), return_index=True)
        directions = rays[unique] / lengths[unique, None]
        lengths = lengths[unique]
        steps = np.arange(0.0, 15.0, self.voxel_size, dtype=np.float32)
        within = steps[None, :] < (lengths[:, None] - self.voxel_size * 0.5)
        samples = self.sensor_pose + directions[:, None, :] * steps[None, :, None]
        cells = np.floor(samples[within] / self.voxel_size).astype(np.int64)
        self.free_voxels.update(np.unique(pack_voxels(cells)).tolist())
        self.scan_count += 1

    def tick(self):
        if self.started is None or self.terminal_reason:
            return
        elapsed = time.monotonic() - self.started
        self.writer.writerow([
            round(elapsed, 3), round(len(self.free_voxels) * self.voxel_size ** 3, 3),
            round(self.travel_m, 3), len(self.free_voxels), self.scan_count,
            self.mission_state, self.execution_status,
        ])
        self.csv_file.flush()
        if int(elapsed) % 30 == 0:
            self.get_logger().info(f"t={elapsed:.0f}s volume={len(self.free_voxels) * self.voxel_size ** 3:.1f}m3 distance={self.travel_m:.1f}m state={self.mission_state} status={self.execution_status}")
        if elapsed >= self.max_seconds:
            self.terminal_reason = "max_duration_reached"

    def close(self):
        if self.started is not None:
            self.tick()
        self.csv_file.close()
        metadata = {
            "terminal_reason": self.terminal_reason or "interrupted",
            "mission_completed": self.completed,
            "mission_state": self.mission_state,
            "execution_status": self.execution_status,
            "voxel_size_m": self.voxel_size,
            "volume_definition": "cumulative unique free voxels traversed by valid registered lidar rays; endpoint voxels excluded; maximum ray length 15 m",
            "time_definition": "wall-clock elapsed since first active TARE mission state",
            "distance_definition": "cumulative 2D path length from /state_estimation, with >1 m pose jumps excluded",
            "scans_processed": self.scan_count,
            "scans_skipped": self.skipped_scans,
        }
        (self.output / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
        return metadata


def make_plot(output):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    data = np.genfromtxt(output / "timeseries.csv", delimiter=",", names=True, dtype=None, encoding="utf-8")
    if data.size < 2:
        return
    t = np.atleast_1d(data["time_s"]) / 60.0
    v = np.atleast_1d(data["observed_free_volume_m3"])
    d = np.atleast_1d(data["distance_m"])
    metadata_path = output / "metadata.json"
    metadata = json.loads(metadata_path.read_text()) if metadata_path.exists() else {}
    complete = metadata.get("mission_completed", False)
    subtitle = "Mission completed" if complete else "Mission stopped before completion"
    fig, axes = plt.subplots(1, 3, figsize=(14, 4.7), constrained_layout=True)
    fig.suptitle(subtitle, fontsize=12, weight="bold")
    axes[0].plot(t, v, color="#187bcd")
    axes[0].set(xlabel="Time (min)", ylabel="Observed free volume (m³)", title="Exploration volume over time")
    axes[1].plot(t, d, color="#d97706")
    axes[1].set(xlabel="Time (min)", ylabel="Travel distance (m)", title="Distance over time")
    axes[2].plot(d, v, color="#14976b")
    axes[2].set(xlabel="Travel distance (m)", ylabel="Observed free volume (m³)", title="Volume versus distance")
    for axis in axes:
        axis.grid(alpha=0.25)
    fig.savefig(output / "exploration_progress.png", dpi=180)
    fig.savefig(output / "exploration_progress.svg")
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--voxel-size", type=float, default=0.5)
    parser.add_argument("--sample-period", type=float, default=1.0)
    parser.add_argument("--max-seconds", type=float, default=1800.0)
    args = parser.parse_args()
    if args.voxel_size <= 0 or args.sample_period <= 0 or args.max_seconds <= 0:
        parser.error("sizes, periods and duration must be positive")
    rclpy.init()
    node = Recorder(args.output, args.voxel_size, args.sample_period, args.max_seconds)
    try:
        while rclpy.ok() and not node.terminal_reason:
            rclpy.spin_once(node, timeout_sec=0.2)
    except KeyboardInterrupt:
        pass
    finally:
        result = node.close()
        print(json.dumps(result, ensure_ascii=False), flush=True)
        node.destroy_node()
        rclpy.try_shutdown()
        make_plot(Path(args.output))


if __name__ == "__main__":
    main()
