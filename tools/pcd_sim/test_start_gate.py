import pytest
from start_gate import StartGate


def update(gate,sim,wall):
    for name in gate.required:gate.observe(name,sim,wall)


def test_start_requires_boundary_fresh_inputs_and_stable_readiness():
    gate=StartGate(('odometry','registered_scan','terrain'))
    assert gate.evaluate(1,1,True)['reason']=='INPUT_MISSING'
    update(gate,2,2)
    assert gate.evaluate(2,2,False)['reason']=='BOUNDARY_WAIT'
    assert not gate.evaluate(2,2,True)['release']
    update(gate,2.5,2.5)
    assert not gate.evaluate(2.5,2.5,True)['release']
    assert gate.evaluate(4,4,True)['reason']=='INPUT_STALE'
    update(gate,4,4)
    assert not gate.evaluate(4,4,True)['release']
    update(gate,5,5)
    assert gate.evaluate(5,5,True)['release']
    update(gate,6,6)
    assert not gate.evaluate(6,6,True)['release']


def test_future_sources_and_paused_clock_cannot_release():
    gate=StartGate(('terrain',))
    gate.observe('terrain',4,2)
    assert gate.evaluate(2,2,True)['reason']=='INPUT_STALE'
    update(gate,3,3)
    assert not gate.evaluate(3,3,True)['release']
    assert gate.evaluate(3,5,True)['reason']=='INPUT_STALE'


def test_clock_reset_latches_and_never_renews_a_mission_epoch():
    gate=StartGate(('terrain',),hold_s=0)
    update(gate,4,4)
    assert gate.evaluate(4,4,True)['release']
    update(gate,1,5)
    assert gate.evaluate(1,5,True)['reason']=='CLOCK_INVALID'
    update(gate,6,6)
    assert not gate.evaluate(6,6,True)['release']
    assert gate.clock_fault
