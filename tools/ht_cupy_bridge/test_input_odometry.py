from types import SimpleNamespace as S
from copy import deepcopy
import math
import pytest
from input_odometry import InputOdometry


def msg(t=10., x=0., z=1.):
    return S(header=S(frame_id='map',stamp=S(sec=int(t),nanosec=round((t-int(t))*1e9))),
             child_frame_id='base_link',pose=S(pose=S(position=S(x=x,y=0.,z=z),orientation=S(x=0.,y=0.,z=0.,w=1.))))


@pytest.mark.parametrize('field,value',[('frame','odom'),('child','wrong'),('q',0.),('q',2.),('x',float('nan')),('z',float('inf'))])
def test_invalid_input_never_enters_surface_history(field,value):
    b=InputOdometry('base_link');m=msg()
    if field=='frame':m.header.frame_id=value
    elif field=='child':m.child_frame_id=value
    elif field=='q':m.pose.pose.orientation.w=value
    else:setattr(m.pose.pose.position,field,value)
    assert not b.add(m,10.) and not b.samples


def test_old_and_duplicate_packets_are_dropped_without_rewinding():
    b=InputOdometry();assert b.add(msg(),10.)
    assert not b.add(msg(9.9,z=8.),10.1)
    assert not b.add(msg(z=9.),10.1)
    assert b.height_at(10.)==1. and b.height_at(10.2) is None
    assert b.fault is None


def test_jump_latches_fault_and_never_reuses_prejump_history():
    b=InputOdometry();assert b.add(msg(),10.)
    assert not b.add(msg(10.02,x=4),10.02)
    assert b.fault=='ODOM_JUMP_RESTART_REQUIRED' and b.height_at(10.) is None
    assert not b.add(msg(10.04),10.04)


def test_clock_rollback_is_distinct_from_an_out_of_order_packet():
    b=InputOdometry();assert b.add(msg(),10.)
    assert not b.check_clock(9.9)
    assert b.fault=='CLOCK_RESET_RESTART_REQUIRED'


def test_quaternion_sign_change_is_not_a_pose_jump():
    b=InputOdometry();assert b.add(msg(),10.)
    m=msg(10.02);m.pose.pose.orientation.w=-1.
    assert b.add(m,10.02) and not b.fault
