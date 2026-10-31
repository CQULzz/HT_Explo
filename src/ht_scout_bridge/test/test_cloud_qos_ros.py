"""Explicit input QoS is compatible with the actual publisher contract."""
from pathlib import Path
import time
import json
import pytest
import rclpy
from rclpy.qos import QoSProfile, ReliabilityPolicy
from rclpy.executors import SingleThreadedExecutor
from sensor_msgs.msg import PointCloud2
from ht_scout_bridge import node as module


@pytest.mark.parametrize('reliability',[ReliabilityPolicy.BEST_EFFORT,ReliabilityPolicy.RELIABLE])
@pytest.mark.parametrize('requested',['best_effort','reliable'])
def test_sensor_cloud_reaches_input_queue(monkeypatch,reliability,requested):
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(module,'get_package_share_directory',lambda _:str(root))
    rclpy.init(args=['--ros-args','-p','cloud_topic:=/offline_review/lidar_input',
                    '-p','cloud_reliability:='+requested])
    consumer=module.ScoutInputs();consumer.timer.cancel()
    received=[];consumer.enqueue=lambda kind,msg:received.append(kind)
    source=rclpy.create_node('offline_lidar_qos_probe')
    pub=source.create_publisher(PointCloud2,'/offline_review/lidar_input',QoSProfile(depth=2,reliability=reliability))
    executor=SingleThreadedExecutor();executor.add_node(consumer);executor.add_node(source)
    try:
        deadline=time.monotonic()+1.5
        while time.monotonic()<deadline and not received:
            pub.publish(PointCloud2());executor.spin_once(timeout_sec=.01)
        compatible=requested=='best_effort' or reliability==ReliabilityPolicy.RELIABLE
        assert bool(received)==compatible
        from test_node import Sink
        consumer.performance_pub=Sink();consumer.publish_input_performance()
        record=json.loads(consumer.performance_pub.messages[-1].data)
        assert record['cloud_reliability']==requested
        assert record['cloud_qos_compatible']==compatible
    finally:
        executor.shutdown();source.destroy_node();consumer.destroy_node();rclpy.try_shutdown()
