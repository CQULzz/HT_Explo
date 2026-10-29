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
    msg.data=array('B',raw.tobytes());before=serialize_message(msg)
    quaternion=np.array([.1,-.2,.3,.9]);quaternion/=np.linalg.norm(quaternion)
    target=transform([1.23,-2.34,.456],quaternion)
    first=transform_cloud(msg,np.eye(4));second=transform_cloud(first,target)
    filtered,registered=transform_cloud_pair(msg,target)
    assert serialize_message(filtered)==serialize_message(first)
    assert serialize_message(registered)==serialize_message(second)
    assert serialize_message(msg)==before
    # Metadata and output bytes must be independent of each other and source.
    saved=deepcopy(registered);filtered.header.frame_id='changed';filtered.data[0]^=1
    filtered.fields[0].offset=1
    assert registered==saved and serialize_message(msg)==before
