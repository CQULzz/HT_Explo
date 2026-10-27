"""Real DDS regression probes; all motor-like outputs use isolated test topics."""
import time
import rclpy
from builtin_interfaces.msg import Time
from geometry_msgs.msg import Twist, TwistStamped
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import Bool
from ht_scout_bridge.command_bridge import ScoutCommandBridge


def probe(*, pause=False, remap=False):
    output='/offline_review/chassis_command'
    actual='/offline_review/remapped_command' if remap else output
    args=['--ros-args','-p','use_sim_time:=true',
          '-p','input_topic:=/offline_review/command','-p','output_topic:='+output]
    if remap:args+=['-r',output+':='+actual]
    rclpy.init(args=args)
    bridge=ScoutCommandBridge();source=rclpy.create_node('offline_clock_probe')
    executor=SingleThreadedExecutor();executor.add_node(bridge);executor.add_node(source)
    clock=source.create_publisher(Clock,'/clock',10)
    command=source.create_publisher(TwistStamped,'/offline_review/command',1)
    permission=source.create_publisher(Bool,'/ht_real/ht_navigation_allowed',1)
    odometry=source.create_publisher(Odometry,'/ht_real/odometry',1)
    seen=[]
    sub=source.create_subscription(Twist,actual,lambda m:seen.append((time.monotonic(),m.linear.x)),10)
    def spin_for(duration):
        deadline=time.monotonic()+duration
        while time.monotonic()<deadline:executor.spin_once(timeout_sec=.001)
    try:
        for step in range(90):
            stamp=Time(sec=100+step//50,nanosec=(step%50)*20_000_000)
            clock.publish(Clock(clock=stamp));spin_for(.008)
            # Use the clock already delivered to the consumer. A future
            # command while /clock is still in flight is correctly rejected.
            delivered=bridge.get_clock().now().to_msg()
            msg=TwistStamped();msg.header.stamp=delivered;msg.header.frame_id='base_link';msg.twist.linear.x=.2
            odom=Odometry();odom.header.stamp=delivered;odom.header.frame_id='map';odom.child_frame_id='base_link';odom.pose.pose.orientation.w=1.
            command.publish(msg);odometry.publish(odom);permission.publish(Bool(data=True));spin_for(.012)
        moving=any(v>.1 for _,v in seen)
        before=len(seen)
        if pause:spin_for(.8)
        return {'forwarded':moving,'last_command':seen[-1][1] if seen else None,
                'outputs_after_pause':len(seen)-before,'reason':bridge.reason(),
                'publisher_topic':bridge.pub.topic_name,'configured_topic':output,
                'configured_publisher_count':len(bridge.get_publishers_info_by_topic(output)),
                'actual_publisher_count':len(bridge.get_publishers_info_by_topic(actual))}
    finally:
        executor.shutdown();source.destroy_node();bridge.destroy_node();rclpy.try_shutdown()


def test_watchdog_stops_with_frozen_ros_clock():
    result=probe(pause=True)
    assert result['forwarded'],result
    assert result['outputs_after_pause']>0 and result['last_command']==0.,result


def test_topic_remapping_preserves_command_ownership_checks():
    result=probe(remap=True)
    assert result['forwarded'],result
