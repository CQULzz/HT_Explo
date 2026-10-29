"""Live timing identifies source cadence without republishing old HT maps."""
import json
from types import SimpleNamespace

import rclpy
from rclpy.time import Time

from cupy_to_ht import CupyToHt
from test_source_contract import source_map


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
