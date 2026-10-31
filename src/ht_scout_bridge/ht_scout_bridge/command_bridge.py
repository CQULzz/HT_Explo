"""Explicit opt-in TwistStamped -> Scout Twist adapter with a stop watchdog."""
import math
import time
import signal
import rclpy
from rclpy.node import Node
from rclpy.clock import Clock, ClockType
from rclpy.signals import SignalHandlerOptions
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool, Int8, String
from rclpy.qos import qos_profile_sensor_data


def command_allowed(msg, now, age, max_linear, max_angular):
    stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
    v=msg.twist
    values=[v.linear.x,v.linear.y,v.linear.z,v.angular.x,v.angular.y,v.angular.z]
    return (msg.header.frame_id=='base_link' and all(math.isfinite(x) for x in values)
            and 0<=now-stamp<=age and abs(v.linear.x)<=max_linear and abs(v.angular.z)<=max_angular
            and all(abs(x)<=1e-9 for x in [v.linear.y,v.linear.z,v.angular.x,v.angular.y]))


class ScoutCommandBridge(Node):
    def __init__(self):
        super().__init__('scout_command_bridge')
        self.input_topic=self.declare_parameter('input_topic','/ht_real/cmd_vel_stamped').value
        output=self.declare_parameter('output_topic','/cmd_vel').value
        if output==self.input_topic:raise ValueError('Input and output topics must differ')
        self.timeout=float(self.declare_parameter('command_timeout',.3).value)
        self.permission_timeout=float(self.declare_parameter('permission_timeout',3.).value)
        self.max_linear=float(self.declare_parameter('max_linear_speed',.4).value)
        self.max_angular=float(self.declare_parameter('max_angular_speed',.8).value)
        if not all(math.isfinite(x) and x>0 for x in [self.timeout,self.permission_timeout,self.max_linear,self.max_angular]):
            raise ValueError('Invalid command bridge limits')
        self.output_topic=output;self.command=None;self.permission=None;self.odom=None
        self.stopped=False;self.clock_fault=False;self.last_ros=None
        self.pub=self.create_publisher(Twist,output,1)
        self.status=self.create_publisher(String,'/ht_real/command_bridge_status',1)
        self.create_subscription(TwistStamped,self.input_topic,self.receive,1)
        self.create_subscription(Bool,'/ht_real/ht_navigation_allowed',self.allow,1)
        self.create_subscription(Odometry,'/ht_real/odometry',self.pose,qos_profile_sensor_data)
        self.create_subscription(Int8,'/ht_real/stop',self.stop,1)
        # Receipt watchdogs use monotonic time. Their timer must keep running
        # when ROS time pauses or moves backwards as well.
        self.watchdog_clock=Clock(clock_type=ClockType.STEADY_TIME)
        self.watchdog_timer=self.create_timer(.05,self.tick,clock=self.watchdog_clock)
    def receive(self,msg):self.command=(msg,time.monotonic())
    def allow(self,msg):self.permission=(msg.data,time.monotonic())
    def pose(self,msg):self.odom=(msg,time.monotonic())
    def stop(self,msg):
        self.stopped=msg.data!=0
        if self.stopped:self.command=None;self.pub.publish(Twist())
    def reason(self):
        now=self.get_clock().now().nanoseconds*1e-9;steady=time.monotonic()
        if self.last_ros is not None and now<self.last_ros:self.clock_fault=True
        self.last_ros=now
        if self.clock_fault:return 'CLOCK_RESET_RESTART_REQUIRED'
        if self.stopped:return 'STOP'
        if len(self.get_publishers_info_by_topic(self.output_topic))!=1:return 'OUTPUT_OWNERSHIP_CONFLICT'
        if len(self.get_publishers_info_by_topic(self.input_topic))!=1:return 'INPUT_OWNERSHIP_CONFLICT'
        if not self.permission or not self.permission[0] or not 0<=steady-self.permission[1]<=self.permission_timeout:return 'PERMISSION_MISSING_OR_STALE'
        if not self.odom:return 'ODOMETRY_MISSING'
        odom,received=self.odom;stamp=odom.header.stamp.sec+odom.header.stamp.nanosec*1e-9
        if odom.header.frame_id!='map' or odom.child_frame_id!='base_link' or not 0<=now-stamp<=.5 or not 0<=steady-received<=.5:return 'ODOMETRY_STALE_OR_INVALID'
        if not self.command:return 'COMMAND_MISSING'
        msg,received=self.command
        if not 0<=steady-received<=self.timeout or not command_allowed(msg,now,self.timeout,self.max_linear,self.max_angular):return 'COMMAND_STALE_OR_INVALID'
        return ''
    def tick(self):
        reason=self.reason()
        self.pub.publish(Twist() if reason else self.command[0].twist)
        self.status.publish(String(data=reason or 'FORWARDING'))


def main():
    rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
    def request_stop(signum,frame):raise KeyboardInterrupt
    signal.signal(signal.SIGINT,request_stop)
    signal.signal(signal.SIGTERM,request_stop)
    node=ScoutCommandBridge()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:
        if rclpy.ok():node.pub.publish(Twist())
        node.destroy_node();rclpy.try_shutdown()
