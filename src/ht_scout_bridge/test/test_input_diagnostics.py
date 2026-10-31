"""Reception counts distinguish missing DDS delivery from accepted work."""
import json

from test_node import node,cloud


def test_counts_expose_duplicate_tf_wait_success_and_bounded_timings(node):
    from test_node import Sink
    node.performance_pub=Sink()
    node.buffer.missing=True
    node.enqueue('cloud',cloud());node.drain_cloud()
    node.enqueue('cloud',cloud())
    node.buffer.missing=False;node.drain_cloud()
    node.publish_input_performance()
    record=json.loads(node.performance_pub.messages[-1].data)
    counts=record['counts']['cloud']
    assert counts['received']==2 and counts['queued']==1
    assert counts['duplicate_or_old']==1 and counts['tf_wait_attempts']==1
    assert counts['processed']==counts['published']==1
    assert record['cloud_reliability']=='reliable'
    assert record['pending']['cloud']==0
    assert len(node.input_times['cloud']['conversion_s'])==1
    assert node.input_times['cloud']['conversion_s'].maxlen==200
    assert record['identity']['node_sha256'] and record['receive_silence_s']['cloud']>=0


def test_counters_do_not_report_expired_cloud_as_published(node):
    old=cloud();old.header.stamp.sec=8
    node.enqueue('cloud',old);node.drain_cloud()
    assert node.input_counts['cloud']['source_time_invalid']==1
    assert node.input_counts['cloud']['published']==0
