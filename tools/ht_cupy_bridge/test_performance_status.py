"""Live timing identifies source cadence without republishing old HT maps."""
import json
import time
from types import SimpleNamespace

import rclpy
from rclpy.time import Time
from rclpy.qos import QoSProfile,ReliabilityPolicy,DurabilityPolicy
from std_msgs.msg import String

from cupy_to_ht import CupyToHt
from test_source_contract import source_map
import numpy as np
from latest_input import LatestInput


def test_performance_uses_unique_source_stamps_and_reports_processing_separately():
    rclpy.init(args=['--ros-args', '-p', 'ht_device:=cpu', '-p', 'ht_fuse_bn:=false',
                    '-p', 'ht_history_backend:=numpy'])
    node = CupyToHt()
    timings, maps = [], []
    node.performance_pub = SimpleNamespace(publish=lambda msg: timings.append(json.loads(msg.data)))
    node.pub = SimpleNamespace(publish=maps.append)
    node.history_pub = SimpleNamespace(get_subscription_count=lambda: 0)
    node.get_clock = lambda: SimpleNamespace(now=lambda: Time(seconds=12))
    try:
        source = source_map()
        node.on_map(source)
        assert len(maps) == len(timings) == 1
        first = timings[0]
        assert first['source_interval_s'] is first['publish_interval_s'] is None
        assert first['source_age_at_publish_s'] == 2.
        assert first['callback_service_s'] >= first['network_inference_s'] > 0.
        assert first['history_backend'] == 'numpy' and first['fused_batchnorm'] is False
        assert first['runtime_id']==node.runtime_manifest['runtime_id']
        assert node.cpu_fuse_bn is False
        node.on_map(source)
        assert len(maps) == len(timings) == 1
        source.header.stamp.sec = 11
        node.last_performance_monotonic = None
        node.on_map(source)
        assert len(maps) == len(timings) == 2
        assert timings[-1]['source_interval_s'] == 1.
        assert timings[-1]['source_age_at_publish_s'] == 1.
        assert timings[-1]['publish_interval_s'] > 0.
        assert maps[-1].header.stamp.sec == 11
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def test_runtime_identity_is_available_to_late_subscriber_and_reports_real_imports():
    rclpy.init(args=['--ros-args','-p','ht_device:=cpu','-p','ht_history_backend:=numpy'])
    node=CupyToHt();rows=[]
    subscription=node.create_subscription(String,'/ht_runtime',lambda msg:rows.append(json.loads(msg.data)),
        QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL))
    try:
        deadline=time.monotonic()+3
        while not rows and time.monotonic()<deadline:rclpy.spin_once(node,timeout_sec=.05)
        assert len(rows)==1
        m=rows[0]
        assert m['actual']['device']=='cpu' and m['actual']['history_backend']=='numpy'
        assert m['modules']['model']['sha256'] and m['weights']['sha256']
        assert m['topics']['ht']==node.pub.topic_name and m['runtime_id']==node.runtime_manifest['runtime_id']
    finally:
        node.destroy_subscription(subscription);node.destroy_node();rclpy.try_shutdown()


def test_queue_stage_and_reason_diagnostics_preserve_main_map_contract():
    rclpy.init(args=['--ros-args','-p','ht_device:=cpu','-p','ht_reason_interval_s:=0.0'])
    node=CupyToHt();maps=[];reasons=[];timings=[]
    node.pub=SimpleNamespace(publish=maps.append)
    node.reason_pub=SimpleNamespace(get_subscription_count=lambda:1,publish=reasons.append)
    node.history_pub=SimpleNamespace(get_subscription_count=lambda:0)
    node.performance_pub=SimpleNamespace(publish=lambda m:timings.append(json.loads(m.data)))
    node.pending_maps=LatestInput(clock=lambda:time.monotonic()-.05)
    node.get_clock=lambda:SimpleNamespace(now=lambda:Time(seconds=12))
    try:
        node.enqueue_map(source_map());node.process_pending()
        assert len(maps)==len(reasons)==len(timings)==1
        row=timings[0]
        assert row['queue_wait_s']>=.05 and row['input_queue']['taken']==1
        assert row['source_age_at_publish_s']==2. # Queue wait is not added to source age.
        assert all(v>=0 for v in row['stages'].values())
        assert row['runtime_profile']['rss_peak_kib']>0
        assert row['history_resources']['surface_array_bytes']>0
        assert row['reason_summary']['counts_overlap']
        assert maps[0].header==reasons[0].header and maps[0].info==reasons[0].info
        assert reasons[0].layers==['reason_flags','raw_model_low_direction_bits','raw_model_min_probability']
        assert len(maps[0].layers)==12 # Diagnostic layers are separate.
        probability=np.stack([np.asarray(d.data) for d in maps[0].data[:8]])
        np.testing.assert_array_equal(np.min(probability,axis=0),np.asarray(reasons[0].data[2].data))
    finally:node.destroy_node();rclpy.try_shutdown()


def test_shutdown_rejects_pending_and_new_maps_without_starting_history():
    rclpy.init(args=['--ros-args','-p','ht_device:=cpu'])
    node=CupyToHt();maps=[];node.pub=SimpleNamespace(publish=maps.append)
    try:
        node.enqueue_map(source_map());node.begin_shutdown()
        node.process_pending();node.on_map(source_map());node.enqueue_map(source_map())
        assert not maps and node.history is None
        assert node.pending_maps.status()['dropped_on_shutdown']==1
    finally:node.destroy_node();rclpy.try_shutdown()
