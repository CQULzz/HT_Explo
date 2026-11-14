from pathlib import Path
import time,json,math,argparse
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,DurabilityPolicy
from visualization_msgs.msg import Marker,MarkerArray
from sensor_msgs.msg import PointCloud2,PointField
from geometry_msgs.msg import Point,TransformStamped
from tf2_ros import TransformBroadcaster
ROOT=Path('/mnt/d/HT-Execution-300s/rviz_video_20261114')
class Player(Node):
 def __init__(self):
  super().__init__('recorded_exploration_viewer');q=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL)
  self.pub=self.create_publisher(MarkerArray,'/visual/markers',q);self.cloud=self.create_publisher(PointCloud2,'/visual/surfaces',q);self.tf=TransformBroadcaster(self)
  self.traj=np.load(ROOT/'trajectory.npy');self.snap=json.loads((ROOT/'snapshots.json').read_text());self.times=np.array([v['elapsed_s'] for v in self.snap]);self.paths=json.loads((ROOT/'paths.json').read_text());self.path_times=np.array([v['elapsed_s'] for v in self.paths]);self.frame=-1;self.free_marker=None;self.control=None;self.base=0.;self.wall=time.monotonic();self.create_timer(.1,self.tick)
 def marker(self,idx,kind,color):
  m=Marker();m.header.frame_id='map';m.ns='recorded';m.id=idx;m.type=kind;m.action=Marker.ADD;m.pose.orientation.w=1.;m.color.r,m.color.g,m.color.b,m.color.a=color;return m
 def point(self,x,y,z):return Point(x=float(x),y=float(y),z=float(z))
 def tick(self):
  try:control=json.loads((ROOT/'control.json').read_text())
  except Exception:return
  if control!=self.control:self.control=control;self.base=float(control.get('time',0));self.wall=time.monotonic()
  rate=float(control.get('rate',4));elapsed=min(float(control.get('end_time',600)),max(0.,self.base+((time.monotonic()-self.wall)*rate if control.get('mode')=='play' else 0)))
  i=min(len(self.traj)-1,max(0,int(np.searchsorted(self.traj[:,0],elapsed))));row=self.traj[i];_,x,y,z,yaw,distance,volume=row
  tf=TransformStamped();tf.header.stamp=self.get_clock().now().to_msg();tf.header.frame_id='map';tf.child_frame_id='replay_camera';tf.transform.translation.x=float(x);tf.transform.translation.y=float(y);tf.transform.rotation.w=1.;self.tf.sendTransform(tf)
  idx=max(0,min(len(self.snap)-1,int(np.searchsorted(self.times,elapsed,side='right')-1)))
  markers=[]
  if idx!=self.frame:
   self.frame=idx;data=np.load(ROOT/self.snap[idx]['file']);pts=np.asarray(data['surface'],dtype=np.float32).reshape(-1,3)
   cloud=PointCloud2();cloud.header.frame_id='map';cloud.height=1;cloud.width=len(pts);cloud.fields=[PointField(name=n,offset=j*4,datatype=PointField.FLOAT32,count=1) for j,n in enumerate(['x','y','z'])];cloud.point_step=12;cloud.row_step=12*len(pts);cloud.is_dense=True;cloud.data=pts.tobytes();self.cloud.publish(cloud)
   m=self.marker(0,Marker.CUBE_LIST,(.12,.52,.32,.72));m.scale.x=.48;m.scale.y=.48;m.scale.z=.025;m.points=[self.point(px,py,.015) for px,py in data['free'].reshape(-1,2)];self.free_marker=m
  if self.free_marker is not None:markers.append(self.free_marker)
  m=self.marker(1,Marker.LINE_STRIP,(1.,.74,.12,1.));m.scale.x=.14;m.points=[self.point(v[1],v[2],.08) for v in self.traj[:i+1]];m.action=Marker.ADD if i>=1 else Marker.DELETE;markers.append(m)
  m=self.marker(2,Marker.CUBE,(1.,.12,.12,1.));m.pose.position=self.point(x,y,.28);m.pose.orientation.z=math.sin(float(yaw)/2);m.pose.orientation.w=math.cos(float(yaw)/2);m.scale.x=.6;m.scale.y=.6;m.scale.z=.45;markers.append(m)
  m=self.marker(3,Marker.ARROW,(1.,.3,.18,1.));m.scale.x=.14;m.scale.y=.32;m.scale.z=.35;m.points=[self.point(x,y,.65),self.point(x+1.5*math.cos(yaw),y+1.5*math.sin(yaw),.65)];markers.append(m)
  pi=max(0,min(len(self.paths)-1,int(np.searchsorted(self.path_times,elapsed,side='right')-1)))
  m=self.marker(4,Marker.LINE_STRIP,(.95,.95,.95,.95));m.scale.x=.07;m.points=[self.point(p[0],p[1],.12) for p in self.paths[pi]['points']];m.action=Marker.ADD if elapsed>=self.paths[0]['elapsed_s'] and len(m.points)>=2 else Marker.DELETE;markers.append(m)
  self.pub.publish(MarkerArray(markers=markers))
  hud=ROOT/'hud.tmp';hud.write_text(f'录包回放 {rate:g}倍速   实验时间 {elapsed:06.1f} / 600 秒   累计里程 {distance:6.1f} 米   观测体积代理 {volume:7.1f} m³',encoding='utf-8');hud.replace(ROOT/'hud.txt')
rclpy.init();node=Player()
try:rclpy.spin(node)
finally:node.destroy_node();rclpy.shutdown()
