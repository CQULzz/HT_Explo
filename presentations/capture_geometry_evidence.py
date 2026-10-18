#!/usr/bin/env python3
"""Read-only local collision/terrain/scan capture; coordinates remain in message frame."""
import argparse,json,time
from pathlib import Path
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,ReliabilityPolicy
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from sensor_msgs_py import point_cloud2
parser=argparse.ArgumentParser(description='Record local pointcloud evidence without changing navigation.');parser.add_argument('--output',type=Path,required=True);parser.add_argument('--duration',type=float,default=6);args=parser.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
rclpy.init();node=Node('readonly_geometry_capture');data={};meta={};pose=[None]
def odom(msg):
 p=msg.pose.pose.position;q=msg.pose.pose.orientation;pose[0]=[p.x,p.y,p.z,float(np.arctan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))];data['robot']=np.array(pose[0])
node.create_subscription(Odometry,'/state_estimation',odom,QoSProfile(depth=1,reliability=ReliabilityPolicy.BEST_EFFORT))
def callback(topic,msg):
 if pose[0] is None:return
 names=[f.name for f in msg.fields if f.name in ('x','y','z','intensity')]
 raw=point_cloud2.read_points(msg,field_names=names,skip_nans=True)
 a=np.column_stack([raw[n] for n in names]).astype(np.float32)
 keep=np.hypot(a[:,0]-pose[0][0],a[:,1]-pose[0][1])<5
 key=topic.strip('/');data[key]=a[keep];meta[key]=dict(stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9,frame=msg.header.frame_id,fields=names,total=len(a),local=int(keep.sum()),received=time.time())
topics=['/collision_cloud','/terrain_map','/terrain_map_ext','/viewpoint_in_collision_cloud_','/viewpoint_vis_cloud','/registered_scan']
for topic in topics:node.create_subscription(PointCloud2,topic,lambda msg,t=topic:callback(t,msg),QoSProfile(depth=2,reliability=ReliabilityPolicy.RELIABLE))
end=time.monotonic()+args.duration
while time.monotonic()<end:rclpy.spin_once(node,timeout_sec=.2)
np.savez_compressed(out/'clouds.npz',**data);(out/'metadata.json').write_text(json.dumps(meta,indent=2)+'\n');print(json.dumps(meta,indent=2));node.destroy_node();rclpy.shutdown()
