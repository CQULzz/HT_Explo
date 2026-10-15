#!/usr/bin/env python3
"""Capture the HT field and the *executed* XYtheta planner output in Garage."""
import argparse
import json
import math
import time
from pathlib import Path

import numpy as np
import rclpy
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry, Path as RosPath
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy
from std_msgs.msg import String


def yaw(q):
    return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))


class Capture(Node):
    def __init__(self, out, interval, max_frames):
        super().__init__('xytheta_planning_capture')
        self.out=out;self.interval=interval;self.max_frames=max_frames
        self.latest_map=None;self.odom=None;self.status='WAIT';self.mission='WAIT'
        self.first_path_at=None;self.last_saved=-1e9;self.frames=[]
        self.create_subscription(GridMap,'/ht_traversability/global_local',self.on_map,
            QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE))
        self.create_subscription(RosPath,'/ht_xytheta_path',self.on_path,10)
        self.create_subscription(Odometry,'/state_estimation',self.on_odom,10)
        self.create_subscription(String,'/ht_execution_status',lambda m:setattr(self,'status',m.data),10)
        self.create_subscription(String,'/mission_state',lambda m:setattr(self,'mission',m.data),10)

    def on_map(self,m):
        try:
            n=round(m.info.length_x/m.info.resolution)
            if n<1 or n!=round(m.info.length_y/m.info.resolution) or m.header.frame_id!='map':return
            layers={name:np.asarray(m.data[m.layers.index(name)].data,dtype=np.float32).reshape((n,n),order='F')
                    for name in [f'ht_dir_{k}' for k in range(8)]+['ht_valid']}
            self.latest_map=(np.stack([layers[f'ht_dir_{k}'] for k in range(8)]),
                             layers['ht_valid']>=.5,
                             np.array([m.info.pose.position.x,m.info.pose.position.y]),
                             float(m.info.resolution),
                             m.header.stamp.sec+m.header.stamp.nanosec*1e-9,
                             yaw(m.info.pose.orientation))
        except (IndexError,ValueError):pass

    def on_odom(self,m):
        p=m.pose.pose.position
        self.odom=np.array([p.x,p.y,yaw(m.pose.pose.orientation)],dtype=float)

    def on_path(self,m):
        if len(m.poses)<2 or self.latest_map is None or self.odom is None or m.header.frame_id!='map':return
        wall=time.monotonic()
        if self.first_path_at is None:self.first_path_at=wall
        if wall-self.last_saved<self.interval or len(self.frames)>=self.max_frames:return
        prob,valid,center,res,stamp,map_yaw=self.latest_map
        if abs(time.time()-stamp)>3.0:return
        route=np.array([[s.pose.position.x,s.pose.position.y,yaw(s.pose.orientation)] for s in m.poses])
        if not np.isfinite(route).all():return
        index=len(self.frames)
        filename=f'snapshot_{index:02d}.npz'
        np.savez_compressed(self.out/filename,probabilities=prob.astype(np.float16),
            valid=valid.astype(np.uint8),center=center,resolution=res,map_yaw=map_yaw,
            robot=self.odom,path=route.astype(np.float32),map_stamp=stamp)
        entry={'file':filename,'t_s':round(wall-self.first_path_at,2),'robot_xytheta':self.odom.tolist(),
               'path_poses':len(route),'goal_xy':route[-1,:2].tolist(),
               'path_length_m':round(float(np.linalg.norm(np.diff(route[:,:2],axis=0),axis=1).sum()),2),
               'status':self.status,'mission':self.mission,'map_age_s':round(time.time()-stamp,2)}
        self.frames.append(entry);self.last_saved=wall
        self.get_logger().info(f"captured {filename}: t={entry['t_s']}s robot={self.odom[:2]} path={len(route)}")


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=35)
    p.add_argument('--interval',type=float,default=3)
    p.add_argument('--max-frames',type=int,default=8)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
    rclpy.init();n=Capture(a.output,a.interval,a.max_frames)
    started=time.monotonic()
    try:
        while time.monotonic()-started<a.seconds and len(n.frames)<a.max_frames:
            rclpy.spin_once(n,timeout_sec=.1)
    finally:
        (a.output/'index.json').write_text(json.dumps({'frames':n.frames,'capture_wall_s':round(time.monotonic()-started,2)},
                                               ensure_ascii=False,indent=2)+'\n')
        n.destroy_node();rclpy.shutdown()
    print(json.dumps({'frames':len(n.frames),'output':str(a.output)},ensure_ascii=False))

if __name__=='__main__':main()
