#!/usr/bin/env python3
"""Record a ROS-native simulation video without capturing the desktop."""

import argparse
import json
import math
import time
from collections import Counter, deque
from pathlib import Path

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node
from sensor_msgs.msg import Image, PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Float32, String


class VideoRecorder(Node):
    def __init__(self):
        super().__init__("ht_sim_video_recorder")
        self.bridge = CvBridge()
        self.camera = None
        self.pose = None
        self.waypoint = None
        self.trajectory = deque(maxlen=6000)
        self.scan_xy = np.empty((0, 2), np.float32)
        self.status = "WAITING"
        self.mission = "WAIT_START"
        self.command_speed = 0.0
        self.measured_speed = 0.0
        self.status_counts = Counter()
        self.distance = 0.0
        self.last_odom = None
        self.last_scan = 0.0
        self.create_subscription(Image, "/camera/image_raw", self.on_image, 2)
        self.create_subscription(Odometry, "/state_estimation", self.on_odom, 20)
        self.create_subscription(PointStamped, "/way_point", self.on_waypoint, 5)
        self.create_subscription(PointCloud2, "/registered_scan", self.on_scan, 1)
        self.create_subscription(String, "/ht_execution_status", self.on_status, 10)
        self.create_subscription(String, "/mission_state", lambda m: setattr(self, "mission", m.data), 10)
        self.create_subscription(Float32, "/speed", lambda m: setattr(self, "command_speed", m.data), 10)

    def on_image(self, msg):
        self.camera = self.bridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

    def on_odom(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
        xy = (p.x, p.y)
        if self.last_odom is not None:
            ds = math.dist(xy, self.last_odom)
            if ds < 1:
                self.distance += ds
        self.last_odom = xy
        if not self.trajectory or math.dist(xy, self.trajectory[-1]) > 0.03:
            self.trajectory.append(xy)
        self.pose = (p.x, p.y, yaw)
        v = msg.twist.twist.linear
        self.measured_speed = math.hypot(v.x, v.y)

    def on_waypoint(self, msg):
        self.waypoint = (msg.point.x, msg.point.y)

    def on_scan(self, msg):
        if time.monotonic() - self.last_scan < 0.5:
            return
        self.last_scan = time.monotonic()
        xyz = point_cloud2.read_points_numpy(msg, field_names=("x", "y", "z"), skip_nans=True)
        self.scan_xy = np.asarray(xyz[::10, :2], dtype=np.float32)

    def on_status(self, msg):
        self.status = msg.data
        self.status_counts[msg.data] += 1

    def render(self, elapsed):
        frame = np.full((720, 1280, 3), (22, 26, 31), np.uint8)
        if self.camera is not None:
            frame[:540, :960] = cv2.resize(self.camera, (960, 540), interpolation=cv2.INTER_LINEAR)
        else:
            cv2.putText(frame, "Waiting for Gazebo camera", (190, 260), cv2.FONT_HERSHEY_SIMPLEX, 1, (230, 230, 230), 2)
        cv2.putText(frame, "SIMULATED CAMERA", (18, 34), cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 255, 255), 2)
        top = frame[:540, 960:]
        top[:] = (28, 32, 38)
        cv2.putText(top, "LOCAL TOP VIEW", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, .55, (235, 235, 235), 1)
        if self.pose:
            x, y, yaw = self.pose
            scale = 10.0  # 320 px covers 32 m.
            def pixel(xy):
                return (int(160 + (xy[0] - x) * scale), int(270 - (xy[1] - y) * scale))
            if len(self.scan_xy):
                uv = np.c_[160 + (self.scan_xy[:, 0] - x) * scale, 270 - (self.scan_xy[:, 1] - y) * scale].astype(int)
                valid = (uv[:, 0] >= 0) & (uv[:, 0] < 320) & (uv[:, 1] >= 0) & (uv[:, 1] < 540)
                top[uv[valid, 1], uv[valid, 0]] = (85, 95, 100)
            trail = [pixel(p) for p in self.trajectory]
            if len(trail) > 1:
                cv2.polylines(top, [np.array(trail, np.int32)], False, (255, 200, 60), 2)
            if self.waypoint:
                wx, wy = pixel(self.waypoint)
                if 0 <= wx < 320 and 0 <= wy < 540:
                    cv2.circle(top, (wx, wy), 6, (210, 70, 220), -1)
            cv2.circle(top, (160, 270), 8, (70, 230, 100), -1)
            cv2.arrowedLine(top, (160, 270), (int(160 + 26 * math.cos(yaw)), int(270 - 26 * math.sin(yaw))), (70, 230, 100), 2)
        cv2.putText(top, "Cyan: path  Pink: target", (10, 518), cv2.FONT_HERSHEY_SIMPLEX, .42, (190, 210, 230), 1)
        cv2.line(frame, (0, 540), (1280, 540), (90, 100, 110), 1)
        cv2.putText(frame, f"TIME {elapsed:5.1f}s     DISTANCE {self.distance:6.1f}m", (24, 585), cv2.FONT_HERSHEY_SIMPLEX, .82, (245, 245, 245), 2)
        cv2.putText(frame, f"CMD {self.command_speed:.2f} m/s     ODOM {self.measured_speed:.2f} m/s", (24, 628), cv2.FONT_HERSHEY_SIMPLEX, .72, (220, 225, 230), 2)
        color = (80, 215, 100) if self.status == "HT_ASSISTED" else (70, 160, 245)
        cv2.putText(frame, f"{self.mission}  |  {self.status}", (24, 677), cv2.FONT_HERSHEY_SIMPLEX, .72, color, 2)
        return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=float, default=75)
    parser.add_argument("--fps", type=float, default=10)
    parser.add_argument("--warmup-timeout", type=float, default=120)
    args = parser.parse_args()
    if args.duration <= 0 or args.fps <= 0:
        parser.error("duration and fps must be positive")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = VideoRecorder()
    try:
        deadline = time.monotonic() + args.warmup_timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(node, timeout_sec=.1)
            if node.camera is not None and node.mission == "EXPLORING" and node.status == "HT_ASSISTED" and node.measured_speed > .08:
                break
        else:
            raise RuntimeError("Simulation did not provide moving camera/HT state before timeout")
        node.status_counts.clear()
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(str(output), fourcc, args.fps, (1280, 720))
        if not writer.isOpened():
            raise RuntimeError("OpenCV could not open MP4 writer")
        start = time.monotonic()
        try:
            frame_count = math.ceil(args.duration * args.fps)
            for i in range(frame_count):
                target = start + i / args.fps
                while time.monotonic() < target:
                    rclpy.spin_once(node, timeout_sec=min(.03, target - time.monotonic()))
                writer.write(node.render(time.monotonic() - start))
                if i and i % (10 * int(args.fps)) == 0:
                    print(f"recorded {i / args.fps:.0f}s", flush=True)
        finally:
            writer.release()
        metadata = {"duration_s": args.duration, "fps": args.fps, "frames": frame_count,
                    "distance_m": round(node.distance, 2), "last_status": node.status,
                    "status_callbacks": dict(node.status_counts), "source": "Gazebo /camera/image_raw plus ROS odometry, lidar and HT state"}
        output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps(metadata), flush=True)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
