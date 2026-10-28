"""SE(3) reference-point conversion; no ROS, device or simulator startup."""
import argparse
import json
import math
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


def self_filter_keep_mask(xyz, self_filter=None, filter_from_lidar=None):
    """Remove geometry, with optional XY-only dilation for explicit trials.

    horizontal_padding_m is additional to dimensions already in the profile.
    Dilating wheel cylinders in X/Y preserves their original vertical bounds;
    increasing the radius instead would also remove more nearby ground.
    """
    points=np.asarray(xyz,float)
    if points.ndim!=2 or points.shape[1]!=3:raise ValueError('Expected Nx3 points')
    valid=np.isfinite(points).all(axis=1)
    if not self_filter or not self_filter.get('enabled'):return valid
    if 'boxes' not in self_filter:
        # Explicit legacy configurations retain their original source frame.
        lo=np.asarray(self_filter['min_xyz'],float);hi=np.asarray(self_filter['max_xyz'],float)
        if lo.shape!=(3,) or hi.shape!=(3,) or not np.isfinite([lo,hi]).all() or np.any(lo>=hi):
            raise ValueError('Invalid source-frame self filter')
        return valid & ~((points>=lo).all(axis=1)&(points<=hi).all(axis=1))
    padding=float(self_filter.get('horizontal_padding_m',0.))
    if not math.isfinite(padding) or padding<0:
        raise ValueError('horizontal_padding_m must be finite and nonnegative')
    if self_filter.get('frame')!='base_link' or filter_from_lidar is None:
        raise ValueError('Body geometry requires calibrated base_link-from-lidar transform')
    t=validate_transform(filter_from_lidar)
    points=points@t[:3,:3].T+t[:3,3]
    if not self_filter['boxes']:raise ValueError('Empty body geometry')
    boxes=[];cylinders=[];lower=np.full(3,np.inf);upper=np.full(3,-np.inf)
    for box in self_filter['boxes']:
        lo=np.asarray(box['min_xyz'],float);hi=np.asarray(box['max_xyz'],float)
        if lo.shape!=(3,) or hi.shape!=(3,) or not np.isfinite([lo,hi]).all() or np.any(lo>=hi):
            raise ValueError('Invalid body box')
        extent=np.array([padding,padding,0.]);lo=lo-extent;hi=hi+extent
        boxes.append((lo,hi));lower=np.minimum(lower,lo);upper=np.maximum(upper,hi)
    for cylinder in self_filter.get('cylinders',[]):
        center=np.asarray(cylinder['center_xyz'],float)
        radius=float(cylinder['radius']);half=float(cylinder['half_length'])
        if (center.shape!=(3,) or not np.isfinite(center).all() or cylinder['axis']!='y'
                or not math.isfinite(radius) or not math.isfinite(half) or min(radius,half)<=0):
            raise ValueError('Invalid wheel cylinder')
        cylinders.append((center,radius,half))
        extent=np.array([radius+padding,half+padding,radius]);lower=np.minimum(lower,center-extent);upper=np.maximum(upper,center+extent)
    # Most scan returns are metres outside the vehicle. Test detailed geometry
    # only inside its exact union AABB; this cannot remove a new point or miss
    # a box/cylinder relative to the unaccelerated union.
    selected=valid&(points>=lower).all(axis=1)&(points<=upper).all(axis=1)
    points=points[selected];occupied=np.zeros(len(points),bool)
    for lo,hi in boxes:occupied|=(points>=lo).all(axis=1)&(points<=hi).all(axis=1)
    for center,radius,half in cylinders:
        local=points-center
        # Exact horizontal rectangular dilation of a Y-axis cylinder.
        radial_x=np.maximum(np.abs(local[:,0])-padding,0.)
        occupied|=(radial_x**2+local[:,2]**2<=radius**2)&(np.abs(local[:,1])<=half+padding)
    valid[selected]&=~occupied
    return valid


def transform_cloud(msg, target_from_lidar, self_filter=None, filter_from_lidar=None):
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
    valid=self_filter_keep_mask(xyz,self_filter,filter_from_lidar)
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
