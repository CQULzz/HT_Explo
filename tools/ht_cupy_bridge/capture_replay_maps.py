#!/usr/bin/env python3
"""Capture time-stamped elevation/HT/camera snapshots during bag replay."""
import argparse,json
from collections import OrderedDict
from pathlib import Path
import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from nav_msgs.msg import Odometry
from grid_map_msgs.msg import GridMap
from cv_bridge import CvBridge

def stamp(m):return m.header.stamp.sec+m.header.stamp.nanosec*1e-9

class Capture(Node):
    def __init__(self,out):
        super().__init__('bag_map_capture');self.out=out;self.latest={};self.frames=[];self.origin=None;self.saved=-1e10;self.bridge=CvBridge();self.ht_count=0;self.elevation_count=0
        self.grids = {kind: OrderedDict() for kind in ['cupy', 'history', 'ht']}
        self.create_subscription(GridMap,'/elevation_mapping/elevation_map_raw',lambda m:self.grid(m,'cupy'),5)
        self.create_subscription(GridMap,'/elevation_mapping/historical_local',lambda m:self.grid(m,'history'),5)
        self.create_subscription(GridMap,'/ht_traversability/global_local',lambda m:self.grid(m,'ht'),5)
        self.create_subscription(Image,'/camera/image_raw',self.camera,qos_profile_sensor_data)
        self.create_subscription(Odometry,'/state_estimation',self.odom,qos_profile_sensor_data)
    def camera(self,m):
        self.latest['camera']=self.bridge.imgmsg_to_cv2(m,'bgr8')
        # Gazebo image headers use simulator-relative time while registered
        # scans use wall-clock stamps. Align images by replay receive time.
        self.latest['camera_source_stamp']=stamp(m)
        self.latest['camera_stamp']=self.get_clock().now().nanoseconds*1e-9
    def odom(self,m):
        p=m.pose.pose.position;q=m.pose.pose.orientation
        self.latest['robot']=np.array([p.x,p.y,np.arctan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))])
        self.latest['odom_stamp']=stamp(m)
    def grid(self,m,kind):
        n=round(m.info.length_x/m.info.resolution);k=round(m.info.length_y/m.info.resolution)
        names=[f'ht_dir_{i}' for i in range(8)]+['ht_valid'] if kind=='ht' else ['elevation','variance']
        if kind == 'cupy':
            names += [name for name in ['observation_age'] if name in m.layers]
        elif kind == 'history':
            names += [name for name in ['elevation_raw', 'input_valid', 'rejected'] if name in m.layers]
        decoded = {}
        for name in names:
            decoded[kind+'_'+name]=np.roll(np.asarray(m.data[m.layers.index(name)].data,np.float32).reshape((n,k),order='F'),(-m.outer_start_index,-m.inner_start_index),(0,1))
        decoded[kind+'_geometry']=np.array([m.info.pose.position.x,m.info.pose.position.y,m.info.resolution]);decoded[kind+'_stamp']=stamp(m)
        key = m.header.stamp.sec*1000000000 + m.header.stamp.nanosec
        buffer = self.grids[kind];buffer[key] = decoded
        while len(buffer)>16:buffer.popitem(last=False)
        if kind=='cupy':self.elevation_count+=1
        if kind=='ht':
            self.ht_count+=1
            if self.origin is None:self.origin=stamp(m)
        self.try_save(key)

    def try_save(self,key):
        if not all(key in self.grids[kind] for kind in self.grids):return
        t=self.grids['ht'][key]['ht_stamp']
        if t-self.saved<0.5 or not all(name in self.latest for name in ['camera','robot']):return
        # Match exact source stamps. Latest-arrival snapshots can otherwise
        # combine a new HT field with a different raw map or historical crop.
        data = dict(self.latest)
        for kind in self.grids:data.update(self.grids[kind][key])
        filename=f'frame_{len(self.frames):04d}.npz'
        np.savez_compressed(self.out/filename,**data)
        self.frames.append({'file':filename,'t_s':t-self.origin,'ht_stamp':t,
                            'camera_offset_s':float(data['camera_stamp']-t),
                            'elevation_offset_s':float(data['cupy_stamp']-t),
                            'history_offset_s':float(data['history_stamp']-t),
                            'robot':self.latest['robot'].tolist()});self.saved=t

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args,ros_args=ap.parse_known_args();args.output.mkdir(parents=True,exist_ok=True)
    rclpy.init(args=ros_args);node=Capture(args.output)
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        (args.output/'index.json').write_text(json.dumps({'frames':node.frames,'ht_count':node.ht_count,'elevation_count':node.elevation_count},indent=2)+'\n');node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
