"""Synthetic readonly status node in isolated test domain; no driver nodes."""
from array import array
import json,time
import numpy as np
import rclpy
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry
from std_msgs.msg import String,Float32MultiArray,MultiArrayLayout,MultiArrayDimension
from rclpy.qos import qos_profile_sensor_data
from ht_scout_bridge.runtime_status import RuntimeStatus

def test_preview_diagnosis_without_gui_has_body_counts_and_no_motor_publisher():
    rclpy.init(args=['--ros-args','-p','run_mode:=preview','-p','mapping_verified:=true',
        '-p','command_topic:=/ht_real/preview/cmd_vel_stamped'])
    node=RuntimeStatus();source=rclpy.create_node('readonly_status_test_source')
    odom=source.create_publisher(Odometry,'/ht_real/odometry',qos_profile_sensor_data)
    maps=source.create_publisher(GridMap,'/ht_real/traversability',1)
    planner=source.create_publisher(String,'/ht_real/ht_execution_status',1)
    follower=source.create_publisher(String,'/ht_real/ht_follower_status',1)
    rows=[];source.create_subscription(String,'/ht_real/runtime_status',lambda m:rows.append(json.loads(m.data)),1)
    ex=rclpy.executors.SingleThreadedExecutor();ex.add_node(node);ex.add_node(source)
    try:
        end=time.monotonic()+1.7
        while time.monotonic()<end:
            o=Odometry();o.header.frame_id='map';o.header.stamp=source.get_clock().now().to_msg();o.pose.pose.orientation.w=1.;odom.publish(o)
            g=GridMap();g.header=o.header;g.info.resolution=.04;g.info.length_x=g.info.length_y=2.44;g.info.pose.orientation.w=1.
            g.layers=['ht_valid','ht_observation_valid','ht_obstacle','ht_elevation','ht_interpolated']
            for value in [1.,0.,0.,0.,0.]:
                a=Float32MultiArray();a.layout=MultiArrayLayout(dim=[MultiArrayDimension(label='column_index',size=61,stride=3721),MultiArrayDimension(label='row_index',size=61,stride=61)])
                a.data=array('f',np.full(3721,value,np.float32));g.data.append(a)
            maps.publish(g);planner.publish(String(data='HT_ASSISTED'));follower.publish(String(data='DRIVING'))
            ex.spin_once(timeout_sec=.01);time.sleep(.01)
        assert rows and rows[-1]['reason']=='PREVIEW_NO_MOTOR_OUTPUT'
        assert rows[-1]['body']['unknown']==rows[-1]['body']['cells']>0
        assert not rows[-1]['motor_output_enabled'] and not rows[-1]['wheel_motion_confirmed']
        assert node.count_publishers('/cmd_vel')==node.count_publishers('/ht_real/cmd_vel_stamped')==0
    finally:
        ex.shutdown();node.destroy_node();source.destroy_node();rclpy.try_shutdown()
