#!/usr/bin/env python3
"""Explicit simulation-only envelope for the native CMU follower comparison.

The original follower command is retained on /comparison/tare_raw_cmd_vel.
No exploration target, path or terrain decision is made here.
"""
import json
import math
import time
from pathlib import Path


def limited_step(previous, requested, dt, stale=False):
    if stale or not all(math.isfinite(x) for x in requested):
        return (0.0, 0.0), 'STALE_OR_INVALID_STOP'
    if requested == (0.0, 0.0):
        return (0.0, 0.0), 'EXPLICIT_ZERO_STOP'
    target = (max(-.25, min(.5, requested[0])), max(-.8, min(.8, requested[1])))
    dt = max(0., min(.1, dt))
    result = tuple(p + max(-rate*dt, min(rate*dt, target_i-p))
                   for p, target_i, rate in zip(previous, target, (.5, 1.2)))
    return result, 'LIMITED'


def main():
    import rclpy
    from rclpy.node import Node
    from geometry_msgs.msg import TwistStamped
    from std_msgs.msg import String

    class Limits(Node):
        def __init__(self):
            super().__init__('comparison_motion_limiter')
            self.declare_parameter('forward_cap', .5)
            self.declare_parameter('reverse_cap', .25)
            self.declare_parameter('yaw_cap', .8)
            self.declare_parameter('linear_accel', .5)
            self.declare_parameter('yaw_accel', 1.2)
            self.declare_parameter('input_timeout', .5)
            self.requested = (0., 0.)
            self.output = (0., 0.)
            self.received = None
            self.last = time.monotonic()
            self.pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)
            self.status = self.create_publisher(String, '/comparison/motion_limit_status', 10)
            self.create_subscription(TwistStamped, '/comparison/tare_raw_cmd_vel', self.receive, 20)
            self.create_timer(.05, self.tick)

        def receive(self, msg):
            self.received = time.monotonic()
            self.requested = (msg.twist.linear.x, msg.twist.angular.z)

        def tick(self):
            now = time.monotonic()
            self.output, state = limited_step(self.output, self.requested, now-self.last,
                                              self.received is None or now-self.received > .5)
            self.last = now
            msg = TwistStamped()
            msg.header.stamp = self.get_clock().now().to_msg()
            msg.header.frame_id = 'vehicle'
            msg.twist.linear.x, msg.twist.angular.z = self.output
            self.pub.publish(msg)
            self.status.publish(String(data=state))

    rclpy.init()
    node = Limits()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
