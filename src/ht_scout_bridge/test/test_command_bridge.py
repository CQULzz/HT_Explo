"""Offline watchdog tests; isolated ROS domain selected by the test runner."""
import copy,math,time
from unittest.mock import Mock
import pytest,rclpy
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from std_msgs.msg import Bool,Int8
from ht_scout_bridge.command_bridge import ScoutCommandBridge,command_allowed

@pytest.fixture
def node():
    rclpy.init();n=ScoutCommandBridge()
    real=n.pub;n.pub=Mock();n.get_publishers_info_by_topic=lambda topic:[object()]
    stamp=n.get_clock().now().to_msg()
    cmd=TwistStamped();cmd.header.stamp=stamp;cmd.header.frame_id='base_link';cmd.twist.linear.x=.2
    odom=Odometry();odom.header.stamp=stamp;odom.header.frame_id='map';odom.child_frame_id='base_link'
    n.receive(cmd);n.pose(odom);n.allow(Bool(data=True))
    yield n
    n.destroy_node();rclpy.try_shutdown()

def test_valid_command_and_watchdog_zero(node):
    node.tick();assert node.pub.publish.call_args[0][0].linear.x==.2
    node.command=(node.command[0],time.monotonic()-.31)
    node.tick();assert node.pub.publish.call_args[0][0].linear.x==0

def test_hold_and_stop_publish_zero(node):
    node.allow(Bool(data=False));node.tick();assert node.pub.publish.call_args[0][0].linear.x==0
    node.allow(Bool(data=True));node.stop(Int8(data=1));node.tick()
    assert node.command is None and node.pub.publish.call_args[0][0].linear.x==0

def test_other_controller_and_odometry_timeout(node):
    node.get_publishers_info_by_topic=lambda topic:[1,2]
    node.tick();assert node.pub.publish.call_args[0][0].linear.x==0
    node.get_publishers_info_by_topic=lambda topic:[1]
    node.odom=(node.odom[0],time.monotonic()-.6)
    node.tick();assert node.pub.publish.call_args[0][0].linear.x==0

@pytest.mark.parametrize('kind',['nan','speed','yaw','frame','future','old','sideways'])
def test_bad_commands_rejected(node,kind):
    msg=node.command[0]
    if kind=='nan':msg.twist.linear.x=float('nan')
    if kind=='speed':msg.twist.linear.x=.41
    if kind=='yaw':msg.twist.angular.z=.81
    if kind=='frame':msg.header.frame_id='map'
    if kind=='future':msg.header.stamp.sec+=2
    if kind=='old':msg.header.stamp.sec-=2
    if kind=='sideways':msg.twist.linear.y=.1
    node.tick();assert node.pub.publish.call_args[0][0].linear.x==0


def test_permission_expiry_and_clock_reset_latch(node):
    node.permission=(True,time.monotonic()-3.1)
    node.tick();assert node.pub.publish.call_args[0][0].linear.x==0
    node.allow(Bool(data=True));node.last_ros=node.get_clock().now().nanoseconds*1e-9+1
    node.tick();assert node.pub.publish.call_args[0][0].linear.x==0
    assert node.clock_fault
    node.last_ros=0
    assert node.reason()=='CLOCK_RESET_RESTART_REQUIRED'


def test_ros_wire_forwards_then_zeroes_when_command_stream_stops():
    # Real DDS endpoints, isolated ROS domain/localhost supplied by test runner.
    rclpy.init();bridge=ScoutCommandBridge();source=rclpy.create_node('offline_command_bridge_probe')
    from geometry_msgs.msg import Twist
    from rclpy.executors import SingleThreadedExecutor
    pub=source.create_publisher(TwistStamped,'/ht_real/cmd_vel_stamped',1)
    permit=source.create_publisher(Bool,'/ht_real/ht_navigation_allowed',1)
    pose=source.create_publisher(Odometry,'/ht_real/odometry',1)
    seen=[];sub=source.create_subscription(Twist,'/cmd_vel',lambda m:seen.append(m.linear.x),10)
    executor=SingleThreadedExecutor();executor.add_node(source);executor.add_node(bridge)
    def run(seconds,commands):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            stamp=source.get_clock().now().to_msg()
            odom=Odometry();odom.header.stamp=stamp;odom.header.frame_id='map';odom.child_frame_id='base_link'
            pose.publish(odom);permit.publish(Bool(data=True))
            if commands:
                cmd=TwistStamped();cmd.header.stamp=stamp;cmd.header.frame_id='base_link';cmd.twist.linear.x=.2;pub.publish(cmd)
            executor.spin_once(timeout_sec=.01)
            time.sleep(.01)
    try:
        run(1.5,True);assert any(v>.1 for v in seen)
        run(.7,False);assert seen[-1]==0.
    finally:
        executor.shutdown();source.destroy_node();bridge.destroy_node();rclpy.try_shutdown()
