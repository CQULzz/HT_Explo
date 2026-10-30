from types import SimpleNamespace as S
from latest_input import LatestInput


def test_queue_timestamp_is_latest_acceptance_and_counts_are_conserved():
    clock=[10.]
    q=LatestInput(clock=lambda:clock[0])
    a=msg(1);b=msg(2)
    assert q.put(a);clock[0]=11.;assert q.put(b)
    clock[0]=12.;assert not q.put(msg(1))
    source,received=q.take_with_metadata()
    assert source is b and received==11.
    assert q.take_with_metadata() is None
    status=q.status()
    assert status['received']==3 and status['accepted']==2 and status['replaced']==1
    assert status['taken']==1 and status['out_of_order']==1 and not status['pending']

def msg(sec):return S(header=S(stamp=S(sec=sec,nanosec=0)))

def test_latest_pending_replaces_without_touching_active_observation():
    q=LatestInput();first=msg(1);assert q.put(first);active=q.take()
    for i in range(2,102):assert q.put(msg(i))
    assert active is first and q.take().header.stamp.sec==101 and q.take() is None
    assert q.replaced==99

def test_late_or_duplicate_observations_cannot_rewind_after_take():
    q=LatestInput();assert q.put(msg(3));q.take()
    assert not q.put(msg(2)) and not q.put(msg(3)) and q.take() is None
    assert q.out_of_order==2
