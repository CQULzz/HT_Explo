import rclpy,time,copy,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import TransformStamped, PolygonStamped, Point32
from grid_map_msgs.msg import GridMap
from std_msgs.msg import Bool, String
import os
from pathlib import Path
from scene_config import load_scene_config
from start_gate import StartGate
from tf2_ros import TransformBroadcaster,StaticTransformBroadcaster
def source_ready(pending, latest_pose_ns, now_ns):
 """Partition original scans only when measured pose and ROS time cover them."""
 ready=[];keep=[]
 for item in pending:
  wall,m=item;stamp=m.header.stamp.sec*10**9+m.header.stamp.nanosec
  (ready if stamp<=latest_pose_ns and stamp<=now_ns else keep).append(item)
 return ready,keep

class Adapter(Node):
 def __init__(self):
  super().__init__('pcd_sim_adapter');self.set_parameters([rclpy.parameter.Parameter('use_sim_time',value=True)])
  self.tb=TransformBroadcaster(self);self.sb=StaticTransformBroadcaster(self)
  self.odom=self.create_publisher(Odometry,'/sim/fixposition_odom',20);self.cloud=self.create_publisher(PointCloud2,'/sim/raw_cloud',5);self.start=self.create_publisher(Bool,'/ht_real/exploration_start',10)
  ts=[]
  for parent,child,xyz in [('map','FP_ENU0',[0,0,0]),('base_link','FP_POI',[.2005158179045505,0,.4242]),('base_link','rslidar',[.1725,0,.5502])]:
   t=TransformStamped();t.header.frame_id=parent;t.child_frame_id=child;t.transform.translation.x,t.transform.translation.y,t.transform.translation.z=map(float,xyz);t.transform.rotation.w=1.;ts.append(t)
  self.configure_start()
  self.sb.sendTransform(ts);self.create_subscription(Odometry,'/sim/ground_truth',self.pose,100);self.create_subscription(PointCloud2,'/sim/raw_points/points',self.scan,qos_profile_sensor_data);self.n=0;self.t0=None;self.pending=[];self.latest_ns=-1;self.queue_delay_s=[];self.source_age_s=[]
  self.create_timer(.02,self.flush);self.create_timer(1.,self.start_tick)
 def configure_start(self):
  self.start_policy=os.environ.get('HT_SIM_START_POLICY','legacy')
  if self.start_policy not in ('ready','legacy'):raise ValueError('Invalid simulation start policy')
  self.scene=load_scene_config(Path(os.environ.get('HT_SIM_RUNTIME',Path(__file__).parent)),os.environ.get('HT_SIM_SCENE_CONFIG'))
  self.start_status=self.create_publisher(String,'/sim/start_status',10)
  self.boundary_publishers=[self.create_publisher(PolygonStamped,topic,1) for topic in
      ['/ht_real/navigation_boundary','/ht_real/coverage_boundary']]
  self.boundary_cycles=0
  self.boundary_ack=None
  self.create_subscription(String,'/ht_real/tare_boundary_status',self.boundary_applied,10)
  self.start_wall=time.monotonic()
  self.gate=StartGate(('odometry','registered_scan','terrain'))
  self.create_subscription(Odometry,'/ht_real/odometry',self.start_odometry,qos_profile_sensor_data)
  self.create_subscription(PointCloud2,'/ht_real/registered_scan',self.start_scan,qos_profile_sensor_data)
  if os.environ.get('HT_SIM_NAVIGATION','ht')=='ht':
   self.create_subscription(GridMap,'/ht_real/traversability',self.start_map,1)
  else:
   self.create_subscription(PointCloud2,'/ht_real/terrain_map_ext',self.start_terrain,1)

 def boundary_applied(self,msg):
  try:
   status=json.loads(msg.data)
   applied=min(float(status['coverage_source_s']),float(status['navigation_source_s']))
   if np.isfinite(applied) and applied>0:self.boundary_ack=(applied,time.monotonic())
  except (ValueError,TypeError,KeyError):
   self.boundary_ack=None

 def start_observe(self,name,msg):
  stamp=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9
  self.gate.observe(name,stamp,time.monotonic())

 def start_odometry(self,msg):
  if msg.header.frame_id=='map' and msg.child_frame_id=='base_link':self.start_observe('odometry',msg)

 def start_scan(self,msg):
  if msg.header.frame_id=='map' and msg.width*msg.height>0:self.start_observe('registered_scan',msg)

 def start_terrain(self,msg):
  if msg.header.frame_id=='map' and msg.width*msg.height>0:self.start_observe('terrain',msg)

 def start_map(self,msg):
  if msg.header.frame_id=='map' and 'ht_valid' in msg.layers and msg.data:
   self.start_observe('terrain',msg)

 def start_tick(self):
  boundary=PolygonStamped()
  boundary.header.frame_id='map';boundary.header.stamp=self.get_clock().now().to_msg()
  boundary.polygon.points=[Point32(x=float(x),y=float(y),z=0.) for x,y in self.scene.navigation_polygon]
  for publisher in self.boundary_publishers:publisher.publish(boundary)
  self.boundary_cycles+=1
  if self.start_policy=='legacy':
   self.start.publish(Bool(data=True));return
  now=self.get_clock().now().nanoseconds/1e9
  applied=self.boundary_ack is not None and 0<=now-self.boundary_ack[0]<=2.5 and 0<=time.monotonic()-self.boundary_ack[1]<=2.5
  delivered=applied and self.boundary_cycles>=2 and all(p.get_subscription_count()>0 for p in self.boundary_publishers)
  result=self.gate.evaluate(now,time.monotonic(),delivered)
  self.start_status.publish(String(data=json.dumps(result)))
  if self.gate.clock_fault:raise RuntimeError('Simulation clock reset; restart required')
  if result['release']:
   directory=os.environ.get('HT_SIM_OUTPUT')
   if directory:
    path=Path(directory)/'START_GATE.json'
    if path.exists():raise FileExistsError(path)
    path.write_text(json.dumps(result,indent=2))
  if result['started']:
   self.start.publish(Bool(data=True))
  elif time.monotonic()-self.start_wall>45:
   raise RuntimeError('Simulation start readiness timeout: '+json.dumps(result))

 def pose(self,m):
  p=m.pose.pose;q=p.orientation;r=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();v=np.array([p.position.x,p.position.y,p.position.z]);t=TransformStamped();t.header=m.header;t.child_frame_id='base_link';t.transform.translation.x,t.transform.translation.y,t.transform.translation.z=v.tolist();t.transform.rotation=q;self.tb.sendTransform(t)
  self.latest_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec
  o=copy.deepcopy(m);o.header.frame_id='FP_ENU0';o.child_frame_id='FP_POI';pos=v+r@np.array([.2005158179045505,0,.4242]);o.pose.pose.position.x,o.pose.pose.position.y,o.pose.pose.position.z=pos.tolist()
  # Gz ground-truth twist is model/body-frame. Translate it to the POI body origin.
  w=o.twist.twist.angular;omega=np.array([w.x,w.y,w.z]);vv=o.twist.twist.linear;vel=np.array([vv.x,vv.y,vv.z])+np.cross(omega,[.2005158179045505,0,.4242]);vv.x,vv.y,vv.z=vel.tolist();self.odom.publish(o);self.flush()
 def scan(self,m):
  m.header.frame_id='rslidar';self.pending.append((time.monotonic(),m));self.pending=self.pending[-5:];self.flush()
 def flush(self):
  now_ns=self.get_clock().now().nanoseconds
  ready,self.pending=source_ready(self.pending,self.latest_ns,now_ns)
  for wall,m in ready:
   stamp_ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec
   self.cloud.publish(m);self.n+=1
   self.queue_delay_s.append(time.monotonic()-wall);self.source_age_s.append((now_ns-stamp_ns)/1e9)
def main():
 rclpy.init();n=Adapter()
 try:rclpy.spin(n)
 except KeyboardInterrupt:pass
 finally:
  def quant(v):return None if not v else dict(zip(['p50','p95','max'],map(float,np.percentile(v,[50,95,100]))))
  print(json.dumps({'adapter_published_scans':n.n,'local_queue_wait_s':quant(n.queue_delay_s),'publish_ros_source_age_s':quant(n.source_age_s),'scope':'Adapter queue/clock only; downstream exact TF and original age gates remain enforced'}),flush=True)
  n.destroy_node();rclpy.try_shutdown()

if __name__=='__main__':main()
