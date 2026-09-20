#!/usr/bin/env python3
"""Lidar-only elevation raster -> real Scout eight-direction student -> GridMap."""
import sys,time,json,argparse,os
from pathlib import Path
import numpy as np,torch
from scipy.spatial import cKDTree
from scipy.ndimage import uniform_filter
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from nav_msgs.msg import Odometry
from grid_map_msgs.msg import GridMap
from std_msgs.msg import Float32MultiArray,MultiArrayDimension
sys.path.insert(0,'/home/lzz/my test/eletranskit_scout/src/ht_traversability_ros2')
from ht_traversability_ros2.model import load_student_model

class LiveHT(Node):
 def __init__(self,out):
  super().__init__('live_student_ht');torch.set_num_threads(2);self.model=load_student_model('/home/lzz/下载/original_scout/mini_25_training/runs/formal/student/best_epoch_weights.pth',torch.device('cpu'));self.cells={};self.pos=None;self.out=out;self.count=0;self.scans=0;self.lastscan=0
  self.pub=self.create_publisher(GridMap,'/ht_traversability/global_local',1)
  self.create_subscription(PointCloud2,'/registered_scan',self.scan,qos_profile_sensor_data);self.create_subscription(Odometry,'/state_estimation',self.odom,qos_profile_sensor_data);self.create_timer(.5,self.infer)
 def odom(self,msg):self.pos=(msg.pose.pose.position.x,msg.pose.pose.position.y)
 def scan(self,msg):
  if msg.header.frame_id not in ['map','/map']:raise RuntimeError('Unexpected cloud frame '+msg.header.frame_id)
  xyz=point_cloud2.read_points_numpy(msg,field_names=('x','y','z'),skip_nans=True);self.lastscan=time.monotonic();self.scans+=1
  ids=np.floor(xyz[:,:2]/.1).astype(int);unique,inverse=np.unique(ids,axis=0,return_inverse=True);z=np.full(len(unique),np.inf);np.minimum.at(z,inverse,xyz[:,2])
  for k,v in zip(map(tuple,unique),z):self.cells[k]=min(self.cells.get(k,np.inf),float(v))
 def infer(self):
  if self.pos is None or not self.cells or time.monotonic()-self.lastscan>2:return
  t=time.monotonic();n=291;res=21/513;cx,cy=self.pos
  # Same orientation as yaw=0 rotated training patches: rows -X, columns -Y.
  axis=((n-1)/2-np.arange(n))*res;xx,yy=np.meshgrid(cx+axis,cy+axis,indexing='ij');keys=np.array(list(self.cells));xy=(keys+.5)*.1;z=np.array(list(self.cells.values()));sel=(np.abs(xy[:,0]-cx)<8)&(np.abs(xy[:,1]-cy)<8)
  if not sel.any():return
  distances,near=cKDTree(xy[sel]).query(np.c_[xx.ravel(),yy.ravel()]);h=z[sel][near].reshape(n,n).astype('float32');known=distances.reshape(n,n)<=.25
  valid=uniform_filter(known.astype(float),size=51,mode='constant')[25:-25,25:-25]>=.9
  with torch.inference_mode():p=torch.softmax(self.model(torch.from_numpy(h[None,None])),dim=2)[0,:,1].numpy()
  msg=GridMap();msg.header.frame_id='map';msg.header.stamp=self.get_clock().now().to_msg();msg.info.resolution=res;msg.info.length_x=msg.info.length_y=n*res;msg.info.pose.position.x=cx;msg.info.pose.position.y=cy;msg.info.pose.orientation.w=1.
  msg.layers=[f'ht_dir_{i}' for i in range(8)]+['ht_valid']
  for i in range(9):
   a=np.full((n,n),np.nan if i<8 else 0,dtype='float32');a[25:-25,25:-25]=np.where(valid,p[i],np.nan) if i<8 else valid
   layer=Float32MultiArray();layer.layout.dim=[MultiArrayDimension(label='column_index',size=n,stride=n*n),MultiArrayDimension(label='row_index',size=n,stride=n)];layer.data=a.flatten(order='F').tolist();msg.data.append(layer)
  self.pub.publish(msg);self.count+=1
  if self.count==10 and os.environ.get('HT_SNAPSHOT'):np.savez_compressed(os.environ['HT_SNAPSHOT'],height=h,known=known,valid=valid,p=p,center=np.array(self.pos),resolution=res)
  if self.count%10==0:print(json.dumps({'maps':self.count,'scans':self.scans,'valid_fraction':float(valid.mean()),'center_valid':bool(valid[120,120]),'center_footprint_valid_fraction':float(valid[105:136,105:136].mean()),'p_quantiles':np.quantile(p[:,valid],[.1,.5,.9]).tolist() if valid.any() else [],'seconds':time.monotonic()-t}),flush=True)

def main():
 rclpy.init();node=LiveHT(None)
 try:rclpy.spin(node)
 except KeyboardInterrupt:pass
 finally:node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
