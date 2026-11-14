#!/usr/bin/env python3
"""Read-only observed motion/coverage collection, plus one simulation start signal."""
import argparse,csv,json,math,time
from pathlib import Path
from collections import Counter,deque
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry,Path as RosPath
from geometry_msgs.msg import TwistStamped,PointStamped
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Bool,String
from grid_map_msgs.msg import GridMap

def stamp(m):return m.header.stamp.sec+m.header.stamp.nanosec*1e-9

def xyz(m):
 f={f.name:f.offset for f in m.fields}
 dtype=np.dtype({'names':['x','y','z'],'formats':['<f4']*3,'offsets':[f[k] for k in ['x','y','z']],'itemsize':m.point_step})
 a=np.ndarray((m.height,m.width),dtype=dtype,buffer=m.data,strides=(m.row_step,m.point_step))
 return np.column_stack([a[k].ravel() for k in ['x','y','z']])

class Collect(Node):
 def __init__(self,out):
  super().__init__('cmu_delivery_observer');self.out=out;self.count=Counter();self.last={};self.position=None;self.previous=None;self.distance=0.;self.yaw=0.;self.cmd=(0.,0.);self.finish=False
  self.pending={};self.poses={};self.free=set();self.surface=set();self.last_ray=-1e9;self.last_ht=None;self.start=None;self.last_row=0;self.received_paths=0;self.ht_ages=[]
  self.events=(out/'events.jsonl').open('w');self.csv=(out/'metrics.csv').open('w');self.writer=csv.DictWriter(self.csv,fieldnames=['elapsed_s','time','x','y','z','yaw','distance_m','sampled_free_volume_m3','surface_voxel_volume_m3','cmd_linear','cmd_angular','finish','odom_age_s','scan_age_s','ht_age_s']);self.writer.writeheader()
  self.start_pub=self.create_publisher(Bool,'/start_exploration',1)
  self.create_subscription(Odometry,'/state_estimation',self.odom,qos_profile_sensor_data)
  self.create_subscription(Odometry,'/state_estimation_at_scan',self.scan_pose,qos_profile_sensor_data)
  self.create_subscription(PointCloud2,'/registered_scan',self.scan,qos_profile_sensor_data)
  self.create_subscription(TwistStamped,'/cmd_vel',self.command,20)
  self.create_subscription(Bool,'/exploration_finish',lambda m:self.setfinish(m),10)
  self.create_subscription(GridMap,'/ht_traversability/global_local',self.ht,1)
  self.create_subscription(PointStamped,'/way_point',lambda m:self.event('waypoint',{'x':m.point.x,'y':m.point.y,'z':m.point.z}),10)
  self.create_subscription(RosPath,'/path',lambda m:self.path(m),10)
  for topic in ['/ht_minimal/recovery','/ht_minimal/local_selection','/ht_minimal/localPlanner','/ht_minimal/pathFollower','/ht_minimal/command_audit','/ht_minimal/path_rejection','/ht_minimal/command_projection','/ht_performance','/ht_runtime']:
   self.create_subscription(String,topic,lambda m,t=topic:self.event(t,json.loads(m.data)),100)
 def event(self,name,data):
  self.count[name]+=1;self.events.write(json.dumps({'time':self.get_clock().now().nanoseconds/1e9,'kind':name,'data':data},allow_nan=False)+'\n')
 def odom(self,m):
  p=m.pose.pose.position;q=m.pose.pose.orientation;now=stamp(m);self.position=(p.x,p.y,p.z);self.last['odom']=now;self.count['odom']+=1
  self.yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
  if self.start is not None and self.previous is not None:self.distance+=math.dist(self.previous[:2],self.position[:2])
  self.previous=self.position
 def scan_pose(self,m):
  p=m.pose.pose.position;self.poses[stamp(m)]=np.array([p.x,p.y,p.z]);
  if len(self.poses)>100:self.poses.pop(next(iter(self.poses)))
  for key in list(self.pending):
   if abs(key-stamp(m))<1e-6:self.process_scan(self.pending.pop(key))
 def command(self,m):self.cmd=(m.twist.linear.x,m.twist.angular.z);self.count['commands']+=1
 def setfinish(self,m):
  if m.data!=self.finish:self.event('finish_transition',{'finish':m.data})
  self.finish=m.data
 def path(self,m):
  self.count['paths']+=1
  if self.count['paths']%5==0:self.event('local_path',{'stamp':stamp(m),'frame':m.header.frame_id,'points':[[p.pose.position.x,p.pose.position.y] for p in m.poses]})
 def ht(self,m):
  self.count['ht_maps']+=1;self.last_ht=stamp(m);self.ht_ages.append(self.get_clock().now().nanoseconds/1e9-self.last_ht)
 def scan(self,m):
  self.count['scans']+=1;s=stamp(m);self.last['scan']=s
  self.pending[s]=m
  if len(self.pending)>30:self.pending.pop(next(iter(self.pending)))
  if s in self.poses:self.process_scan(self.pending.pop(s))
 def process_scan(self,m):
  s=stamp(m)
  if self.start is None or s-self.last_ray<1 or not self.poses:return
  k=min(self.poses,key=lambda k:abs(k-s))
  if abs(k-s)>.05:self.count['ray_unmatched']+=1;return
  self.last_ray=s;origin=self.poses[k];points=xyz(m);points=points[np.isfinite(points).all(1)]
  cells=np.floor(points/.5).astype(np.int64);self.surface.update(map(tuple,cells))
  if len(points)>1024:points=points[np.linspace(0,len(points)-1,1024).astype(int)]
  delta=points-origin;length=np.linalg.norm(delta,axis=1);good=length>.3;delta=delta[good];length=length[good]
  direction=delta/length[:,None];steps=np.arange(.25,12.,.25)
  rays=origin+direction[:,None,:]*steps[None,:,None];mask=steps[None,:]<(length[:,None]-.25)
  cells=np.unique(np.floor(rays[mask]/.5).astype(np.int64),axis=0);self.free.update(map(tuple,cells));self.count['ray_frames']+=1
 def row(self):
  if self.position is None:return
  now=self.get_clock().now().nanoseconds/1e9
  self.writer.writerow(dict(elapsed_s=time.monotonic()-self.start,time=now,x=self.position[0],y=self.position[1],z=self.position[2],yaw=self.yaw,distance_m=self.distance,sampled_free_volume_m3=len(self.free)*.125,surface_voxel_volume_m3=len(self.surface)*.125,cmd_linear=self.cmd[0],cmd_angular=self.cmd[1],finish=self.finish,odom_age_s=now-self.last.get('odom',now),scan_age_s=now-self.last.get('scan',now),ht_age_s='' if self.last_ht is None else now-self.last_ht));self.csv.flush();self.events.flush()

def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--duration',type=float,default=600);p.add_argument('--require-ht',action='store_true');p.add_argument('--attach',action='store_true');a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
 rclpy.init();n=Collect(a.output);deadline=time.monotonic()+300
 while time.monotonic()<deadline:
  rclpy.spin_once(n,timeout_sec=.1)
  if n.position is not None and n.count['scans']>=5 and (not a.require_ht or n.count['ht_maps']>=5):break
 else:raise RuntimeError('Inputs not ready in 300 seconds')
 n.start=time.monotonic();n.distance=0.;n.free.clear();n.surface.clear()
 (a.output/'START.json').write_text(json.dumps({'clock':n.get_clock().now().nanoseconds/1e9,'position':n.position,'duration':a.duration,'counts':n.count},indent=2))
 if not a.attach:n.start_pub.publish(Bool(data=True))
 last=0
 try:
  while time.monotonic()-n.start<a.duration:
   rclpy.spin_once(n,timeout_sec=.05)
   if time.monotonic()-last>=.5:n.row();last=time.monotonic()
 finally:
  n.row();summary={'elapsed_s':time.monotonic()-n.start,'distance_m':n.distance,'position':n.position,'sampled_free_volume_m3':len(n.free)*.125,'surface_voxel_volume_m3':len(n.surface)*.125,'finish':n.finish,'counts':n.count,'ht_source_age_s':None if not n.ht_ages else {k:float(np.quantile(n.ht_ages,q)) for k,q in [('p50',.5),('p95',.95),('p99',.99)]},'free_volume_definition':'union of sampled sensor rays at 0.5m voxel resolution, 1Hz/1024 endpoints/12m range; observation proxy, not ground truth'}
  (a.output/'SUMMARY.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True);n.csv.close();n.events.close();n.destroy_node();rclpy.shutdown()
if __name__=='__main__':main()
