"""Validate surface-reference odometry without inventing TF or resetting maps.

Out-of-order packets are ignored. A large pose discontinuity or ROS-clock
rollback latches a fault; restart the complete mapping/planning pipeline in a
consistent frame. Automatic history reset would leave upstream maps/graphs in
different epochs and is intentionally not attempted here.
"""
from collections import deque
import math


class InputOdometry:
    def __init__(self, child_frame=''):
        self.child_frame = child_frame
        self.samples = deque(maxlen=4000)
        self.last_pose = None
        self.last_clock = None
        self.fault = None

    def check_clock(self, now):
        if self.last_clock is not None and now < self.last_clock-1e-6:
            self.fault = 'CLOCK_RESET_RESTART_REQUIRED'
        self.last_clock = now
        return self.fault is None

    def add(self, msg, now):
        if not self.check_clock(now):
            return False
        stamp = msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        p, q = msg.pose.pose.position, msg.pose.pose.orientation
        xyz = (p.x, p.y, p.z)
        quat = (q.x, q.y, q.z, q.w)
        if (msg.header.frame_id not in ('map', '/map') or
                (self.child_frame and msg.child_frame_id != self.child_frame) or
                not all(math.isfinite(v) for v in (stamp, *xyz, *quat)) or
                abs(sum(v*v for v in quat)-1) > .01 or
                stamp <= 0 or stamp > now+.1 or now-stamp > .75):
            return False
        if self.last_pose is not None:
            old_stamp, old_xyz, old_quat = self.last_pose
            dt = stamp-old_stamp
            if dt <= 0:
                return False
            dot = sum(a*b for a, b in zip(quat, old_quat))
            norms = math.sqrt(sum(v*v for v in quat)*sum(v*v for v in old_quat))
            angle = 2*math.acos(min(1., abs(dot)/norms))
            if math.dist(xyz, old_xyz) > .75+3*dt or angle > .5+4*dt:
                self.fault = 'ODOM_JUMP_RESTART_REQUIRED'
                return False
        self.last_pose = (stamp, xyz, quat)
        self.samples.append((stamp, p.z))
        return True

    def height_at(self, stamp, max_skew=.05):
        if self.fault or not self.samples or not math.isfinite(stamp):
            return None
        # Bounded nearest height is sufficient for the surface-layer hint;
        # unlike planner scan poses it is not used to transform lidar points.
        nearest = min(self.samples, key=lambda p: abs(p[0]-stamp))
        return nearest[1] if abs(nearest[0]-stamp) <= max_skew else None
