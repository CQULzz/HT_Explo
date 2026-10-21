"""Malformed input must be rejected before history/state/model publication."""
from array import array
from copy import deepcopy
import importlib.util
import os
from pathlib import Path

import numpy as np
import pytest
import rclpy
from grid_map_msgs.msg import GridMap
from std_msgs.msg import Float32MultiArray, MultiArrayDimension, MultiArrayLayout
import cupy_to_ht


def source_map():
    m = GridMap(); m.header.frame_id = 'map'; m.header.stamp.sec = 10
    m.info.resolution = .04093567251461988
    m.info.length_x = m.info.length_y = 291*m.info.resolution
    m.info.pose.orientation.w = 1.
    m.layers = ['elevation', 'variance', 'observation_age']
    for value in (0., .001, 0.):
        a = Float32MultiArray()
        a.layout = MultiArrayLayout(dim=[
            MultiArrayDimension(label='column_index', size=291, stride=291*291),
            MultiArrayDimension(label='row_index', size=291, stride=291)])
        a.data = array('f', np.full(291*291, value, np.float32).tobytes())
        m.data.append(a)
    return m


def invalidate(m, case):
    if case == 'short_variance': m.data[1].data = array('f', [0.])
    elif case == 'short_age': m.data[2].data = array('f', [0.])
    elif case == 'missing_data': m.data.pop()
    elif case == 'nan_length': m.info.length_x = float('nan')
    elif case == 'fractional_cells': m.info.length_x += .1*m.info.resolution
    elif case == 'nan_center': m.info.pose.position.x = float('nan')
    elif case == 'rotation': m.info.pose.orientation.z = m.info.pose.orientation.w = 2**-.5
    elif case == 'buffer_index': m.outer_start_index = 291
    elif case == 'duplicate_layer': m.layers[1] = 'elevation'
    elif case == 'offset': m.data[0].layout.data_offset = 1
    elif case == 'row_major': m.data[0].layout.dim[0].label = 'row_index'
    elif case == 'stride': m.data[0].layout.dim[1].stride = 1
    elif case == 'zero_resolution': m.info.resolution = 0.
    elif case == 'coarse_resolution': m.info.resolution = .1
    elif case == 'rectangular_input': m.info.length_y = 341*m.info.resolution
    elif case == 'small_input': m.info.length_x = m.info.length_y = 51*m.info.resolution
    else: raise AssertionError(case)


CASES = ['short_variance','short_age','missing_data','nan_length','fractional_cells',
         'nan_center','rotation','buffer_index','duplicate_layer','offset','row_major',
         'stride','zero_resolution','coarse_resolution','rectangular_input','small_input']


@pytest.fixture
def node():
    module = cupy_to_ht
    if os.environ.get('HT_BRIDGE_UNDER_TEST'):
        spec = importlib.util.spec_from_file_location('bridge_before', os.environ['HT_BRIDGE_UNDER_TEST'])
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        module.__file__ = cupy_to_ht.__file__
    rclpy.init(); n = module.CupyToHt()
    try: yield n
    finally: n.destroy_node(); rclpy.try_shutdown()


@pytest.mark.parametrize('case', CASES)
def test_invalid_input_is_rejected_without_state_change(node, case):
    m = source_map(); invalidate(m, case)
    node.on_map(m)
    assert node.last_source_stamp is None
    assert node.history is None
    assert node.count == 0


def test_all_three_buffers_decode_at_the_same_world_cells():
    m = source_map(); m.outer_start_index = 7; m.inner_start_index = 290
    logical = np.arange(291*291, dtype=np.float32).reshape(291,291)
    for i, a in enumerate(m.data):
        physical = np.roll(logical+i, (7,290), (0,1))
        a.data = array('f', physical.flatten(order='F').tobytes())
    resolution, *decoded = cupy_to_ht.decode_elevation_source(m)
    for i, a in enumerate(decoded): np.testing.assert_array_equal(a, logical+i)
    assert resolution == m.info.resolution


def test_valid_model_and_map_are_unchanged_from_before(node):
    before = Path(__file__).resolve().parents[2]/'validation/logic_resolution_2026-10-22/cupy_to_ht_before.py'
    spec = importlib.util.spec_from_file_location('valid_bridge_before', before)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    module.__file__ = cupy_to_ht.__file__
    old = module.CupyToHt()
    def capture(n):
        messages=[]; n.pub=type('Publisher', (), {'publish': lambda _, m: messages.append(m)})()
        m=source_map(); m.header.stamp=n.get_clock().now().to_msg()
        n.on_map(m)
        assert len(messages)==1
        return messages[0]
    try:
        a, b = capture(old), capture(node)
        assert a.info == b.info and a.layers == b.layers
        for x,y in zip(a.data,b.data):
            assert x.layout == y.layout
            np.testing.assert_array_equal(np.array(x.data),np.array(y.data))
    finally: old.destroy_node()


def test_older_map_does_not_rewind_fused_history(node):
    m=source_map();node.on_map(m)
    count=node.count;history=node.history
    m.header.stamp.sec=9;node.on_map(m)
    assert node.count==count and node.history is history and node.last_source_stamp==(10,0)


def test_discontinuous_odometry_prevents_reusing_previous_history(node):
    from nav_msgs.msg import Odometry
    m=source_map();node.on_map(m);count=node.count
    a=Odometry();a.header.frame_id='map';a.header.stamp=node.get_clock().now().to_msg();a.pose.pose.orientation.w=1.
    node.on_odometry(a)
    b=deepcopy(a)
    t=a.header.stamp.sec*10**9+a.header.stamp.nanosec+10**6
    b.header.stamp.sec=t//10**9;b.header.stamp.nanosec=t%10**9;b.pose.pose.position.x=5.
    node.on_odometry(b)
    assert node.input_odometry.fault=='ODOM_JUMP_RESTART_REQUIRED'
    m.header.stamp.sec=11;node.on_map(m)
    assert node.count==count and node.robot_z_at(a.header.stamp.sec+a.header.stamp.nanosec*1e-9) is None
