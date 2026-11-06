import math
from pathlib import Path
import runpy
import numpy as np
import pytest
import rclpy
from tare_sim_command import TareSimBridge, bounded, intersects


def test_motion_envelope_and_explicit_stop():
    p=(0.,0.)
    for _ in range(100):p=bounded(9.,9.,p,.02)
    assert p==(.4,.8)
    for _ in range(100):p=bounded(-9.,-9.,p,.02)
    assert p==(-.25,-.8)
    assert bounded(0.,0.,(.4,.8),.02)==(0.,0.)
    assert bounded(float('nan'),0.,p,.02)==(0.,0.)
    assert bounded(.4,.8,(0.,0.),1.)==pytest.approx((.05,.12))


def test_same_geometry_margin_includes_current_pose_and_future_sweep():
    radius=.7+math.sqrt(2)*.1
    assert intersects(np.array([[radius-1e-4,0.,0.]]),(0.,0.,0.,0.),0.,0.)
    assert not intersects(np.array([[radius+1e-4,0.,0.]]),(0.,0.,0.,0.),0.,0.)
    assert intersects(np.array([[radius+.1,0.,0.]]),(0.,0.,0.,0.),.4,0.)
    assert not intersects(np.array([[.1,0.,.501]]),(0.,0.,0.,0.),.4,0.)
    assert not intersects(np.empty((0,3)),(0.,0.,0.,0.),.4,.8)


def test_bridge_refuses_actual_chassis_output():
    rclpy.init()
    try:
        with pytest.raises(ValueError,match='isolated simulation'):
            TareSimBridge()
    finally:rclpy.shutdown()


def test_tare_launch_resolves_all_cmu_packages_without_starting_nodes():
    # Build real launch actions and their actual parameters. No launch service,
    # model or process starts, and the HT hardware entry is unchanged.
    from launch import LaunchContext
    ctx=LaunchContext()
    repo=Path(__file__).resolve().parents[2]
    ctx.launch_configurations.update(seed='42',calibration_file=str(
        repo/'src/ht_scout_bridge/config/scout_extrinsics.yaml'))
    module=runpy.run_path(str(Path(__file__).with_name('tare_geometric.launch.py')))
    nodes=module['start'](ctx)
    assert len(nodes)==7


def test_actual_ros_bridge_moves_only_with_fresh_geometry_and_stops_on_stale_command():
    import time
    from rclpy.node import Node
    from rclpy.executors import SingleThreadedExecutor
    from geometry_msgs.msg import Twist, TwistStamped, PoseStamped
    from nav_msgs.msg import Odometry, Path as RosPath
    from std_msgs.msg import String, Header
    from sensor_msgs.msg import PointCloud2
    from sensor_msgs_py.point_cloud2 import create_cloud_xyz32
    rclpy.init(args=['--ros-args','-p','input_topic:=/sim/tare/raw_command',
                     '-p','output_topic:=/sim/cmd_vel'])
    bridge=TareSimBridge();source=Node('tare_bridge_fixture',use_global_arguments=False)
    executor=SingleThreadedExecutor();executor.add_node(bridge);executor.add_node(source)
    raw=source.create_publisher(TwistStamped,'/sim/tare/raw_command',1)
    odom=source.create_publisher(Odometry,'/ht_real/odometry',5)
    path=source.create_publisher(RosPath,'/sim/tare/path',5)
    geo=source.create_publisher(PointCloud2,'/ht_real/collision_cloud',1)
    mission=source.create_publisher(String,'/ht_real/mission_state',5)
    commands=[]
    sub=source.create_subscription(Twist,'/sim/cmd_vel',lambda m:commands.append(m.linear.x),10)
    def spin(duration,send_geometry=True,send_command=True,geometry_age=0.):
        until=time.monotonic()+duration
        while time.monotonic()<until:
            stamp=source.get_clock().now().to_msg()
            o=Odometry();o.header=Header(stamp=stamp,frame_id='map')
            o.child_frame_id='base_link';o.pose.pose.orientation.w=1.;odom.publish(o)
            p=RosPath();p.header=Header(stamp=stamp,frame_id='vehicle');p.poses=[PoseStamped()];path.publish(p)
            mission.publish(String(data='EXPLORING'))
            if send_geometry:
                from rclpy.time import Time
                old_stamp=Time(nanoseconds=source.get_clock().now().nanoseconds-int(geometry_age*1e9)).to_msg()
                geo.publish(create_cloud_xyz32(Header(stamp=old_stamp,frame_id='map'),[]))
            if send_command:
                c=TwistStamped();c.header=Header(stamp=stamp,frame_id='vehicle');c.twist.linear.x=.4;raw.publish(c)
            executor.spin_once(timeout_sec=.01)
    try:
        spin(.4,send_geometry=False)
        assert commands and all(v==0 for v in commands)
        commands.clear();spin(.6,geometry_age=1.2)
        assert any(v>0 for v in commands) and all(0<=v<=.4 for v in commands)
        commands.clear();spin(.35,geometry_age=3.2)
        assert commands and all(v==0 for v in commands[-3:])
        commands.clear();spin(.4,geometry_age=1.2)
        assert any(v>0 for v in commands)
        commands.clear();spin(.6,send_command=False)
        assert commands and all(v==0 for v in commands[-3:])
    finally:
        executor.shutdown();source.destroy_node();bridge.destroy_node();rclpy.shutdown()
