from pathlib import Path
import sys,time,json,collections,math,csv,os
import numpy as np,cv2,rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.time import Time
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from std_msgs.msg import String,Bool
from geometry_msgs.msg import Twist
from tf2_ros import Buffer,TransformListener,TransformException
from grid_map_msgs.msg import GridMap
from scipy.spatial.transform import Rotation
class Observer(Node):
 def __init__(self, output, runtime):
  super().__init__('pcd_sim_observer');self.set_parameters([rclpy.parameter.Parameter('use_sim_time',value=True)])
  self.output=Path(output);self.runtime=Path(runtime);self.completion=None
  self.output.mkdir(exist_ok=True)
  self.tf=Buffer();self.listener=TransformListener(self.tf,self);self.free=set();self.path=[];self.distance=0.;self.pose=None;self.status={};self.cmd=[0.,0.];self.count=collections.Counter();self.completed=False;self.t0=None;self.wall0=time.monotonic();self.last_scan=-100;self.last_snap=-100;self.scans=0
  self.relay=self.create_publisher(PointCloud2,'/sim_evidence/scan',2)
  self.create_subscription(Odometry,'/sim/ground_truth',self.odom,30);self.create_subscription(PointCloud2,'/ht_real/registered_scan',self.scan,qos_profile_sensor_data);self.create_subscription(Twist,'/sim/cmd_vel',self.command,10);self.create_subscription(Bool,'/ht_real/mission_completed',lambda m:setattr(self,'completed',self.completed or m.data),10)
  self.create_subscription(GridMap,'/ht_real/traversability',self.grid,qos_profile_sensor_data)
  for k in ['runtime_status','input_status','ht_execution_status','ht_follower_status','mission_state','input_performance','ht_performance']:
   self.create_subscription(String,'/ht_real/'+k,lambda m,k=k:self.stat(k,m),10)
  self.events=open(self.output/'events.jsonl','w');self.f=open(self.output/'metrics.csv','w');self.writer=csv.writer(self.f);self.writer.writerow(['sim_time','elapsed_sim','elapsed_wall','x','y','z','distance_m','observed_free_volume_m3','v_cmd','w_cmd','mission_completed','runtime_reason','execution','follower','maps','sampled_scans'])
  self.video=cv2.VideoWriter(str(self.output/'trajectory.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),2,(960,640));assert self.video.isOpened();self.frames=0
  self.bg=self.background();self.create_timer(.5,self.sample)
 def background(self):
  a=np.full((640,960,3),245,np.uint8);p=np.load(self.runtime/'local_map.npy');p=p[(abs(p[:,0])<15)&(abs(p[:,1])<15)&(p[:,2]<3)]
  for x,y,z in p[::2]:cv2.circle(a,self.xy(x,y),1,(140,150,140) if z<-.6 else (65,80,110),-1)
  return a
 def xy(self,x,y):return (int(320+x*18),int(320-y*18))
 def stat(self,k,m):
  self.status[k]=m.data;self.count[k]+=1;self.events.write(json.dumps({'time':self.get_clock().now().nanoseconds/1e9,'topic':k,'data':m.data})+'\n')
 def command(self,m):self.cmd=[m.linear.x,m.angular.z]
 def odom(self,m):
  p=m.pose.pose.position;v=np.array([p.x,p.y,p.z]);t=m.header.stamp.sec+m.header.stamp.nanosec/1e9
  if self.pose is not None:self.distance+=float(np.linalg.norm(v[:2]-self.pose[:2]))
  self.pose=v;self.path.append((t,*v));self.count['odom']+=1
 def grid(self,m):
  self.count['map']+=1;t=m.header.stamp.sec+m.header.stamp.nanosec/1e9
  if t-self.last_snap>=10:
   self.last_snap=t;np.savez_compressed(self.output/f'ht_snapshot_{t:.2f}.npz',stamp=t,layers=np.array(m.layers),data=np.array([np.asarray(x.data) for x in m.data]),resolution=m.info.resolution,position=[m.info.pose.position.x,m.info.pose.position.y],start=[m.outer_start_index,m.inner_start_index])
 def scan(self,m):
  t=m.header.stamp.sec+m.header.stamp.nanosec/1e9
  if t-self.last_scan<1:return
  self.last_scan=t;self.relay.publish(m)
  try:tf=self.tf.lookup_transform('map','rslidar',Time.from_msg(m.header.stamp))
  except TransformException:self.count['metric_tf_missing']+=1;return
  if self.t0 is None:self.t0=t;(self.output/'READY.json').write_text(json.dumps({'first_sensor_cycle_sim':t,'wall':time.time()}))
  tr=tf.transform.translation;origin=np.array([tr.x,tr.y,tr.z]);pts=point_cloud2.read_points_numpy(m,field_names=['x','y','z'],skip_nans=True)[::32,:3];rays=pts-origin;length=np.linalg.norm(rays,axis=1);valid=(length>.4)&(length<30);rays=rays[valid];length=length[valid];unit=rays/length[:,None]
  ds=np.arange(.2,15,.2);points=origin+unit[:,None,:]*ds[None,:,None];mask=ds[None,:]<(length[:,None]-.25);mask&=(points[:,:,2]>-1.5)&(points[:,:,2]<2.5)&(abs(points[:,:,0])<15)&(abs(points[:,:,1])<15);v=np.floor((points[mask]+[20,20,5])/.2).astype(np.int64);keys=v[:,0]*1000000+v[:,1]*1000+v[:,2];self.free.update(map(int,np.unique(keys)));self.scans+=1
 def sample(self):
  t=self.get_clock().now().nanoseconds/1e9
  if self.pose is None:return
  elapsed=t-self.t0 if self.t0 is not None else -1
  reason=self.status.get('runtime_status','')
  try:reason=json.loads(reason).get('reason','')
  except ValueError:pass
  self.writer.writerow([t,elapsed,time.monotonic()-self.wall0,*self.pose,self.distance,len(self.free)*.008,*self.cmd,int(self.completed),reason,self.status.get('ht_execution_status',''),self.status.get('ht_follower_status',''),self.count['map'],self.scans]);self.f.flush();self.events.flush()
  im=self.bg.copy()
  if len(self.path)>1:cv2.polylines(im,[np.array([self.xy(x[1],x[2]) for x in self.path[::5]],np.int32)],False,(20,40,235),2)
  cv2.circle(im,self.xy(*self.pose[:2]),5,(0,0,255),-1)
  for i,line in enumerate(['Recorded PCD scene / actual simulated trajectory',f'sim elapsed {elapsed:.1f}s; wall {time.monotonic()-self.wall0:.1f}s',f'distance {self.distance:.3f} m',f'sampled ray free volume {len(self.free)*.008:.2f} m3',f'cmd v={self.cmd[0]:.2f} w={self.cmd[1]:.2f}',reason[:65],f'completed={self.completed} maps={self.count["map"]}']):cv2.putText(im,line,(12,25+i*25),cv2.FONT_HERSHEY_SIMPLEX,.55,(15,15,15),1,cv2.LINE_AA)
  self.video.write(im);self.frames+=1
  if self.t0 is not None and elapsed>=float(os.environ.get("HT_SIM_DURATION","600")):self.completion=({'elapsed_sim':elapsed,'elapsed_wall':time.monotonic()-self.wall0,'distance':self.distance,'free_volume':len(self.free)*.008,'mission_completed':self.completed,'counts':dict(self.count),'video_frames':self.frames});raise SystemExit
 def close(self):
  self.video.release();self.f.close();self.events.close();np.save(self.output/'trajectory.npy',np.array(self.path));np.save(self.output/'free_voxel_keys.npy',np.array(sorted(self.free),dtype=np.int64))

def main(argv=None):
 from collection_lifecycle import write_completion
 args=sys.argv[1:] if argv is None else argv
 if len(args)!=1:raise ValueError('Expected output directory')
 output=Path(args[0]);runtime=Path(__file__).parent
 rclpy.init();node=None;completion=None
 try:
  node=Observer(output,runtime)
  try:rclpy.spin(node)
  except (KeyboardInterrupt,SystemExit):pass
 finally:
  try:
   if node is not None:
    try:
     node.close()
     completion=node.completion
    finally:node.destroy_node()
  finally:rclpy.try_shutdown()
 # Failed IO/entity cleanup propagates before DONE; no false success marker.
 write_completion(output,completion)

if __name__=='__main__':main()
