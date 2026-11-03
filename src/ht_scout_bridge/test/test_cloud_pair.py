from array import array
from copy import deepcopy

import numpy as np
import pytest
from sensor_msgs.msg import PointCloud2,PointField
from rclpy.serialization import serialize_message

from ht_scout_bridge.geometry import transform_cloud,transform_cloud_pair,transform


@pytest.mark.parametrize('big_endian',[False,True])
@pytest.mark.parametrize('row_padding',[0,11])
def test_pair_matches_two_serial_transforms_and_preserves_all_input_bytes(big_endian,row_padding):
    msg=PointCloud2();msg.header.frame_id='rslidar';msg.header.stamp.sec=10
    msg.height=2;msg.width=5;msg.point_step=24;msg.row_step=msg.width*msg.point_step+row_padding
    msg.is_bigendian=big_endian
    msg.fields=[PointField(name=n,offset=i*4,datatype=7,count=1) for i,n in enumerate(['x','y','z','intensity'])]
    msg.fields.append(PointField(name='ring',offset=16,datatype=4,count=1))
    raw=np.full((msg.height,msg.row_step),173,np.uint8)
    dtype='>f4' if big_endian else '<f4'
    values=np.array([[1,2,3,11],[-0.,0.,1,22],[np.nan,0,0,33],[4,-5,6,44],[1e-20,-1e-20,.1,55]],np.float32)
    for row in range(2):
        for col in range(5):raw[row,col*24:col*24+16]=values[col].astype(dtype).view(np.uint8)
    msg.data=array('B',raw.tobytes());before=deepcopy(msg)
    quaternion=np.array([.1,-.2,.3,.9]);quaternion/=np.linalg.norm(quaternion)
    target=transform([1.23,-2.34,.456],quaternion)
    first=transform_cloud(msg,np.eye(4));second=transform_cloud(first,target)
    filtered,registered=transform_cloud_pair(msg,target)
    # Compare every message field and byte of point storage. CDR alignment
    # padding is unspecified and may differ across serializations on ARM.
    assert filtered==first
    assert registered==second
    assert msg==before
    # Metadata and output bytes must be independent of each other and source.
    saved=deepcopy(registered);filtered.header.frame_id='changed';filtered.data[0]^=1
    filtered.fields[0].offset=1
    assert registered==saved and msg==before


def test_filter_trace_preserves_removed_returns_without_reintroducing_them():
    from ht_scout_bridge.geometry import cloud_filter_trace
    msg=PointCloud2();msg.header.frame_id='rslidar';msg.header.stamp.sec=123
    msg.height=1;msg.width=3;msg.point_step=12;msg.row_step=36
    msg.fields=[PointField(name=n,offset=i*4,datatype=7,count=1) for i,n in enumerate(('x','y','z'))]
    msg.data=array('B',np.array([[0,0,0],[2,0,0],[np.nan,0,0]],'<f4').tobytes())
    config={'enabled':True,'min_xyz':[-.5,-.5,-.5],'max_xyz':[.5,.5,.5]}
    t=np.eye(4);t[0,3]=5
    a,b=transform_cloud_pair(msg,t,config)
    audit={};c,d=transform_cloud_pair(msg,t,config,audit=audit)
    assert serialize_message(a)==serialize_message(c) and serialize_message(b)==serialize_message(d)
    trace=cloud_filter_trace(msg,t,audit)
    assert trace.header==msg.header and trace.width==2 and a.width==1
    points=np.frombuffer(trace.data,dtype=[('x','<f4'),('y','<f4'),('z','<f4'),('reject_flags','<u4'),('raw_index','<u4')])
    np.testing.assert_array_equal(points['x'],[5,7])
    np.testing.assert_array_equal(points['reject_flags'],[1,0])
    np.testing.assert_array_equal(points['raw_index'],[0,1])
