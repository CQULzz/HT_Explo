import importlib.util
from pathlib import Path
from types import SimpleNamespace as S
import pytest
spec=importlib.util.spec_from_file_location('sim_adapter',Path(__file__).with_name('sim_adapter.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
def message(ns):return S(header=S(stamp=S(sec=ns//10**9,nanosec=ns%10**9),frame_id='rslidar'),data=b'unchanged lidar bytes')
@pytest.mark.parametrize('pose,clock,ready',[(200,199,False),(199,200,False),(200,200,True),(201,201,True),(-1,200,False)])
def test_scan_waits_for_both_pose_and_source_clock(pose,clock,ready):
 m=message(200);item=(1234.,m);a,b=module.source_ready([item],pose,clock)
 assert (a,b)==([item],[]) if ready else (a,b)==([],[item])
 assert m.header.stamp.nanosec==200 and m.data==b'unchanged lidar bytes'
def test_no_extra_wall_wait_and_original_message_identity():
 m=message(1793850000000000001);item=(999999999999.,m)
 a,b=module.source_ready([item],1793850000000000001,1793850000000000001)
 assert a[0] is item and a[0][1] is m and not b
def test_future_scan_becomes_ready_without_reordering_other_sources():
 a,b,c=[(0.,message(ns)) for ns in [200,400,300]]
 ready,pending=module.source_ready([a,b,c],300,300);assert ready==[a,c] and pending==[b]
 ready,pending=module.source_ready(pending,400,400);assert ready==[b] and not pending
