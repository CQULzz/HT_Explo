#!/usr/bin/env python3
"""Move the simulation-only vehicle to the same Garage start pose before each trial."""
import json
import math
import time
import argparse

import rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from rclpy.node import Node

TARGET=(0.30,3.50,math.pi/2)

def wrap(a):
    return math.atan2(math.sin(a),math.cos(a))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--scenario',choices=['garage','campus','indoor','forest','tunnel'],default='garage')
    args=parser.parse_args()
    rclpy.init()
    node=Node('paired_trial_staging')
    pose=None
    def odom(msg):
        nonlocal pose
        p=msg.pose.pose.position;q=msg.pose.pose.orientation
        pose=(p.x,p.y,math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))
    node.create_subscription(Odometry,'/state_estimation',odom,10)
    pub=node.create_publisher(TwistStamped,'/cmd_vel',10)
    deadline=time.monotonic()+75
    settled=0
    target=TARGET if args.scenario=='garage' else None
    while time.monotonic()<deadline:
        rclpy.spin_once(node,timeout_sec=.025)
        if pose is None:continue
        # Preserve each world's native spawn; the Garage staging location is
        # a historical paired-test choice, not a safe universal destination.
        if target is None:target=pose
        dx=target[0]-pose[0];dy=target[1]-pose[1]
        distance=math.hypot(dx,dy)
        goal_yaw=target[2] if distance<.35 else math.atan2(dy,dx)
        err=wrap(goal_yaw-pose[2])
        cmd=TwistStamped();cmd.header.stamp=node.get_clock().now().to_msg()
        cmd.header.frame_id='vehicle'
        if distance<.35 and abs(err)<.10:
            settled+=1
            if settled>=8:break
        else:
            settled=0
            if abs(err)>.13:cmd.twist.angular.z=max(-.5,min(.5,1.5*err))
            else:cmd.twist.linear.x=min(.20,max(.05,.45*distance))
        pub.publish(cmd)
        time.sleep(.025)
    for _ in range(15):
        pub.publish(TwistStamped());time.sleep(.025)
    result={'pose':pose,'target':target,'scenario':args.scenario,
            'position_error_m':math.hypot(pose[0]-target[0],pose[1]-target[1]) if pose else None,
            'yaw_error_rad':abs(wrap(pose[2]-target[2])) if pose else None}
    print(json.dumps(result),flush=True)
    ok=pose is not None and result['position_error_m']<.40 and result['yaw_error_rad']<.15
    node.destroy_node();rclpy.shutdown()
    if not ok:raise SystemExit(2)

if __name__=='__main__':main()
