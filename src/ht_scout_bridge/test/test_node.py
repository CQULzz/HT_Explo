from pathlib import Path
from copy import deepcopy
from array import array
from types import SimpleNamespace as S
import numpy as np
import pytest
import rclpy
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from grid_map_msgs.msg import GridMap
from std_msgs.msg import Float32MultiArray,MultiArrayLayout,MultiArrayDimension
from tf2_ros import LookupException
from ht_scout_bridge import node as module
from test_geometry import cloud

ROOT=Path(__file__).resolve().parents[1]


class Sink:
    def __init__(self):self.messages=[]
    def get_subscription_count(self):return 1
    def publish(self,m):self.messages.append(deepcopy(m))


class FakeTf:
    def __init__(self,n):self.node=n;self.missing=False;self.mismatch=False
    def lookup_transform(self,parent,child,when):
        if self.missing:raise LookupException('not yet available at source time')
        n=self.node;f=n.frames;t=np.eye(4)
        if parent==f['poi'] and child==f['vehicle']:t=n.poi_base.copy()
        elif parent==f['poi'] and child==f['lidar']:t=n.poi_lidar.copy()
        elif parent==f['world'] and child==f['poi']:t[2,3]=.65899
        elif parent==f['world'] and child in (f['source_world'],'odom'):pass
        else:raise LookupException('unknown frames')
        if self.mismatch and parent==f['poi']:t[0,3]+=.01
        m=TransformStamped();m.header.frame_id=parent;m.child_frame_id=child
        m.transform.translation.x,m.transform.translation.y,m.transform.translation.z=map(float,t[:3,3]);m.transform.rotation.w=1.
        assert when.nanoseconds>0
        return m


@pytest.fixture
def node(monkeypatch):
    monkeypatch.setattr(module,'get_package_share_directory',lambda _:str(ROOT))
    rclpy.init();n=module.ScoutInputs();n.timer.cancel()
    n.buffer=FakeTf(n);n.clock_ok=lambda:10.05;n.age_layer='observation_age'
    for name in ['odom_pub','cloud_pub','filtered_cloud_pub','elevation_pub','status_pub','stop_pub']:setattr(n,name,Sink())
    try:yield n
    finally:n.destroy_node();rclpy.try_shutdown()


def odom():
    m=Odometry();m.header.frame_id='FP_ENU0';m.child_frame_id='FP_POI';m.header.stamp.sec=10
    m.pose.pose.position.z=.65899;m.pose.pose.orientation.w=1.
    m.pose.covariance=np.eye(6).ravel().tolist();m.twist.covariance=np.eye(6).ravel().tolist()
    return m


def elevation(n=291,age=True):
    m=GridMap();m.header.frame_id='odom';m.header.stamp.sec=10
    m.info.resolution=.04;m.info.length_x=m.info.length_y=n*.04;m.info.pose.orientation.w=1.0
    m.layers=['elevation','variance']+(['observation_age'] if age else [])
    for i in range(len(m.layers)):
        a=Float32MultiArray();a.layout=MultiArrayLayout(dim=[
            MultiArrayDimension(label='column_index',size=n,stride=n*n),
            MultiArrayDimension(label='row_index',size=n,stride=n)])
        a.data=array('f',np.full(n*n,[0.,.001,.2][i],np.float32).tobytes());m.data.append(a)
    return m


def test_real_odom_callback_publishes_base_link_pose_with_calibrated_offset(node):
    m=odom();node.enqueue('odom',m)
    out=node.odom_pub.messages[-1]
    assert out.header.frame_id=='map' and out.child_frame_id=='base_link'
    assert out.pose.pose.position.x==pytest.approx(-.2005158179045505)
    assert out.pose.pose.position.z==pytest.approx(.23479) and out.header.stamp==m.header.stamp


def test_lidar_callback_applies_external_pose_and_calibration(node):
    m=cloud();node.enqueue('cloud',m)
    out=node.cloud_pub.messages[-1];a=np.frombuffer(bytes(out.data),dtype='<f4').reshape(-1,4)
    assert out.header.frame_id=='map'
    np.testing.assert_allclose(a[0,:3],[1-.0280158179045505,2,3+.78499],atol=1e-6)
    filtered=node.filtered_cloud_pub.messages[-1]
    assert filtered.header==m.header and filtered.header.frame_id=='rslidar'
    raw=np.frombuffer(bytes(filtered.data),dtype='<f4').reshape(-1,4)
    np.testing.assert_array_equal(raw[0],[1,2,3,11])


def test_tf_is_awaited_without_latest_pose_substitution(node):
    node.buffer.missing=True;node.enqueue('cloud',cloud())
    assert not node.cloud_pub.messages and len(node.pending['cloud'])==1
    assert not node.filtered_cloud_pub.messages
    node.buffer.missing=False;node.drain()
    assert len(node.cloud_pub.messages)==1 and not node.pending['cloud']


def test_inconsistent_external_extrinsics_latch_stop(node):
    node.buffer.mismatch=True;node.enqueue('odom',odom())
    assert node.fault=='EXTRINSICS_TF_MISMATCH_RESTART_REQUIRED'
    assert node.stop_pub.messages[-1].data==1 and not node.odom_pub.messages
    node.buffer.mismatch=False;node.enqueue('odom',odom());assert not node.odom_pub.messages


def test_wrong_nav2_frame_contract_is_rejected_without_renaming(node):
    m=odom();m.header.frame_id='map';m.child_frame_id='vrtk_link';node.enqueue('odom',m)
    assert not node.odom_pub.messages and any('REJECTED' in s.data for s in node.status_pub.messages)


def test_native_grid_frame_transform_preserves_age_and_unknowns(node):
    m=elevation();m.data[0].data[1]=float('nan');node.enqueue('elevation',m)
    out=node.elevation_pub.messages[-1]
    assert out.header.frame_id=='map' and np.isnan(out.data[0].data[1])
    np.testing.assert_array_equal(out.data[2].data,m.data[2].data)
    assert out.info.resolution==m.info.resolution and out.header.stamp==m.header.stamp


@pytest.mark.parametrize('message',[lambda:elevation(250),lambda:elevation(age=False)])
def test_incompatible_real_mapper_defaults_are_not_silently_accepted(node,message):
    node.enqueue('elevation',message())
    assert not node.elevation_pub.messages and any('REJECTED' in s.data for s in node.status_pub.messages)


def test_queue_is_bounded_and_fault_clock_is_latched(node):
    node.buffer.missing=True
    for i in range(20):
        m=cloud();m.header.stamp.nanosec=i*10**6;node.enqueue('cloud',m)
    assert len(node.pending['cloud'])==10
    del node.clock_ok
    # Same real clock, then a recorded future previous value: direct callback
    # test only, not a simulator or live /clock publisher.
    node.last_clock=node.get_clock().now().nanoseconds/1e9+1
    node.drain();assert node.fault=='CLOCK_RESET_RESTART_REQUIRED'
    assert node.stop_pub.messages[-1].data==1


def test_true_observation_age_is_preserved_without_rejuvenating_history(node):
    m=elevation();m.data[2].data[7]=123.5
    node.enqueue('elevation',m);out=node.elevation_pub.messages[-1]
    assert out.layers[2]=='observation_age' and out.data[2].data[7]==123.5
    assert out.data[2].data[0]==pytest.approx(.2)


def test_timer_layer_is_not_promoted_to_measurement_freshness(node):
    m=elevation();m.layers[2]='time'
    with pytest.raises(ValueError):node.convert_elevation(m)
    node.age_layer='time'
    with pytest.raises(ValueError):node.convert_elevation(m)


def test_real_age_map_drives_the_existing_ht_model_without_resizing(node):
    import sys
    sys.path.insert(0,str(ROOT.parents[1]/'tools/ht_cupy_bridge'))
    from cupy_to_ht import CupyToHt
    bridge=CupyToHt();bridge.pub=Sink();bridge.history_pub=Sink()
    try:
        m=elevation()
        m.header.stamp=bridge.get_clock().now().to_msg()
        mapped=node.convert_elevation(m)
        body=odom();body.header.stamp=m.header.stamp
        bridge.on_odometry(node.convert_odom(body));bridge.on_map(mapped)
        assert len(bridge.pub.messages)==1
        result=bridge.pub.messages[0]
        assert result.header.frame_id=='map' and result.info.resolution==.04
        assert len(result.layers)==12
        assert result.info.length_x==pytest.approx(241*.04)
        for k in range(8):assert 'ht_dir_'+str(k) in result.layers
        assert bridge.surface.offset_m==pytest.approx(.23479,abs=1e-6)
    finally:bridge.destroy_node()


def test_grid_world_translation_updates_cell_heights_and_center_without_double_z(node):
    original=node.buffer.lookup_transform
    def shifted(parent,child,when):
        t=original(parent,child,when)
        if parent=='map' and child=='odom':
            t.transform.translation.x=2.0;t.transform.translation.y=-3.0;t.transform.translation.z=1.5
        return t
    node.buffer.lookup_transform=shifted
    m=elevation();out=node.convert_elevation(m)
    assert out.info.pose.position.x==2 and out.info.pose.position.y==-3
    assert out.info.pose.position.z==0 and out.data[0].data[0]==pytest.approx(1.5)
    np.testing.assert_array_equal(out.data[1].data,m.data[1].data)
    np.testing.assert_array_equal(out.data[2].data,m.data[2].data)
