#!/usr/bin/env python3
"""Record current HT execution beside its directional field and a shadow XYθ plan.

The shadow planner subscribes to TARE's goal but never controls the vehicle.
"""

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
from geometry_msgs.msg import PointStamped, TwistStamped
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry, Path as RosPath
from rclpy.node import Node
from sensor_msgs.msg import Image, PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import Float32, String

from xytheta_grid_planner import grid_from_arrays


W, H = 1600, 900
FONT = cv2.FONT_HERSHEY_SIMPLEX
BG = (24, 28, 33)
WHITE = (235, 239, 243)
CYAN = (235, 190, 55)
PURPLE = (210, 90, 210)
GREEN = (90, 225, 120)
ORANGE = (55, 170, 245)


def label(img, value, x, y, scale=.55, color=WHITE, thick=1):
    cv2.putText(img, str(value), (int(x), int(y)), FONT, scale, color, thick, cv2.LINE_AA)


def box(img, x0, y0, x1, y1, title):
    cv2.rectangle(img, (x0, y0), (x1 - 1, y1 - 1), (63, 70, 78), 1)
    cv2.rectangle(img, (x0 + 1, y0 + 1), (x1 - 2, y0 + 33), (35, 41, 48), -1)
    label(img, title, x0 + 12, y0 + 23, .52)


def heat_colors(prob):
    """Low probability red, middle yellow, high green; BGR pixels."""
    q = np.clip(np.nan_to_num(prob, nan=0), 0, 1)
    red = np.where(q < .5, 220, 220 * (1 - (q - .5) * 2))
    green = np.where(q < .5, 220 * q * 2, 220)
    blue = np.full_like(q, 48)
    return np.stack((blue, green, red), axis=-1).astype(np.uint8)


def clipped_polyline(img, points, color, width, rect):
    for a, b in zip(points[:-1], points[1:]):
        visible, aa, bb = cv2.clipLine(rect, a, b)
        if visible:
            cv2.line(img, aa, bb, color, width, cv2.LINE_AA)


class Recorder(Node):
    def __init__(self):
        super().__init__("ht_exploration_detailed_recorder")
        self.cvbridge = CvBridge()
        self.camera = None
        self.robot = None
        self.trace = deque(maxlen=6000)
        self.tare_path = []
        self.shadow_path = []
        self.shadow_status = "WAIT_INPUT"
        self.shadow_details = {}
        self.goal = None
        self.scan = np.empty((0, 2), np.float32)
        self.field = None
        self.map_stamp = None
        self.status = "WAITING"
        self.mission = "WAIT_START"
        self.cmd_speed = 0.0
        self.odom_speed = 0.0
        self.runtime_ms = math.nan
        self.distance = 0.0
        self.last_xy = None
        self.last_scan = 0.0
        self.status_counts = Counter()
        self.shadow_counts = Counter()
        self.map_count = 0
        self.path_count = 0
        self.shadow_plans = 0
        self.create_subscription(Image, "/camera/image_raw", self.on_camera, 2)
        self.create_subscription(Odometry, "/state_estimation", self.on_odom, 20)
        self.create_subscription(PointCloud2, "/registered_scan", self.on_scan, 1)
        self.create_subscription(RosPath, "/local_path", self.on_path, 3)
        self.create_subscription(RosPath, "/xytheta_grid_path", self.on_shadow_path, 3)
        self.create_subscription(PointStamped, "/way_point", self.on_goal, 5)
        self.create_subscription(GridMap, "/ht_traversability/global_local", self.on_map, 1)
        self.create_subscription(String, "/ht_execution_status", self.on_status, 10)
        self.create_subscription(String, "/mission_state", self.on_mission, 5)
        self.create_subscription(String, "/xytheta_grid_status", self.on_shadow_status, 5)
        self.create_subscription(TwistStamped, "/cmd_vel", self.on_cmd, 10)
        self.create_subscription(Float32, "/runtime", self.on_runtime, 5)

    def on_camera(self, msg):
        self.camera = self.cvbridge.imgmsg_to_cv2(msg, desired_encoding="bgr8")

    def on_odom(self, msg):
        p = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                         1 - 2 * (q.y * q.y + q.z * q.z))
        xy = (p.x, p.y)
        if self.last_xy is not None:
            step = math.dist(xy, self.last_xy)
            if step < 1:
                self.distance += step
        self.last_xy = xy
        self.robot = (p.x, p.y, yaw)
        if not self.trace or math.dist(xy, self.trace[-1]) > .05:
            self.trace.append(xy)
        v = msg.twist.twist.linear
        self.odom_speed = math.hypot(v.x, v.y)

    def on_scan(self, msg):
        if time.monotonic() - self.last_scan < .6:
            return
        self.last_scan = time.monotonic()
        try:
            xyz = point_cloud2.read_points_numpy(msg, field_names=("x", "y", "z"), skip_nans=True)
            self.scan = np.asarray(xyz[::12, :2], dtype=np.float32)
        except Exception as exc:
            self.get_logger().warn(f"Scan decode: {exc}")

    def on_path(self, msg):
        self.tare_path = [(p.pose.position.x, p.pose.position.y) for p in msg.poses]
        self.path_count += 1

    def on_shadow_path(self, msg):
        path = []
        for pose in msg.poses:
            q = pose.pose.orientation
            yaw = math.atan2(2 * q.w * q.z, 1 - 2 * q.z * q.z)
            path.append((pose.pose.position.x, pose.pose.position.y, yaw))
        self.shadow_path = path

    def on_goal(self, msg):
        self.goal = (msg.point.x, msg.point.y)

    def on_map(self, msg):
        try:
            n = round(msg.info.length_x / msg.info.resolution)
            if n != round(msg.info.length_y / msg.info.resolution):
                return
            def layer(name):
                return np.asarray(msg.data[msg.layers.index(name)].data,
                                  dtype=np.float32).reshape((n, n), order="F")
            probs = np.stack([layer(f"ht_dir_{k}") for k in range(8)])
            valid = layer("ht_valid") >= .5
            self.field = grid_from_arrays(
                probs, valid, (msg.info.pose.position.x, msg.info.pose.position.y),
                float(msg.info.resolution), 8)
            self.map_stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            self.map_count += 1
        except (IndexError, KeyError, ValueError) as exc:
            self.get_logger().warn(f"HT grid: {exc}")

    def on_status(self, msg):
        self.status = msg.data
        self.status_counts[msg.data] += 1

    def on_mission(self, msg):
        self.mission = msg.data

    def on_shadow_status(self, msg):
        try:
            data = json.loads(msg.data)
            self.shadow_status = data.get("status", "UNKNOWN")
            self.shadow_details = data
            self.shadow_counts[self.shadow_status] += 1
            if self.shadow_status == "PLANNED":
                self.shadow_plans += 1
        except json.JSONDecodeError:
            self.shadow_status = msg.data

    def on_cmd(self, msg):
        self.cmd_speed = msg.twist.linear.x

    def on_runtime(self, msg):
        self.runtime_ms = msg.data * 1000

    def draw_camera(self, frame):
        box(frame, 0, 70, 800, 450, "01  GAZEBO CAMERA  |  LIVE VEHICLE VIEW")
        if self.camera is not None:
            frame[105:448, 2:798] = cv2.resize(self.camera, (796, 343))
        else:
            label(frame, "Waiting for camera", 280, 280, .8)

    def draw_xy(self, frame):
        box(frame, 800, 70, 1600, 450, "02  EXECUTED XY  |  HT MAP, TARE ROUTE, GOAL")
        if self.robot is None:
            return
        rx, ry, yaw = self.robot
        x0, y0, scale = 1200, 278, 18
        def pix(x, y):
            return (int(x0 + (x - rx) * scale), int(y0 - (y - ry) * scale))
        if self.field is not None:
            xs, ys, probs, safe, res = self.field
            peak = np.max(probs, axis=0)
            for i, x in enumerate(xs):
                for j, y in enumerate(ys):
                    u, v = pix(x, y)
                    if 804 <= u < 1598 and 106 <= v < 448:
                        color = tuple(int(z) for z in heat_colors(np.array(peak[i, j]))) if safe[i, j] else (55, 57, 61)
                        d = max(2, int(scale * res / 2))
                        cv2.rectangle(frame, (u - d, v - d), (u + d, v + d), color, -1)
        if len(self.scan):
            uv = np.c_[x0 + (self.scan[:, 0] - rx) * scale,
                       y0 - (self.scan[:, 1] - ry) * scale].astype(int)
            mask = (uv[:, 0] > 802) & (uv[:, 0] < 1598) & (uv[:, 1] > 106) & (uv[:, 1] < 448)
            frame[uv[mask, 1], uv[mask, 0]] = (165, 170, 174)
        for points, color, width in ((list(self.trace), CYAN, 2), (self.tare_path, ORANGE, 3)):
            if len(points) > 1:
                clipped_polyline(frame, [pix(x, y) for x, y in points], color, width,
                                 (803, 106, 795, 299))
        if self.goal:
            u, v = pix(*self.goal)
            if 813 <= u < 1588 and 116 <= v < 395:
                cv2.drawMarker(frame, (u, v), PURPLE, cv2.MARKER_TILTED_CROSS, 18, 3)
        cv2.circle(frame, (x0, y0), 8, GREEN, -1)
        cv2.arrowedLine(frame, (x0, y0),
                        (int(x0 + 28 * math.cos(yaw)), int(y0 - 28 * math.sin(yaw))),
                        GREEN, 3, tipLength=.3)
        cv2.rectangle(frame, (807, 407), (1592, 446), BG, -1)
        label(frame, "cyan driven | orange TARE XY path | magenta waypoint | green robot", 815, 432, .47)

    def draw_layers(self, frame):
        box(frame, 0, 450, 800, 830, "03  SAME XY GRID AT 8 TRAVEL HEADINGS  |  HT P(x,y,theta)")
        if self.field is None:
            label(frame, "Waiting for 8-direction HT field", 210, 635, .65)
            return
        xs, ys, probs, safe, _ = self.field
        for k in range(8):
            col, row = k % 4, k // 4
            left, top = col * 200 + 3, 485 + row * 168
            tile = np.ascontiguousarray(probs[k].T[::-1, :])
            valid = np.ascontiguousarray(safe.T[::-1, :])
            colored = heat_colors(tile)
            colored[~valid] = (49, 54, 60)
            patch = cv2.resize(colored, (190, 136), interpolation=cv2.INTER_NEAREST)
            frame[top + 19:top + 155, left:left + 190] = patch
            for x in range(left, left + 190, 19):
                cv2.line(frame, (x, top + 19), (x, top + 155), (18, 22, 25), 1)
            for y in range(top + 19, top + 155, 17):
                cv2.line(frame, (left, y), (left + 190, y), (18, 22, 25), 1)
            label(frame, f"theta={k * 45:3d} deg", left + 5, top + 15, .43)
            if self.robot:
                i = int(np.argmin(np.abs(xs - self.robot[0])))
                j = int(np.argmin(np.abs(ys - self.robot[1])))
                u = left + int((i + .5) * 190 / len(xs))
                v = top + 19 + int((len(ys) - j - .5) * 136 / len(ys))
                cv2.circle(frame, (u, v), 4, (255, 255, 255), 1)
        label(frame, "red low  /  yellow medium  /  green high  /  gray unsupported", 10, 822, .43)

    def draw_shadow(self, frame):
        box(frame, 800, 450, 1600, 830,
            "04  8-LAYER HT FIELD + SHADOW XY-theta A*  |  DOES NOT DRIVE")
        if self.robot is None:
            return
        rx, ry, yaw = self.robot
        def project(x, y, k):
            return (int(1200 + (x - rx) * 27 + (y - ry) * 13),
                    int(735 - (y - ry) * 14 - k * 24))
        # Draw the actual eight probability layers in the same XY coordinates.
        # Thin sampled tiles and alpha blending keep all stacked layers visible.
        if self.field is not None:
            xs, ys, probs, safe, res = self.field
            for k in range(8):
                sheet = frame.copy()
                for i in range(0, len(xs), 2):
                    x = float(xs[i])
                    if abs(x - rx) > 5:
                        continue
                    for j in range(0, len(ys), 2):
                        y = float(ys[j])
                        if abs(y - ry) > 5 or not safe[i, j]:
                            continue
                        value = float(probs[k, i, j])
                        if not math.isfinite(value):
                            continue
                        d = res
                        quad = np.asarray([project(x - d, y - d, k),
                                           project(x + d, y - d, k),
                                           project(x + d, y + d, k),
                                           project(x - d, y + d, k)], np.int32)
                        color = tuple(int(z) for z in heat_colors(np.array(value)))
                        cv2.fillConvexPoly(sheet, quad, color)
                frame[486:795, 803:1598] = cv2.addWeighted(
                    sheet[486:795, 803:1598], .42,
                    frame[486:795, 803:1598], .58, 0)
        for k in range(8):
            corners = [project(rx + a, ry + b, k) for a, b in
                       ((-5, -5), (5, -5), (5, 5), (-5, 5))]
            cv2.polylines(frame, [np.asarray(corners, np.int32)], True, (96, 106, 115), 1)
            for a in (-2.5, 0, 2.5):
                cv2.line(frame, project(rx + a, ry - 5, k), project(rx + a, ry + 5, k), (70, 78, 86), 1)
                cv2.line(frame, project(rx - 5, ry + a, k), project(rx + 5, ry + a, k), (70, 78, 86), 1)
            label(frame, f"{k * 45:3d}", 1520, 733 - k * 24, .38, (160, 174, 190))
        if len(self.shadow_path) > 1:
            states = [(x, y, round((a % (2 * math.pi)) / (math.pi / 4)) % 8)
                      for x, y, a in self.shadow_path]
            uv = [project(*s) for s in states]
            clipped_polyline(frame, uv, (220, 230, 70), 3, (803, 485, 795, 310))
            for a, b in zip(uv[:-1], uv[1:]):
                if a[0] == b[0] and abs(a[1] - b[1]) >= 20:
                    cv2.circle(frame, b, 4, PURPLE, -1)
            cv2.circle(frame, uv[-1], 6, (235, 235, 245), 2)
        here = project(rx, ry, round((yaw % (2 * math.pi)) / (math.pi / 4)) % 8)
        cv2.circle(frame, here, 7, GREEN, -1)
        details = self.shadow_details
        label(frame, f"shadow: {self.shadow_status}", 816, 806, .55,
              GREEN if self.shadow_status == "PLANNED" else ORANGE)
        if self.shadow_status == "PLANNED":
            label(frame, f"states {details.get('states')} | expand {details.get('expanded')} | "
                         f"{details.get('planning_ms')} ms | turns {details.get('rotations')} | "
                         f"reverse {details.get('reverse')}", 1030, 806, .42)

    def render(self, elapsed):
        frame = np.full((H, W, 3), BG, np.uint8)
        label(frame, "HT EXPLORATION  /  CAMPUS SIMULATION", 18, 42, .95, WHITE, 2)
        label(frame, f"t={elapsed:5.1f}s   distance={self.distance:5.1f}m", 1075, 42, .72, CYAN, 2)
        self.draw_camera(frame)
        self.draw_xy(frame)
        self.draw_layers(frame)
        self.draw_shadow(frame)
        age = time.time() - self.map_stamp if self.map_stamp else math.nan
        runtime = f"{self.runtime_ms:.0f}ms" if math.isfinite(self.runtime_ms) else "--"
        age_text = f"{age:.2f}s" if math.isfinite(age) else "--"
        label(frame, f"TARE: {self.mission} / {self.status}   plan {runtime}   "
                     f"map age {age_text}", 15, 858, .55, WHITE)
        label(frame, f"cmd {self.cmd_speed:+.2f}m/s   odom {self.odom_speed:.2f}m/s   "
                     f"HT maps {self.map_count}   XYtheta shadow plans {self.shadow_plans}",
              15, 886, .52, WHITE)
        return frame


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=float, default=150)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--warmup", type=float, default=180)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    rclpy.init()
    node = Recorder()
    try:
        wait_started = time.monotonic()
        while time.monotonic() - wait_started < args.warmup:
            rclpy.spin_once(node, timeout_sec=.05)
            if (node.camera is not None and node.robot is not None and node.field is not None
                    and node.path_count > 0 and node.status == "HT_ASSISTED"
                    and node.odom_speed > .05):
                break
        else:
            raise RuntimeError(f"No moving HT-assisted simulation after {args.warmup}s: "
                               f"camera={node.camera is not None} map={node.field is not None} "
                               f"path={node.path_count} status={node.status}")
        node.distance = 0
        node.status_counts.clear()
        node.shadow_counts.clear()
        node.map_count = node.path_count = node.shadow_plans = 0
        writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"),
                                 args.fps, (W, H))
        if not writer.isOpened():
            raise RuntimeError("MP4 writer failed")
        start = time.monotonic()
        try:
            for i in range(math.ceil(args.duration * args.fps)):
                deadline = start + i / args.fps
                while time.monotonic() < deadline:
                    rclpy.spin_once(node, timeout_sec=min(.025, deadline - time.monotonic()))
                frame = node.render(time.monotonic() - start)
                writer.write(frame)
                if i == args.fps * 5:
                    cv2.imwrite(str(output.with_suffix(".preview.png")), frame)
                if i and i % (args.fps * 15) == 0:
                    print(f"recorded {i / args.fps:.0f}s distance={node.distance:.1f}m "
                          f"shadow={node.shadow_status}", flush=True)
        finally:
            writer.release()
        report = {
            "source": "Current HT_Explo-fixposition TARE + CMU Campus + independent CuPy map",
            "duration_s": args.duration, "fps": args.fps, "frames": math.ceil(args.duration * args.fps),
            "distance_m": round(node.distance, 2), "ht_maps": node.map_count,
            "tare_paths": node.path_count, "ht_status_callbacks": dict(node.status_counts),
            "shadow_xytheta_plans": node.shadow_plans,
            "shadow_status_callbacks": dict(node.shadow_counts),
            "interpretation": "TARE controls in XY using directional HT edge costs; XYtheta A* is a read-only shadow prototype"
        }
        output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report), flush=True)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
