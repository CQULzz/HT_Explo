from pathlib import Path
from copy import deepcopy
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from ht_scout_bridge.geometry import load_calibration,transform,convert_reference,transform_cloud,self_filter_keep_mask

PROFILE=Path(__file__).resolve().parents[1]/'config/scout_extrinsics.yaml'


def test_calibration_chain_matches_source_and_ground_height():
    meta,b,l=load_calibration(PROFILE)
    np.testing.assert_allclose(b[:3,3],[-.2005158179045505,0,-.4242],atol=1e-12)
    np.testing.assert_allclose(l[:3,3],[-.0280158179045505,0,.126],atol=1e-12)
    np.testing.assert_allclose((np.linalg.inv(b)@l)[:3,3],[.1725,0,.5502],atol=1e-12)
    assert meta['source']['poi_coincident_with_fixposition_link_confirmed']


@pytest.mark.parametrize('yaw',[0,30,90,-90,179])
def test_position_offset_rotates_with_vehicle_instead_of_fixed_world_offset(yaw):
    _,b,_=load_calibration(PROFILE)
    q=Rotation.from_euler('z',yaw,degrees=True).as_quat()
    src=transform([10,20,.65899],q)
    t,v,w,pc,tc=convert_reference(np.eye(4),src,b,[1,0,0],[0,0,0],np.eye(6),np.eye(6))
    np.testing.assert_allclose(t[:3,3],src[:3,3]+src[:3,:3]@b[:3,3],atol=1e-10)
    assert t[2,3]==pytest.approx(.23479)
    np.testing.assert_allclose(t[:3,:3],src[:3,:3])


def test_rotation_adds_lever_arm_velocity_and_rotates_covariance():
    _,b,_=load_calibration(PROFILE)
    t,v,w,p,c=convert_reference(np.eye(4),np.eye(4),b,[0,0,0],[0,0,1],np.eye(6),np.eye(6))
    np.testing.assert_allclose(v,[0,-.2005158179045505,0],atol=1e-10)
    np.testing.assert_allclose(w,[0,0,1]);np.testing.assert_allclose(p,p.T)
    assert np.linalg.eigvalsh(p).min()>0 and np.linalg.eigvalsh(c).min()>0


def test_parent_world_transform_is_composed_not_frame_renamed():
    _,b,_=load_calibration(PROFILE)
    world=transform([50,-3,2],Rotation.from_euler('z',40,degrees=True).as_quat())
    src=transform([10,20,1],[0,0,0,1])
    t,*_=convert_reference(world,src,b,[0,0,0],[0,0,0],np.eye(6),np.eye(6))
    np.testing.assert_allclose(t,world@src@b,atol=1e-10)
    assert not np.allclose(t,src@b)


def cloud(big=False,padded=True):
    from sensor_msgs.msg import PointCloud2,PointField
    from array import array
    m=PointCloud2();m.header.frame_id='rslidar';m.header.stamp.sec=10
    m.height=2;m.width=2;m.point_step=16;m.row_step=40 if padded else 32;m.is_bigendian=big
    m.fields=[PointField(name=n,offset=4*i,datatype=PointField.FLOAT32,count=1) for i,n in enumerate(['x','y','z','intensity'])]
    raw=bytearray(m.row_step*m.height)
    a=np.ndarray((2,2,4),dtype='>f4' if big else '<f4',buffer=raw,strides=(m.row_step,m.point_step,4))
    a[:]=np.array([[[1,2,3,11],[4,5,6,22]],[[7,8,9,33],[float('nan'),0,0,44]]])
    m.data=array('B',raw);return m


@pytest.mark.parametrize('big',[False,True])
@pytest.mark.parametrize('padded',[False,True])
def test_organized_and_endian_clouds_preserve_intensity_and_source_stamp(big,padded):
    m=cloud(big,padded);source=bytes(m.data)
    t=transform([1,2,3],Rotation.from_euler('z',90,degrees=True).as_quat())
    out=transform_cloud(m,t);assert out.width==3 and out.height==1 and out.header.stamp==m.header.stamp
    a=np.frombuffer(bytes(out.data),dtype='>f4' if big else '<f4').reshape(3,4)
    np.testing.assert_allclose(a[:,:3],np.array([[1,2,3],[4,5,6],[7,8,9]])@t[:3,:3].T+t[:3,3],atol=1e-6)
    np.testing.assert_array_equal(a[:,3],[11,22,33]);assert bytes(m.data)==source


@pytest.mark.parametrize('case',['quaternion','position','covariance','matrix'])
def test_invalid_transform_data_rejected(case):
    _,b,_=load_calibration(PROFILE)
    if case=='quaternion':
        with pytest.raises(ValueError):transform([0,0,0],[0,0,0,0])
    elif case=='position':
        with pytest.raises(ValueError):transform([float('nan'),0,0],[0,0,0,1])
    else:
        a=np.eye(4);p=np.eye(6)
        if case=='covariance':p[0,0]=-1
        else:a[0,0]=2
        with pytest.raises(ValueError):convert_reference(a,np.eye(4),b,[0,0,0],[0,0,0],p,np.eye(6))


def test_lidar_self_filter_uses_source_coordinates_without_inventing_free_cells():
    m=cloud(False,False)
    raw=np.frombuffer(bytes(m.data),dtype='<f4').copy().reshape(4,4)
    raw[0,:3]=[0,0,0]  # Vehicle return inside the source profile's body box.
    from array import array
    m.data=array('B',raw.tobytes())
    profile,b,l=load_calibration(PROFILE)
    out=transform_cloud(m,np.eye(4),profile['lidar_self_filter'],np.linalg.inv(b)@l)
    assert out.width==2
    points=np.frombuffer(bytes(out.data),dtype='<f4').reshape(2,4)
    np.testing.assert_array_equal(points[:,3],[22,33])


def test_physical_filter_retains_ground_and_nearby_features_but_removes_front_and_wheels():
    profile,b,l=load_calibration(PROFILE);base_from_lidar=np.linalg.inv(b)@l
    base=np.array([[0,0,-.23479],[0,.5,-.23479],[.55,.45,-.19],
                   [.44,0,0],[.249,.29153,-.0702],[0,0,0],
                   [.249+.15,.29153,-.0702+.15],[0,0,-.4],
                   [.249+.15,.33153,-.0702+.15]],float)
    lidar=(base-base_from_lidar[:3,3])@base_from_lidar[:3,:3]
    keep=self_filter_keep_mask(lidar,profile['lidar_self_filter'],base_from_lidar)
    # The old point at y=.29153 is inside the now-modeled visual chassis
    # shell's 2cm margin (max y=.2930249); it was only outside the wheel cylinder.
    # A point another 4cm outboard must still be retained as nearby terrain.
    np.testing.assert_array_equal(keep,[True,True,True,False,False,False,False,True,True])
    legacy={'enabled':True,'min_xyz':[-1,-.7,-.9],'max_xyz':[.2,.7,.2]}
    old=self_filter_keep_mask(lidar,legacy)
    assert not old[0] and old[3]  # Actual old-ground deletion/front-body omission.


def test_body_filter_requires_its_calibrated_reference_and_preserves_nonfinite_rejection():
    profile,b,l=load_calibration(PROFILE)
    with pytest.raises(ValueError):self_filter_keep_mask(np.zeros((1,3)),profile['lidar_self_filter'])
    invalid=np.array([[np.nan,0,0],[0,np.inf,0]],float)
    with np.errstate(invalid='ignore'):
        assert not self_filter_keep_mask(invalid,profile['lidar_self_filter'],np.linalg.inv(b)@l).any()


def test_union_broad_phase_matches_every_unaccelerated_shape():
    profile,b,l=load_calibration(PROFILE);t=np.linalg.inv(b)@l;f=profile['lidar_self_filter']
    base=np.random.default_rng(7).uniform(-4,4,(30000,3));inside=np.zeros(len(base),bool)
    for box in f['boxes']:inside|=(base>=box['min_xyz']).all(1)&(base<=box['max_xyz']).all(1)
    for cylinder in f['cylinders']:
        local=base-cylinder['center_xyz'];inside|=(local[:,0]**2+local[:,2]**2<=cylinder['radius']**2)&(np.abs(local[:,1])<=cylinder['half_length'])
    lidar=(base-t[:3,3])@t[:3,:3]
    np.testing.assert_array_equal(self_filter_keep_mask(lidar,f,t),~inside)
