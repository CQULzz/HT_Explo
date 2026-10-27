"""Real Scout inputs; external localization/TF remains the sole TF authority."""
from collections import deque
from copy import deepcopy
import math
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import rclpy
from rclpy.node import Node
from rclpy.time import Time
from rclpy.qos import QoSProfile, ReliabilityPolicy
from ament_index_python.packages import get_package_share_directory
from tf2_ros import Buffer, TransformListener, TransformException
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
from grid_map_msgs.msg import GridMap
from std_msgs.msg import String, Int8
from .geometry import load_calibration,transform,convert_reference,transform_cloud,covariance


def pose_matrix(p):
    return transform([p.position.x,p.position.y,p.position.z],
                     [p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w])


def stamp_ns(msg):
    return msg.header.stamp.sec*10**9+msg.header.stamp.nanosec


def set_pose(p,t):
    p.position.x,p.position.y,p.position.z=map(float,t[:3,3])
    p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w=map(float,Rotation.from_matrix(t[:3,:3]).as_quat())


class ScoutInputs(Node):
    def __init__(self):
        super().__init__('ht_scout_inputs')
        default=Path(get_package_share_directory('ht_scout_bridge'))/'config/scout_extrinsics.yaml'
        self.profile,self.poi_base,self.poi_lidar=load_calibration(self.declare_parameter('calibration_file',str(default)).value)
        self.frames=self.profile['frames']
        self.age_layer=self.declare_parameter('source_age_layer','time').value
        if self.age_layer not in ('time','observation_age'):raise ValueError('Unknown measured age layer')
        self.max_age=float(self.declare_parameter('max_input_age',1.).value)
        if not math.isfinite(self.max_age) or self.max_age<=0:raise ValueError('Invalid max_input_age')
        self.twist_cov_frame=self.declare_parameter('twist_covariance_frame','parent').value
        if self.twist_cov_frame not in ('parent','child'):raise ValueError('Invalid twist covariance frame')
        self.buffer=Buffer();self.listener=TransformListener(self.buffer,self)
        self.status_pub=self.create_publisher(String,'/ht_real/input_status',5)
        self.stop_pub=self.create_publisher(Int8,'/ht_real/stop',5)
        self.odom_pub=self.create_publisher(Odometry,'/ht_real/odometry',20)
        self.cloud_pub=self.create_publisher(PointCloud2,'/ht_real/registered_scan',2)
        self.elevation_pub=self.create_publisher(GridMap,'/ht_real/elevation_raw',1)
        self.last_clock=None;self.fault=None;self.last_pose=None
        self.last_stamp={'odom':-1,'cloud':-1,'elevation':-1}
        self.pending={k:deque() for k in self.last_stamp}
        sensor=QoSProfile(depth=20,reliability=ReliabilityPolicy.BEST_EFFORT)
        self.odom_sub=self.create_subscription(Odometry,self.declare_parameter('odometry_topic','/fixposition/odometry_enu').value,
            lambda m:self.enqueue('odom',m),sensor)
        self.cloud_sub=self.create_subscription(PointCloud2,self.declare_parameter('cloud_topic','/rslidar_points').value,
            lambda m:self.enqueue('cloud',m),QoSProfile(depth=2,reliability=ReliabilityPolicy.BEST_EFFORT))
        self.elevation_sub=self.create_subscription(GridMap,self.declare_parameter('elevation_topic','/elevation_mapping_node/elevation_map_raw').value,
            lambda m:self.enqueue('elevation',m),QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE))
        self.timer=self.create_timer(.05,self.drain)

    def status(self,text):
        self.status_pub.publish(String(data=text))

    def latch(self,text):
        self.fault=text
        for q in self.pending.values():q.clear()
        self.stop_pub.publish(Int8(data=1));self.status(text)

    def clock_ok(self):
        now=self.get_clock().now().nanoseconds/1e9
        if self.last_clock is not None and now<self.last_clock-1e-6:self.latch('CLOCK_RESET_RESTART_REQUIRED')
        self.last_clock=now
        return now

    def lookup(self,parent,child,msg):
        # stamp0 would request latest TF and conceal temporal mismatch.
        if stamp_ns(msg)<=0:raise ValueError('Require positive source timestamp')
        if parent==child:return np.eye(4)
        tf=self.buffer.lookup_transform(parent,child,Time.from_msg(msg.header.stamp))
        p,q=tf.transform.translation,tf.transform.rotation
        return transform([p.x,p.y,p.z],[q.x,q.y,q.z,q.w])

    def check_static(self,child,expected,msg):
        actual=self.lookup(self.frames['poi'],child,msg)
        error=np.linalg.inv(expected)@actual
        if np.linalg.norm(error[:3,3])>.001 or Rotation.from_matrix(error[:3,:3]).magnitude()>.001:
            self.latch('EXTRINSICS_TF_MISMATCH_RESTART_REQUIRED')
            raise ValueError('External TF disagrees with configured calibration')

    def enqueue(self,kind,msg):
        self.clock_ok()
        if self.fault:return
        n=stamp_ns(msg)
        if n<=self.last_stamp[kind] or any(stamp_ns(m)==n for m in self.pending[kind]):return
        self.pending[kind].append(msg)
        self.pending[kind]=deque(sorted(self.pending[kind],key=stamp_ns))
        limit=64 if kind=='odom' else 10 if kind=='cloud' else 2
        while len(self.pending[kind])>limit:
            self.pending[kind].popleft();self.status(kind.upper()+'_QUEUE_OVERFLOW_DROPPED_OLDEST')
        self.drain()

    def drain(self):
        now=self.clock_ok()
        if self.fault:
            self.stop_pub.publish(Int8(data=1));return
        for kind,q in self.pending.items():
            while q and not self.fault:
                msg=q[0];age=now-stamp_ns(msg)/1e9
                if age>self.max_age or age<-.1 or stamp_ns(msg)<=0:
                    q.popleft();self.status(kind.upper()+'_SOURCE_TIME_INVALID');continue
                if stamp_ns(msg)<=self.last_stamp[kind]:q.popleft();continue
                try:
                    result=getattr(self,'convert_'+kind)(msg)
                except TransformException:
                    self.status(kind.upper()+'_WAIT_TIMESTAMPED_TF');break
                except (ValueError,OverflowError) as error:
                    if not self.fault:q.popleft()
                    self.status(kind.upper()+'_REJECTED: '+str(error));continue
                if self.fault:break
                q.popleft();self.last_stamp[kind]=stamp_ns(msg)
                getattr(self,kind+'_pub' if kind!='cloud' else 'cloud_pub').publish(result)
                self.status(kind.upper()+'_READY')

    def convert_odom(self,msg):
        if msg.header.frame_id!=self.frames['source_world'] or msg.child_frame_id!=self.frames['poi']:
            raise ValueError('Expected FP_ENU0/FP_POI odometry with nav2_mode=false; no frame renaming')
        self.check_static(self.frames['vehicle'],self.poi_base,msg)
        map_source=self.lookup(self.frames['world'],msg.header.frame_id,msg)
        source_poi=pose_matrix(msg.pose.pose)
        # Cross-check the external dynamic localization tree against ENU data.
        tf_poi=self.lookup(self.frames['world'],self.frames['poi'],msg)
        check=np.linalg.inv(map_source@source_poi)@tf_poi
        if np.linalg.norm(check[:3,3])>.02 or Rotation.from_matrix(check[:3,:3]).magnitude()>.02:
            self.latch('LOCALIZATION_TF_MISMATCH_RESTART_REQUIRED')
            raise ValueError('TF and odometry disagree at the same timestamp')
        a,b=msg.twist.twist.linear,msg.twist.twist.angular
        tc=covariance(msg.twist.covariance)
        if self.twist_cov_frame=='parent':
            j=np.zeros((6,6));j[:3,:3]=source_poi[:3,:3].T;j[3:,3:]=source_poi[:3,:3].T
            tc=j@tc@j.T
        t,v,w,pc,tc=convert_reference(map_source,source_poi,self.poi_base,
            [a.x,a.y,a.z],[b.x,b.y,b.z],msg.pose.covariance,tc)
        n=stamp_ns(msg)
        if self.last_pose is not None:
            old_n,old_t=self.last_pose;dt=(n-old_n)/1e9
            delta=np.linalg.inv(old_t)@t
            if dt<=0:raise ValueError('Nonincreasing odometry')
            if np.linalg.norm(delta[:3,3])>.75+3*dt or Rotation.from_matrix(delta[:3,:3]).magnitude()>.5+4*dt:
                self.latch('ODOM_JUMP_RESTART_REQUIRED');raise ValueError('Localization discontinuity')
        out=deepcopy(msg);out.header.frame_id=self.frames['world'];out.child_frame_id=self.frames['vehicle']
        set_pose(out.pose.pose,t)
        out.twist.twist.linear.x,out.twist.twist.linear.y,out.twist.twist.linear.z=map(float,v)
        out.twist.twist.angular.x,out.twist.twist.angular.y,out.twist.twist.angular.z=map(float,w)
        out.pose.covariance=pc.ravel().tolist();out.twist.covariance=tc.ravel().tolist()
        self.last_pose=(n,t)
        return out

    def convert_cloud(self,msg):
        if msg.header.frame_id!=self.frames['lidar']:raise ValueError('Expected calibrated rslidar-frame cloud')
        self.check_static(self.frames['lidar'],self.poi_lidar,msg)
        t=self.lookup(self.frames['world'],self.frames['poi'],msg)@self.poi_lidar
        out=transform_cloud(msg,t,self.profile.get('lidar_self_filter'));out.header.frame_id=self.frames['world']
        if not out.width:raise ValueError('No finite cloud points')
        return out

    def convert_elevation(self,msg):
        # Retain HT's tested metric contract; never resize a250-cell source or
        # create observation_age=0 for retained historical posterior cells.
        if msg.header.frame_id not in ('map','odom'):raise ValueError('Expected map/odom elevation frame')
        info=msg.info;r=info.resolution
        if (not math.isfinite(r) or not .040<=r<=.042 or
                any(not math.isclose(v/r,291,rel_tol=0,abs_tol=1e-6) for v in [info.length_x,info.length_y])):
            raise ValueError('Need native291x291 elevation; source250x250 must not be renamed/resized')
        if len(set(msg.layers))!=len(msg.layers) or len(msg.layers)!=len(msg.data):raise ValueError('Invalid layers')
        needed=['elevation','variance',self.age_layer]
        for name in needed:
            if name not in msg.layers:raise ValueError('Missing '+name+'; do not fabricate freshness')
            a=msg.data[msg.layers.index(name)];d=a.layout.dim
            if (len(d)!=2 or d[0].label!='column_index' or d[1].label!='row_index' or
                    d[0].size!=291 or d[1].size!=291 or d[0].stride!=291*291 or d[1].stride!=291 or
                    a.layout.data_offset!=0 or len(a.data)!=291*291):raise ValueError('Invalid layer layout')
        if not 0<=msg.outer_start_index<291 or not 0<=msg.inner_start_index<291:raise ValueError('Invalid circular buffer')
        source_pose=pose_matrix(info.pose)
        if abs(info.pose.position.z)>1e-6:raise ValueError('Require absolute elevation with neutral grid Z')
        if not np.allclose(source_pose[:3,:3],np.eye(3),atol=1e-6,rtol=0):raise ValueError('Rotated source grid requires explicit regridding')
        t=self.lookup(self.frames['world'],msg.header.frame_id,msg)
        if not np.allclose(t[:3,:3],np.eye(3),atol=1e-6,rtol=0):raise ValueError('Rotated world grid requires explicit regridding')
        out=deepcopy(msg);out.header.frame_id=self.frames['world'];set_pose(out.info.pose,t@source_pose)
        out.info.pose.position.z=0.0  # Heights below already carry the absolute world Z.
        out.layers=['elevation','variance','observation_age'];out.basic_layers=[n for n in out.basic_layers if n in out.layers]
        out.data=[deepcopy(msg.data[msg.layers.index(n)]) for n in needed]
        values=np.asarray(out.data[0].data,np.float64)+t[2,3]
        finite=np.isfinite(np.asarray(out.data[0].data));values=values.astype(np.float32)
        if not np.isfinite(values[finite]).all():raise ValueError('Elevation transform overflows')
        from array import array
        out.data[0].data=array('f',values.tobytes())
        return out


def main():
    rclpy.init();node=ScoutInputs()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:node.destroy_node();rclpy.try_shutdown()
