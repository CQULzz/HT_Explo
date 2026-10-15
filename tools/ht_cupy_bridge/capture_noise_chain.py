#!/usr/bin/env python3
"""Capture synchronized latest inputs for elevation-noise diagnosis."""
import argparse,time,json
from pathlib import Path
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points_numpy
from nav_msgs.msg import Odometry
from grid_map_msgs.msg import GridMap

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=True);rclpy.init();node=Node('noise_chain_capture');latest={};index=[]
    def cloud(m):
        xyz=read_points_numpy(m,field_names=('x','y','z'),skip_nans=True)
        # Fixed planar ground ROI from the previous stop, plus surrounding area.
        keep=(xyz[:,0]>-2)&(xyz[:,0]<3)&(xyz[:,1]>7)&(xyz[:,1]<15)&(xyz[:,2]>-.5)&(xyz[:,2]<.5)
        latest['points']=np.asarray(xyz[keep],np.float32);latest['cloud_stamp']=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
    def grid(m,name):
        nx=round(m.info.length_x/m.info.resolution);ny=round(m.info.length_y/m.info.resolution)
        latest[name]=np.roll(np.asarray(m.data[m.layers.index('elevation')].data,np.float32).reshape((nx,ny),order='F'),(-m.outer_start_index,-m.inner_start_index),(0,1))
        latest[name+'_geometry']=np.array([m.info.pose.position.x,m.info.pose.position.y,m.info.resolution])
        latest[name+'_stamp']=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
    def odom(m):
        p=m.pose.pose.position;q=m.pose.pose.orientation
        latest['odom']=np.array([p.x,p.y,p.z,q.x,q.y,q.z,q.w])
    node.create_subscription(PointCloud2,'/registered_scan',cloud,qos_profile_sensor_data)
    node.create_subscription(PointCloud2,'/velodyne_points',
        lambda m:latest.update(raw_points=np.asarray(read_points_numpy(m,field_names=('x','y','z'),skip_nans=True),np.float32)),qos_profile_sensor_data)
    node.create_subscription(GridMap,'/elevation_mapping/elevation_map_raw',lambda m:grid(m,'cupy'),10)
    node.create_subscription(GridMap,'/elevation_mapping/historical_local',lambda m:grid(m,'history'),10)
    node.create_subscription(Odometry,'/state_estimation',odom,10)
    def save():
        if not all(k in latest for k in ['points','cupy','history','odom']):return
        name=f'noise_{len(index):03d}.npz';np.savez_compressed(args.output/name,**latest)
        index.append({'file':name,'wall':time.time()})
    node.create_timer(2.,save)
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        save();(args.output/'index.json').write_text(json.dumps(index,indent=2)+'\n');node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
