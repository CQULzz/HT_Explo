#!/usr/bin/env python3
"""Live view of the current XY route lifted into XY-theta for inspection.

TARE plans viewpoint edges in XY. The orange theta values below are derived
from edge bearings; they are not states optimized by an XY-theta planner.
"""

import argparse
import json
import math
import time
from collections import deque
from pathlib import Path

import cv2
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import rclpy
from geometry_msgs.msg import PointStamped
from nav_msgs.msg import Odometry, Path as RosPath
from rclpy.node import Node
from std_msgs.msg import String


def yaw_deg(q):
    return math.degrees(math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z)))


def split_wrap(x, y, theta):
    output = []
    current = []
    for p in zip(x, y, theta):
        if current and abs(p[2] - current[-1][2]) > 180:
            output.append(np.asarray(current))
            current = []
        current.append(p)
    if current:
        output.append(np.asarray(current))
    return output


class XYThetaViewer(Node):
    def __init__(self):
        super().__init__("ht_xytheta_live_viewer")
        self.robot = None
        self.trace = deque(maxlen=4000)
        self.local_path = np.empty((0, 2))
        self.waypoint = None
        self.status = "WAITING"
        self.mission = "WAIT_START"
        self.measured_speed = 0.0
        self.path_updates = 0
        self.create_subscription(Odometry, "/state_estimation", self.on_odom, 20)
        self.create_subscription(RosPath, "/local_path", self.on_path, 2)
        self.create_subscription(PointStamped, "/way_point", self.on_waypoint, 5)
        self.create_subscription(String, "/ht_execution_status", lambda m: setattr(self, "status", m.data), 5)
        self.create_subscription(String, "/mission_state", lambda m: setattr(self, "mission", m.data), 5)

    def on_odom(self, msg):
        p = msg.pose.pose.position
        yaw = yaw_deg(msg.pose.pose.orientation)
        self.robot = (p.x, p.y, yaw)
        if not self.trace or math.hypot(p.x - self.trace[-1][0], p.y - self.trace[-1][1]) > .04 or abs(yaw - self.trace[-1][2]) > 4:
            self.trace.append((p.x, p.y, yaw))
        v = msg.twist.twist.linear
        self.measured_speed = math.hypot(v.x, v.y)

    def on_path(self, msg):
        self.local_path = np.asarray([(p.pose.position.x, p.pose.position.y) for p in msg.poses], dtype=float).reshape((-1, 2))
        self.path_updates += 1

    def on_waypoint(self, msg):
        self.waypoint = (msg.point.x, msg.point.y)


def draw(view, elapsed, fig, axes):
    ax3d, axxy, axth = axes
    for ax in axes:
        ax.clear()
    x, y, yaw = view.robot
    trail = np.asarray(view.trace, dtype=float).reshape((-1, 3))
    local = view.local_path
    if len(local) > 1:
        edge_lengths = np.linalg.norm(np.diff(local, axis=0), axis=1)
        cutoff = max(2, np.searchsorted(np.r_[0.0, np.cumsum(edge_lengths)], 20.0, side="right"))
        local = local[:cutoff]
    # Plot observed robot pose; split the +/-180 degree wrap for legibility.
    if len(trail) > 1:
        for part in split_wrap(trail[:, 0], trail[:, 1], trail[:, 2]):
            if len(part) > 1:
                ax3d.plot(part[:, 0], part[:, 1], part[:, 2], color="#087fbf", lw=2.2)
        axxy.plot(trail[:, 0], trail[:, 1], color="#087fbf", lw=2.0, label="actual XY trajectory")
    ax3d.scatter([x], [y], [yaw], color="#1baf55", s=70, depthshade=False)
    axxy.scatter([x], [y], color="#1baf55", s=70, zorder=5, label="robot now")
    axxy.arrow(x, y, math.cos(math.radians(yaw)) * 1.5, math.sin(math.radians(yaw)) * 1.5,
               color="#1baf55", width=.04, length_includes_head=True)

    edge_dist = []
    edge_theta = []
    if len(local) > 1:
        axxy.plot(local[:, 0], local[:, 1], "o-", color="#e88822", markersize=3, lw=2,
                  label="published local XY route")
        accumulated = 0.0
        for a, b in zip(local[:-1], local[1:]):
            delta = b - a
            length = np.linalg.norm(delta)
            if length < 1e-4:
                continue
            bearing = math.degrees(math.atan2(delta[1], delta[0]))
            ax3d.plot([a[0], b[0]], [a[1], b[1]], [bearing, bearing], color="#e88822", lw=2.5)
            edge_dist.extend([accumulated, accumulated + length, np.nan])
            edge_theta.extend([bearing, bearing, np.nan])
            accumulated += length
        if edge_dist:
            axth.plot(edge_dist, edge_theta, color="#e88822", lw=2.3, label="edge bearing used for HT lookup")
    if view.waypoint:
        wx, wy = view.waypoint
        axxy.scatter([wx], [wy], color="#b337bb", marker="x", s=100, linewidths=3, label="commanded waypoint")
        if math.hypot(wx - x, wy - y) > .05:
            command_bearing = math.degrees(math.atan2(wy - y, wx - x))
            axth.axhline(command_bearing, color="#b337bb", ls="--", lw=1.5, label="waypoint bearing")
    axth.axhline(yaw, color="#1baf55", ls=":", lw=1.7, label="actual robot yaw")
    for degree in range(-180, 181, 45):
        axth.axhline(degree, color="gray", lw=.5, alpha=.25)

    ax3d.set(xlabel="X (m)", ylabel="Y (m)", zlabel="theta (deg)", zlim=(-180, 180),
             xlim=(x - 10, x + 10), ylim=(y - 10, y + 10))
    ax3d.set_zticks(range(-180, 181, 45))
    ax3d.view_init(elev=22, azim=-58)
    ax3d.set_title("XY-theta embedding: actual pose and XY edge bearings", fontsize=10)
    axxy.set(xlabel="X (m)", ylabel="Y (m)", xlim=(x - 10, x + 10), ylim=(y - 10, y + 10))
    axxy.set_aspect("equal", adjustable="box")
    axxy.grid(alpha=.2)
    axxy.legend(loc="lower left", fontsize=7)
    axth.set(xlabel="Distance along published local path (m)", ylabel="theta (deg)", ylim=(-180, 180), xlim=(0, 20))
    axth.grid(alpha=.2)
    axth.legend(loc="lower left", fontsize=7)
    fig.suptitle(f"{elapsed:.1f}s   robot=({x:.1f}, {y:.1f}, {yaw:.0f}deg)   speed={view.measured_speed:.2f}m/s   {view.mission} / {view.status}", fontsize=12)
    fig.text(.5, .018, "Orange theta = edge atan2(dY,dX), then HT uses nearest 45-degree bin; current TARE does not search (x,y,theta) states.",
             ha="center", color="#9c3a20", fontsize=9)
    fig.canvas.draw()
    rgba = np.asarray(fig.canvas.buffer_rgba())
    return cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGR)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=float, default=75)
    parser.add_argument("--fps", type=float, default=2)
    parser.add_argument("--warmup-timeout", type=float, default=150)
    parser.add_argument("--show", action="store_true", help="also show the live view on the desktop")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    view = XYThetaViewer()
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100)
    ax3d = fig.add_subplot(121, projection="3d")
    axxy = fig.add_axes([.55, .52, .41, .37])
    axth = fig.add_axes([.60, .13, .35, .27])
    try:
        deadline = time.monotonic() + args.warmup_timeout
        while time.monotonic() < deadline:
            rclpy.spin_once(view, timeout_sec=.1)
            if view.robot and view.path_updates and view.mission == "EXPLORING":
                break
        else:
            raise RuntimeError("No live robot pose/local path before timeout")
        writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (1280, 720))
        if not writer.isOpened():
            raise RuntimeError("Cannot create MP4")
        start = time.monotonic()
        frames = math.ceil(args.duration * args.fps)
        try:
            for i in range(frames):
                target = start + i / args.fps
                while time.monotonic() < target:
                    rclpy.spin_once(view, timeout_sec=min(.05, target - time.monotonic()))
                frame = draw(view, time.monotonic() - start, fig, (ax3d, axxy, axth))
                writer.write(frame)
                if args.show:
                    cv2.imshow("TARE XY-theta live view", frame)
                    cv2.waitKey(1)
                if i and i % max(1, int(10 * args.fps)) == 0:
                    print(f"rendered {i / args.fps:.0f}s; path updates {view.path_updates}; status {view.status}", flush=True)
        finally:
            writer.release()
            if args.show:
                cv2.destroyAllWindows()
        metadata = {"duration_s": args.duration, "fps": args.fps, "frames": frames,
                    "path_updates": view.path_updates,
                    "semantics": "orange theta is derived from 2D edge bearing, blue theta is measured robot yaw; no XY-theta state-space search"}
        output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")
        print(json.dumps(metadata), flush=True)
    finally:
        plt.close(fig)
        view.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
