import rclpy,time,copy,json,sys
import numpy as np
from scipy.spatial.transform import Rotation
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import TransformStamped
from std_msgs.msg import Bool
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
  self.sb.sendTransform(ts);self.create_subscription(Odometry,'/sim/ground_truth',self.pose,100);self.create_subscription(PointCloud2,'/sim/raw_points/points',self.scan,qos_profile_sensor_data);self.n=0;self.t0=None;self.pending=[];self.latest_ns=-1;self.queue_delay_s=[];self.source_age_s=[]
  self.create_timer(.02,self.flush);self.create_timer(1.,lambda:self.start.publish(Bool(data=True)))
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
