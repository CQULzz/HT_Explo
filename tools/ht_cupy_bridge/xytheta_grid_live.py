#!/usr/bin/env python3
"""Publish live XY-theta A* paths from HT, odometry, and TARE's XY waypoint.

Shadow mode only: this node never publishes /cmd_vel, /speed, or /way_point.
"""

import argparse
import json
import math
import time

import numpy as np
import rclpy
from geometry_msgs.msg import PointStamped, PoseStamped
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry, Path
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String

from xytheta_grid_planner import grid_from_arrays, nearest_index, plan


class LiveGridPlanner(Node):
    def __init__(self, stride, timeout, hz):
        super().__init__("xytheta_grid_live")
        self.stride = stride
        self.timeout = timeout
        self.latest = None
        self.robot = None
        self.target = None
        self.map_stamp = None
        self.count = 0
        self.path_pub = self.create_publisher(Path, "/xytheta_grid_path", 2)
        self.status_pub = self.create_publisher(String, "/xytheta_grid_status", 2)
        self.create_subscription(GridMap, "/ht_traversability/global_local", self.on_map,
                                 QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE))
        self.create_subscription(Odometry, "/state_estimation", self.on_odom, 10)
        self.create_subscription(PointStamped, "/way_point", self.on_goal, 10)
        self.create_timer(1 / hz, self.replan)

    def on_map(self, msg):
        try:
            n = round(msg.info.length_x / msg.info.resolution)
            if n < 1 or n != round(msg.info.length_y / msg.info.resolution):
                raise ValueError("not a square HT grid")
            def layer(name):
                return np.asarray(msg.data[msg.layers.index(name)].data,
                                  dtype=np.float32).reshape((n, n), order="F")
            p = np.stack([layer(f"ht_dir_{k}") for k in range(8)])
            valid = layer("ht_valid") >= .5
            if msg.header.frame_id != "map":
                raise ValueError("HT grid is not in map frame")
            self.latest = grid_from_arrays(
                p, valid, (msg.info.pose.position.x, msg.info.pose.position.y),
                float(msg.info.resolution), self.stride)
            self.map_stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
        except (ValueError, IndexError, KeyError) as exc:
            self.get_logger().warn(f"HT grid rejected: {exc}")
            self.latest = None

    def on_odom(self, msg):
        pos = msg.pose.pose.position
        q = msg.pose.pose.orientation
        yaw = math.atan2(2 * (q.w * q.z + q.x * q.y),
                         1 - 2 * (q.y * q.y + q.z * q.z))
        self.robot = (pos.x, pos.y, math.degrees(yaw))

    def on_goal(self, msg):
        self.target = (msg.point.x, msg.point.y)

    def publish_status(self, status, **details):
        if status != "PLANNED":
            empty = Path()
            empty.header.frame_id = "map"
            empty.header.stamp = self.get_clock().now().to_msg()
            self.path_pub.publish(empty)
        message = String()
        message.data = json.dumps({"status": status, **details})
        self.status_pub.publish(message)

    def replan(self):
        if self.latest is None or self.robot is None or self.target is None:
            self.publish_status("WAIT_INPUT")
            return
        age = self.get_clock().now().nanoseconds * 1e-9 - self.map_stamp
        if age < 0 or age > self.timeout:
            self.publish_status("HT_MAP_STALE", age_s=round(age, 3))
            return
        rx, ry, yaw = self.robot
        gx, gy = self.target
        if math.hypot(gx - rx, gy - ry) < .35:
            self.publish_status("TARGET_AT_ROBOT")
            return
        x, y, p, safe, _ = self.latest
        start = (nearest_index(x, rx), nearest_index(y, ry), round(yaw / 45) % 8)
        # TARE supplies an XY waypoint, so the goal yaw is deliberately free.
        goal = (nearest_index(x, gx), nearest_index(y, gy), None)
        if abs(x[goal[0]] - gx) > .25 or abs(y[goal[1]] - gy) > .25:
            self.publish_status("TARGET_OUTSIDE_HT_MAP")
            return
        started = time.perf_counter()
        try:
            states, actions, cost, expanded = plan(x, y, p, safe, start, goal,
                                                    .2, 1.0, .22, 1.2)
        except (ValueError, RuntimeError) as exc:
            self.publish_status("NO_XYTHETA_ROUTE", reason=str(exc))
            return
        message = Path()
        message.header.frame_id = "map"
        message.header.stamp = self.get_clock().now().to_msg()
        for i, j, k in states:
            pose = PoseStamped()
            pose.header = message.header
            pose.pose.position.x = float(x[i])
            pose.pose.position.y = float(y[j])
            angle = k * math.pi / 4
            pose.pose.orientation.z = math.sin(angle / 2)
            pose.pose.orientation.w = math.cos(angle / 2)
            message.poses.append(pose)
        self.path_pub.publish(message)
        self.count += 1
        self.publish_status("PLANNED", states=len(states), expanded=expanded,
                            cost=round(cost, 3), planning_ms=round((time.perf_counter() - started) * 1000, 2),
                            map_age_s=round(age, 3),
                            rotations=sum(a.startswith("rotate") for a in actions),
                            reverse=actions.count("reverse"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stride", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--hz", type=float, default=2.0)
    args = parser.parse_args()
    if args.stride < 1 or args.timeout <= 0 or args.hz <= 0:
        parser.error("stride, timeout, and hz must be positive")
    rclpy.init()
    node = LiveGridPlanner(args.stride, args.timeout, args.hz)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == "__main__":
    main()
