"""Actual ROS callbacks keep receiving during a deliberately blocked inference."""
import threading,time
import rclpy
from rclpy.executors import MultiThreadedExecutor
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry
from cupy_to_ht import CupyToHt

def test_receivers_remain_responsive_and_only_latest_pending_is_processed():
    rclpy.init();active=threading.Event();release=threading.Event();processed=[]
    class Probe(CupyToHt):
        def on_map(self,m):
            processed.append(m.header.stamp.sec)
            if len(processed)==1:active.set();release.wait(timeout=4)
    n=Probe();source=rclpy.create_node('offline_latest_input_probe')
    pub=source.create_publisher(GridMap,'/elevation_mapping/elevation_map_raw',1)
    odom=source.create_publisher(Odometry,'/state_estimation',1)
    executor=MultiThreadedExecutor(num_threads=2);executor.add_node(n);executor.add_node(source)
    thread=threading.Thread(target=executor.spin);thread.start()
    try:
        end=time.monotonic()+3
        while not active.is_set() and time.monotonic()<end:
            m=GridMap();m.header.stamp.sec=1;pub.publish(m);time.sleep(.03)
        assert active.is_set()
        for i in range(2,12):
            m=GridMap();m.header.stamp.sec=i;pub.publish(m)
            o=Odometry();o.header.frame_id='map';o.child_frame_id='base_link';o.header.stamp=source.get_clock().now().to_msg();o.pose.pose.orientation.w=1.;odom.publish(o);time.sleep(.03)
        end=time.monotonic()+1
        while n.pending_maps.replaced<5 and time.monotonic()<end:time.sleep(.01)
        assert n.pending_maps.replaced>=5
        with n.odometry_lock:assert len(n.input_odometry.samples)>0
        release.set();end=time.monotonic()+2
        while len(processed)<2 and time.monotonic()<end:time.sleep(.01)
        assert processed[:2]==[1,11]
    finally:
        release.set();executor.shutdown();executor._executor.shutdown(wait=True);thread.join(timeout=2)
        n.destroy_node();source.destroy_node();rclpy.try_shutdown()
