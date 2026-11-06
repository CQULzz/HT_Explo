"""Bound CMU commands for the PCD simulation; never an actual-car entry point."""
import math
import signal
import time
import json
import numpy as np
import rclpy
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Path
from std_msgs.msg import String
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from ht_scout_bridge.command_bridge import ScoutCommandBridge


def bounded(v,w,previous,dt):
    if not all(math.isfinite(x) for x in [v,w,dt]):return (0.,0.)
    v=float(np.clip(v,-.25,.4));w=float(np.clip(w,-.8,.8))
    if v==0 and w==0:return (0.,0.)
    dt=max(0.,min(dt,.1))
    return (float(np.clip(v,previous[0]-.5*dt,previous[0]+.5*dt)),
            float(np.clip(w,previous[1]-1.2*dt,previous[1]+1.2*dt)))


def intersects(points,pose,v,w):
    """Same .7m + half 0.2m grid diagonal, +/- .5m collision envelope.

    Include the current pose and a .4s command sweep. A fresh empty collision
    cloud can pass; missing geometry is handled separately and never passes.
    """
    x,y,z,yaw=pose
    radius=.7+math.sqrt(2)*.1
    for t in np.linspace(0,.4,9):
        if abs(w)<1e-6:dx=v*t*math.cos(yaw);dy=v*t*math.sin(yaw)
        else:
            dx=v/w*(math.sin(yaw+w*t)-math.sin(yaw))
            dy=-v/w*(math.cos(yaw+w*t)-math.cos(yaw))
        if np.any((np.hypot(points[:,0]-x-dx,points[:,1]-y-dy)<=radius)&
                  (abs(points[:,2]-z)<=.5)):return True
    return False


class TareSimBridge(ScoutCommandBridge):
    def __init__(self):
        super().__init__()
        if self.output_topic!='/sim/cmd_vel' or self.input_topic!='/sim/tare/raw_command':
            raise ValueError('This comparison bridge only accepts isolated simulation topics')
        self.path_timeout=float(self.declare_parameter('path_timeout',3.).value)
        self.geometry_timeout=float(self.declare_parameter('geometry_timeout',3.).value)
        if not all(math.isfinite(value) and value>0 for value in (self.path_timeout,self.geometry_timeout)):
            raise ValueError('Invalid TARE simulation freshness timeout')
        self.path=None;self.geometry=None;self.previous=(0.,0.);self.last_receive=None
        self.state='WAIT_START';self.state_time=None
        self.create_subscription(Path,'/sim/tare/path',lambda m:setattr(self,'path',(m,time.monotonic())),5)
        self.create_subscription(PointCloud2,'/ht_real/collision_cloud',self.collision,1)
        self.create_subscription(String,'/ht_real/mission_state',self.mission,10)
        self.runtime_pub=self.create_publisher(String,'/ht_real/runtime_status',1)
        self.follower_pub=self.create_publisher(String,'/ht_real/ht_follower_status',1)

    def mission(self,m):self.state=m.data;self.state_time=time.monotonic()

    def collision(self,m):
        points=point_cloud2.read_points_numpy(m,field_names=['x','y','z'],skip_nans=True)
        self.geometry=(m.header,np.asarray(points,dtype=float).reshape(-1,3),time.monotonic())

    def receive(self,msg):
        now=time.monotonic()
        if msg.header.frame_id!='vehicle' or not all(math.isfinite(x) for x in [msg.twist.linear.x,msg.twist.angular.z]):self.command=None;return
        # CMU is driven by base_link odometry with zero sensorOffsets. Its
        # 'vehicle' axes therefore coincide with this base_link command frame.
        v,w=bounded(msg.twist.linear.x,msg.twist.angular.z,self.previous,
                    .02 if self.last_receive is None else now-self.last_receive)
        self.previous=(v,w);self.last_receive=now
        out=TwistStamped();out.header=msg.header;out.header.frame_id='base_link'
        out.twist.linear.x=v;out.twist.angular.z=w
        self.command=(out,now)

    def reason(self):
        now=self.get_clock().now().nanoseconds/1e9;steady=time.monotonic()
        if self.state_time is None or not 0<=steady-self.state_time<=3:return 'TARE_STATE_STALE'
        if self.state not in ['EXPLORING','RETURNING_HOME']:return 'TARE_'+self.state
        if not self.path:return 'TARE_PATH_MISSING'
        path,received=self.path;stamp=path.header.stamp.sec+path.header.stamp.nanosec/1e9
        if not path.poses or not 0<=steady-received<=self.path_timeout or not 0<=now-stamp<=self.path_timeout:return 'TARE_PATH_STALE_OR_EMPTY'
        if not self.geometry:return 'GEOMETRY_MISSING'
        header,points,received=self.geometry;stamp=header.stamp.sec+header.stamp.nanosec/1e9
        if header.frame_id!='map' or not 0<=steady-received<=self.geometry_timeout or not 0<=now-stamp<=self.geometry_timeout:return 'GEOMETRY_STALE_OR_INVALID'
        self.permission=(True,steady)
        reason=super().reason()
        if reason:return reason
        p=self.odom[0].pose.pose.position;q=self.odom[0].pose.pose.orientation
        yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
        command=self.command[0].twist
        if intersects(points,(p.x,p.y,p.z,yaw),command.linear.x,command.angular.z):return 'GEOMETRY_COMMAND_BLOCKED'
        return ''

    def tick(self):
        super().tick()
        reason=self.reason() or 'TARE_GEOMETRIC_COMMAND'
        if reason!='TARE_GEOMETRIC_COMMAND':self.previous=(0.,0.)
        self.follower_pub.publish(String(data=reason))
        self.runtime_pub.publish(String(data=json.dumps({'reason':reason,'baseline':'current-fork TARE geometric + CMU','mission':self.state})))


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    stop=False
    def request_stop(*args):
        nonlocal stop
        stop=True
    signal.signal(signal.SIGINT,request_stop);signal.signal(signal.SIGTERM,request_stop)
    node=TareSimBridge()
    try:
        while rclpy.ok() and not stop:rclpy.spin_once(node,timeout_sec=.1)
    finally:
        from geometry_msgs.msg import Twist
        node.pub.publish(Twist());node.destroy_node();rclpy.try_shutdown()


if __name__=='__main__':main()
