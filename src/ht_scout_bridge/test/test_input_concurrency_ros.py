"""Real ROS receive/worker concurrency and in-flight failure barriers."""
from pathlib import Path
import threading
import time

import pytest
import rclpy
from rclpy.executors import MultiThreadedExecutor
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from grid_map_msgs.msg import GridMap

from ht_scout_bridge import node as module
from test_node import FakeTf,Sink,odom,elevation
from test_geometry import cloud


@pytest.fixture
def running(monkeypatch):
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setattr(module,'get_package_share_directory',lambda _:str(root))
    rclpy.init(args=['--ros-args','-p','cloud_topic:=/offline_pipeline/cloud',
                    '-p','odometry_topic:=/offline_pipeline/odom',
                    '-p','elevation_topic:=/offline_pipeline/elevation'])
    active,release=threading.Event(),threading.Event()
    class Probe(module.ScoutInputs):
        def convert_cloud(self,msg):
            pair=super().convert_cloud(msg)
            active.set();assert release.wait(4),'test did not release the cloud worker'
            return pair
    n=Probe();n.buffer=FakeTf(n);clock=[10.05]
    n.get_clock=lambda:type('Clock',(),{'now':lambda _:Time(seconds=clock[0])})()
    for name in ['odom_pub','cloud_pub','filtered_cloud_pub','elevation_pub','status_pub','stop_pub']:
        setattr(n,name,Sink())
    source=rclpy.create_node('offline_pipeline_source')
    pubs={'cloud':source.create_publisher(PointCloud2,'/offline_pipeline/cloud',2),
          'odom':source.create_publisher(Odometry,'/offline_pipeline/odom',2),
          'elevation':source.create_publisher(GridMap,'/offline_pipeline/elevation',1)}
    executor=MultiThreadedExecutor(num_threads=3);executor.add_node(n);executor.add_node(source)
    thread=threading.Thread(target=executor.spin);thread.start()
    try:
        end=time.monotonic()+3
        while not all(p.get_subscription_count() for p in pubs.values()) and time.monotonic()<end:
            time.sleep(.01)
        assert all(p.get_subscription_count() for p in pubs.values())
        pubs['cloud'].publish(cloud());assert active.wait(2)
        yield n,pubs,release,clock
    finally:
        n.close_inputs();release.set();executor.shutdown()
        executor._executor.shutdown(wait=True);thread.join(timeout=2)
        source.destroy_node();n.destroy_node();rclpy.try_shutdown()


def until(condition,seconds=2):
    end=time.monotonic()+seconds
    while not condition() and time.monotonic()<end:time.sleep(.005)
    assert condition()


def test_cloud_work_does_not_block_elevation_odom_or_monotonic_ingestion(running):
    n,pubs,release,_=running
    pubs['odom'].publish(odom());pubs['elevation'].publish(elevation())
    until(lambda:len(n.odom_pub.messages)==len(n.elevation_pub.messages)==1)
    assert not n.cloud_pub.messages and not n.filtered_cloud_pub.messages
    # Duplicate active input and older messages cannot be reprocessed.
    pubs['cloud'].publish(cloud())
    older=cloud();older.header.stamp.sec=9;pubs['cloud'].publish(older)
    newer=cloud();newer.header.stamp.nanosec=20_000_000;pubs['cloud'].publish(newer)
    until(lambda:len(n.pending['cloud'])==1)
    release.set();until(lambda:len(n.cloud_pub.messages)==2)
    assert [m.header.stamp.nanosec for m in n.cloud_pub.messages]==[0,20_000_000]
    assert len(n.filtered_cloud_pub.messages)==2


@pytest.mark.parametrize('failure',['extrinsics','clock_reset','expired','closing'])
def test_inflight_cloud_pair_is_discarded_after_fault_expiry_or_shutdown(running,failure):
    n,pubs,release,clock=running
    if failure=='extrinsics':
        n.buffer.mismatch=True;pubs['odom'].publish(odom());until(lambda:n.fault is not None)
    elif failure=='clock_reset':
        clock[0]=9.;pubs['odom'].publish(odom());until(lambda:n.fault is not None)
    elif failure=='expired':clock[0]=11.2
    else:n.close_inputs()
    release.set();until(lambda:not n.processing_locks['cloud'].locked())
    assert not n.filtered_cloud_pub.messages and not n.cloud_pub.messages
    if failure in ('extrinsics','clock_reset'):assert n.stop_pub.messages[-1].data==1
