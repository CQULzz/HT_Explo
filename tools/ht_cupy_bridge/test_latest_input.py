from types import SimpleNamespace as S
from latest_input import LatestInput

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
