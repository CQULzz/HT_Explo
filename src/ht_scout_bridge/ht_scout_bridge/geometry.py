"""SE(3) reference-point conversion; no ROS, device or simulator startup."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
import yaml


def transform(xyz, xyzw):
    p, q = np.asarray(xyz, float), np.asarray(xyzw, float)
    if p.shape != (3,) or q.shape != (4,) or not np.isfinite(p).all() or not np.isfinite(q).all():
        raise ValueError('Nonfinite pose or wrong vector shape')
    if abs(float(q@q)-1) > .01:
        raise ValueError('Quaternion must have unit norm')
    t = np.eye(4);t[:3,:3] = Rotation.from_quat(q).as_matrix();t[:3,3] = p
    return t


def validate_transform(t):
    t = np.asarray(t, float)
    if (t.shape != (4,4) or not np.isfinite(t).all() or
            not np.allclose(t[3], [0,0,0,1], atol=1e-9, rtol=0) or
            not np.allclose(t[:3,:3].T@t[:3,:3], np.eye(3), atol=1e-8, rtol=0) or
            not np.isclose(np.linalg.det(t[:3,:3]), 1, atol=1e-8, rtol=0)):
        raise ValueError('Invalid rigid transform')
    return t


def from_config(entry):
    rpy = np.asarray(entry['rpy'], float)
    if rpy.shape != (3,) or not np.isfinite(rpy).all():
        raise ValueError('Invalid RPY calibration')
    return transform(entry['xyz'], Rotation.from_euler('xyz', rpy).as_quat())


def load_calibration(path):
    data = yaml.safe_load(Path(path).read_text())
    for key in ['poi_coincident_with_fixposition_link_confirmed','rack_contact_height_confirmed']:
        if data['source'].get(key) is not True:
            raise ValueError('Unconfirmed calibration: '+key)
    frames=data['frames']
    if set(frames) != {'world','source_world','poi','vehicle','lidar'} or len(set(frames.values())) != 5:
        raise ValueError('Source and target frame names must be explicit and distinct')
    t={k:from_config(v) for k,v in data['transforms'].items()}
    poi_base=t['poi_to_base_footprint']@t['base_footprint_to_base_link']
    poi_lidar=poi_base@t['base_link_to_sensor_kit']@t['sensor_kit_to_helios']@t['helios_to_lidar']
    return data, validate_transform(poi_base), validate_transform(poi_lidar)


def skew(v):
    x,y,z=v
    return np.array([[0,-z,y],[z,0,-x],[-y,x,0]],float)


def covariance(values):
    p=np.asarray(values,float).reshape(6,6)
    if not np.isfinite(p).all() or not np.allclose(p,p.T,atol=1e-6,rtol=0):
        raise ValueError('Nonfinite or nonsymmetric covariance')
    if np.linalg.eigvalsh(p).min() < -1e-7:
        raise ValueError('Negative covariance eigenvalue')
    return p


def convert_reference(world_from_source, source_from_poi, poi_from_base,
                      linear, angular, pose_cov, twist_cov):
    """Odometry twist is expressed at/in POI, per the Fixposition ROS contract.

    Preserve lever-arm velocity v_base=R_pb^T(v_poi+omega_poi cross r_pb),
    not just pose. Covariances use first-order fixed-axis pose errors.
    """
    a,b,c=map(validate_transform,(world_from_source,source_from_poi,poi_from_base))
    velocity=np.asarray(linear,float);omega=np.asarray(angular,float)
    if velocity.shape!=(3,) or omega.shape!=(3,) or not np.isfinite([velocity,omega]).all():
        raise ValueError('Invalid odometry twist')
    r=c[:3,3];rotation=c[:3,:3].T
    v=rotation@(velocity+np.cross(omega,r));w=rotation@omega
    j_pose=np.zeros((6,6));j_pose[:3,:3]=a[:3,:3];j_pose[3:,3:]=a[:3,:3]
    j_pose[:3,3:]=-a[:3,:3]@skew(b[:3,:3]@r)
    j_twist=np.zeros((6,6));j_twist[:3,:3]=rotation;j_twist[3:,3:]=rotation
    j_twist[:3,3:]=-rotation@skew(r)
    return a@b@c,v,w,j_pose@covariance(pose_cov)@j_pose.T,j_twist@covariance(twist_cov)@j_twist.T


def transform_cloud(msg, target_from_lidar, self_filter=None):
    """Rigid scan registration; preserves fields, intensity and timestamps.

    This is not per-point motion deskew. The input may be externally deskewed
    while remaining expressed in rslidar; choose that topic in the launch.
    """
    from copy import deepcopy
    from array import array
    t=validate_transform(target_from_lidar)
    if (msg.point_step<=0 or msg.row_step<msg.point_step*msg.width or
            len(msg.data)!=msg.row_step*msg.height or not msg.width or not msg.height):
        raise ValueError('Invalid PointCloud2 storage')
    fields={f.name:f for f in msg.fields}
    if len(fields)!=len(msg.fields):raise ValueError('Duplicate point fields')
    for name in ['x','y','z']:
        f=fields.get(name)
        if f is None or f.datatype!=7 or f.count!=1 or f.offset+4>msg.point_step:
            raise ValueError('Require float32 XYZ fields')
    offsets=[fields[n].offset for n in ['x','y','z']]
    if any(abs(a-b)<4 for i,a in enumerate(offsets) for b in offsets[i+1:]):
        raise ValueError('Overlapping XYZ fields')
    raw=np.ndarray((msg.height,msg.width,msg.point_step),dtype=np.uint8,
                   buffer=bytes(msg.data),strides=(msg.row_step,msg.point_step,1)).copy().reshape(-1,msg.point_step)
    dtype='>f4' if msg.is_bigendian else '<f4'
    xyz=np.stack([np.ndarray((len(raw),),dtype=dtype,buffer=raw,
                  offset=fields[n].offset,strides=(msg.point_step,)) for n in ['x','y','z']],axis=1)
    valid=np.isfinite(xyz).all(axis=1)
    if self_filter and self_filter.get('enabled'):
        lo=np.asarray(self_filter['min_xyz'],float);hi=np.asarray(self_filter['max_xyz'],float)
        if lo.shape!=(3,) or hi.shape!=(3,) or not np.isfinite([lo,hi]).all() or np.any(lo>=hi):
            raise ValueError('Invalid source-frame self filter')
        valid &= ~((xyz>=lo).all(axis=1)&(xyz<=hi).all(axis=1))
    raw=raw[valid].copy();xyz=xyz[valid]
    moved=xyz@t[:3,:3].T+t[:3,3]
    if not np.isfinite(moved).all():raise ValueError('Nonfinite registered points')
    for i,n in enumerate(['x','y','z']):
        values=moved[:,i].astype(dtype)
        if not np.isfinite(values).all():raise ValueError('Registered points overflow float32')
        raw[:,fields[n].offset:fields[n].offset+4]=values.view(np.uint8).reshape(-1,4)
    result=deepcopy(msg);result.height=1;result.width=len(raw)
    result.row_step=result.point_step*result.width;result.is_dense=True
    result.data=array('B',raw.tobytes())
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('calibration');args=parser.parse_args()
    data,base,lidar=load_calibration(args.calibration)
    print(json.dumps({'source':data['source'],'frames':data['frames'],
                      'poi_from_base_link':base.tolist(),'poi_from_rslidar':lidar.tolist()},indent=2))
