"""Real boundary and readiness DDS transport, without a physics simulator."""
import json
import time

import pytest
import rclpy
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from geometry_msgs.msg import PolygonStamped
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import Bool, Float32MultiArray, String

from scene_config import SceneConfig
from sim_adapter import Adapter


def test_actual_adapter_sends_scene_boundary_before_releasing_start(tmp_path,monkeypatch):
    config=SceneConfig(bounds_xy_m=(-30,30,-30,30))
    config.write(tmp_path/'scene_config.json')
    monkeypatch.setenv('HT_SIM_RUNTIME',str(tmp_path))
    monkeypatch.setenv('HT_SIM_OUTPUT',str(tmp_path))
    monkeypatch.setenv('HT_SIM_START_POLICY','ready')
    monkeypatch.setenv('HT_SIM_NAVIGATION','ht')
    monkeypatch.delenv('HT_SIM_SCENE_CONFIG',raising=False)
    rclpy.init()
    adapter=Adapter()
    for timer in adapter.timers:timer.cancel()
    source=Node('sim_readiness_fixture')
    executor=SingleThreadedExecutor()
    executor.add_node(adapter)
    executor.add_node(source)
    boundaries=[]
    starts=[]
    acknowledgement=source.create_publisher(String,'/ht_real/tare_boundary_status',10)
    applied={'navigation_source_s':-1.,'coverage_source_s':-1.}
    def apply(message,key):
        boundaries.append(message)
        applied[key]=message.header.stamp.sec+message.header.stamp.nanosec/1e9
        acknowledgement.publish(String(data=json.dumps(applied)))
    subscriptions=[source.create_subscription(PolygonStamped,topic,
        lambda m,key=key:apply(m,key),10) for topic,key in
        [('/ht_real/navigation_boundary','navigation_source_s'),
         ('/ht_real/coverage_boundary','coverage_source_s')]]
    subscriptions.append(source.create_subscription(Bool,'/ht_real/exploration_start',
        lambda m:starts.append(m.data),10))
    clock=source.create_publisher(Clock,'/clock',10)
    odom=source.create_publisher(Odometry,'/ht_real/odometry',10)
    scan=source.create_publisher(PointCloud2,'/ht_real/registered_scan',10)
    terrain=source.create_publisher(GridMap,'/ht_real/traversability',10)
    def service(seconds):
        until=time.monotonic()+seconds
        while time.monotonic()<until:executor.spin_once(timeout_sec=.01)
    def feed(second,send_map):
        for _ in range(4):
            c=Clock();c.clock.sec=second;clock.publish(c)
            o=Odometry();o.header.frame_id='map';o.child_frame_id='base_link'
            o.header.stamp=c.clock;odom.publish(o)
            s=PointCloud2();s.header=o.header;s.width=s.height=1;scan.publish(s)
            if send_map:
                m=GridMap();m.header=o.header;m.layers=['ht_valid']
                m.data=[Float32MultiArray(data=[1.])];terrain.publish(m)
            service(.03)
        adapter.start_tick();service(.1)
    try:
        service(.3)
        feed(1,False)
        feed(2,False)
        assert boundaries and not starts
        assert [(p.x,p.y) for p in boundaries[-1].polygon.points] == list(config.navigation_polygon)
        feed(3,True)
        assert not starts
        feed(4,True)
        assert starts and all(starts)
        record=json.loads((tmp_path/'START_GATE.json').read_text())
        assert record['release'] and set(record['sources']) == {'odometry','registered_scan','terrain'}
        feed(5,True)
        assert json.loads((tmp_path/'START_GATE.json').read_text()) == record
    finally:
        executor.shutdown();adapter.destroy_node();source.destroy_node();rclpy.shutdown()
