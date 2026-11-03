"""Exercise evidence publication using the actual history/context/model pipeline."""
from types import SimpleNamespace
import numpy as np
import rclpy
from rclpy.time import Time
from cupy_to_ht import CupyToHt
from test_source_contract import source_map


def test_evidence_diagnostics_follow_main_publication_and_retain_original_geometry():
    rclpy.init(args=['--ros-args','-p','ht_qualify_evidence:=true','-p','ht_device:=cpu'])
    node=CupyToHt();events=[];maps=[];evidence=[];history=[]
    node.get_clock=lambda:SimpleNamespace(now=lambda:Time(seconds=12))
    def capture(label,rows):
        def publish(m):events.append(label);rows.append(m)
        return SimpleNamespace(get_subscription_count=lambda:1,publish=publish)
    node.pub=capture('ht',maps);node.evidence_pub=capture('evidence',evidence);node.history_pub=capture('history',history)
    try:
        source=source_map();node.on_map(source)
        assert events==['ht','evidence','history']
        assert maps[0].header==evidence[0].header==history[0].header==source.header
        assert evidence[0].info==maps[0].info
        assert 'last_accepted_age_s' in evidence[0].layers
        for d in evidence[0].data:
            assert d.layout==maps[0].data[0].layout and len(d.data)==241*241
        def layer(name):return np.asarray(evidence[0].data[evidence[0].layers.index(name)].data)
        assert np.isfinite(layer('last_accepted_age_s')).all()
        assert not np.any(layer('evidence_flags'))
        # Resending a source does not refresh evidence or HT stamps.
        node.on_map(source);assert events==['ht','evidence','history']
    finally:node.destroy_node();rclpy.try_shutdown()
