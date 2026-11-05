import threading,time
from types import SimpleNamespace as S
from latest_input import LatestInput
from map_worker import MapWorker

def msg(n):return S(header=S(stamp=S(sec=n,nanosec=0)))
def wait(predicate):
    end=time.monotonic()+2
    while not predicate() and time.monotonic()<end:time.sleep(.002)
    assert predicate()

def test_blocked_inference_keeps_only_latest_monotonic_input():
    entered=threading.Event();release=threading.Event();processed=[];pending=LatestInput()
    def callback(m,**kw):
        processed.append(m.header.stamp.sec)
        if len(processed)==1:entered.set();release.wait(3)
    worker=MapWorker(pending,callback)
    try:
        worker.submit(msg(1));assert entered.wait(2)
        for i in range(2,12):assert worker.submit(msg(i))
        assert not worker.submit(msg(5));assert pending.replaced==9
        release.set();wait(lambda:len(processed)==2);assert processed==[1,11]
    finally:release.set();worker.close()

def test_shutdown_joins_active_callback_and_discards_pending():
    entered=threading.Event();release=threading.Event();processed=[];pending=LatestInput()
    def callback(m,**kw):entered.set();release.wait(3);processed.append(m.header.stamp.sec)
    worker=MapWorker(pending,callback);closer=None
    try:
        worker.submit(msg(1));assert entered.wait(2);worker.submit(msg(2))
        closer=threading.Thread(target=worker.close);closer.start()
        wait(lambda:pending.dropped_on_shutdown==1)
        assert closer.is_alive() and not worker.submit(msg(3))
        release.set();closer.join(2);assert not closer.is_alive();assert processed==[1]
    finally:
        release.set();worker.close()
        if closer:closer.join(2)

def test_failure_is_observable_and_not_silently_retried():
    def callback(m,**kw):raise ValueError('controlled failure')
    worker=MapWorker(LatestInput(),callback)
    try:
        worker.submit(msg(1));wait(lambda:worker.failure is not None)
        assert isinstance(worker.failure,ValueError);worker.thread.join(2);assert not worker.thread.is_alive()
    finally:worker.close()

def test_original_receive_time_is_forwarded_and_idle_close_is_idempotent():
    seen=[];worker=MapWorker(LatestInput(clock=lambda:10.25),lambda m,**kw:seen.append((m,kw)))
    original=msg(1)
    try:
        worker.submit(original);wait(lambda:bool(seen));assert seen==[(original,{'received_monotonic':10.25})]
    finally:worker.close();worker.close()
    assert not worker.thread.is_alive()
