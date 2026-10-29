#!/usr/bin/env python3
"""Offline raw-scan reconstruction for recorded Scout TF; no control output.

Use trusted local SQLite bags only. Keep each bag's history independent. The
recorded scout_chassis_link, rather than its ground-level base_link, matches
the production calibration's vehicle origin. All TF lookups use source time.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import pickle
import sqlite3
import sys
import threading
import time
from types import SimpleNamespace

import cupy as cp
import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.serialization import deserialize_message, serialize_message
from rclpy.time import Time
from scipy.spatial.transform import Rotation
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points_numpy
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer
from nav_msgs.msg import Odometry
from elevation_mapping_cupy import ElevationMap, Parameter
from elevation_mapping_cupy.elevation_mapping_ros import ElevationMappingNode

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src/ht_scout_bridge'))
from ht_scout_bridge.geometry import load_calibration, self_filter_keep_mask
from cupy_to_ht import CupyToHt
from replay_real_archive import layers


def matrix(tf):
    t, q = tf.transform.translation, tf.transform.rotation
    out = np.eye(4)
    out[:3, :3] = Rotation.from_quat([q.x, q.y, q.z, q.w]).as_matrix()
    out[:3, 3] = [t.x, t.y, t.z]
    return out


def global_points(history, now):
    result = []
    for (tx, ty), (z, v, t) in sorted(history.tiles.items()):
        latest = np.argmax(t, axis=0)[None]
        zz = np.take_along_axis(z, latest, axis=0)[0]
        tt = np.take_along_axis(t, latest, axis=0)[0]
        i, j = np.nonzero(np.isfinite(zz) & (now-tt <= history.max_age_s))
        result.append(np.column_stack(((tx*history.tile_size+i)*history.resolution,
                                      (ty*history.tile_size+j)*history.resolution, zz[i,j])))
    return np.concatenate(result).astype(np.float32) if result else np.empty((0,3),np.float32)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bag',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--cupy-package',type=Path,required=True)
    p.add_argument('--calibration-file',type=Path,
        default=ROOT/'src/ht_scout_bridge/config/scout_extrinsics.yaml',
        help='Explicit recorded-data calibration/filter profile; defaults to real Scout profile')
    p.add_argument('--self-filter-horizontal-padding-m',type=float,default=0.,
        help='Extra XY-only dilation of each physical primitive; offline experiment, default unchanged')
    p.add_argument('--surface-registration',action='store_true',
        help='Explicitly enable the independently installed scan-to-map Z/tilt registration candidate')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    if not math.isfinite(a.self_filter_horizontal_padding_m) or a.self_filter_horizontal_padding_m<0:
        p.error('self-filter-horizontal-padding-m must be finite and nonnegative')
    (a.output/'frames').mkdir()
    databases=sorted(a.bag.glob('*.db3'))
    assert len(databases)==1, 'Explicit single-file bag expected'
    c=sqlite3.connect('file:'+str(databases[0])+'?mode=ro&immutable=1',uri=True)
    topics={n:i for i,n in c.execute('select id,name from topics')}
    rclpy.init(args=['--ros-args','-p','ht_device:=cuda','-p','ht_quality_backend:=numba',
        '-p','surface_sensor_ground_offset_m:=0.23479','-p','odometry_child_frame:=base_link',
        '-p','ht_small_hole_repair:=true'])
    node=CupyToHt();clock=[0]
    node.get_clock=lambda:SimpleNamespace(now=lambda:Time(nanoseconds=clock[0]))
    ht_out=[];hist_out=[]
    node.pub=SimpleNamespace(publish=ht_out.append,get_subscription_count=lambda:0)
    node.history_pub=SimpleNamespace(publish=hist_out.append,get_subscription_count=lambda:1)
    buf=Buffer(cache_time=Duration(seconds=180.))
    tf_edges={}
    for name in ['/tf_static','/tf']:
        for (data,) in c.execute('select data from messages where topic_id=? order by timestamp',(topics[name],)):
            for t in deserialize_message(data,TFMessage).transforms:
                if name=='/tf_static': buf.set_transform_static(t,'recorded')
                else:buf.set_transform(t,'recorded')
                tf_edges[t.header.frame_id+' -> '+t.child_frame_id]=matrix(t).tolist()
    profile,b,l=load_calibration(a.calibration_file)
    from copy import deepcopy
    baseline_filter=deepcopy(profile['lidar_self_filter'])
    profile['lidar_self_filter']['horizontal_padding_m']=a.self_filter_horizontal_padding_m
    endpoint_filter=deepcopy(profile['lidar_self_filter'])
    endpoint_filter.pop('wheel_occlusion',None)
    expected=np.linalg.inv(b)@l
    recorded=matrix(buf.lookup_transform('scout_chassis_link','rslidar',Time()))
    assert np.allclose(recorded,expected,atol=1e-7), (recorded,expected)
    plugin=a.output/'plugins.yaml';plugin.write_text('min_filter:\n  enable: false\n')
    param=Parameter(use_chainer=False,resolution=.04,map_length=11.64,
        weight_file=str(a.cupy_package/'config/core/weights.dat'),plugin_config_file=str(plugin),
        enable_drift_compensation=False,enable_overlap_clearance=False,enable_deterministic_fusion=True)
    if a.surface_registration and not hasattr(param,'enable_surface_registration'):
        raise RuntimeError('Install the independent mapper with --surface-registration first')
    if hasattr(param,'enable_surface_registration'):
        param.enable_surface_registration=a.surface_registration
    param.subscriber_cfg={'scan':{'data_type':'pointcloud'}};param.update()
    mapping=ElevationMap(param);assert mapping.fusion_backend=='deterministic'
    native=[]
    proxy=SimpleNamespace(map_translation=True,map=mapping,last_integrated_stamp=None,
        map_access_lock=threading.RLock(),map_data=np.empty((291,291),np.float32),map_frame='map',
        publisher_configs={'raw':{'layers':['elevation','variance','observation_age'],'basic_layers':['elevation']}},
        map_publishers={'raw':SimpleNamespace(publish=native.append)})
    freeze={'scope':'Offline raw lidar -> stable CuPy -> production HT history/local crop -> HT; no control',
        'commit':__import__('subprocess').check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'bag':str(a.bag),'tf_edges':tf_edges,'recorded_chassis_from_lidar':recorded.tolist(),
        'canonical_vehicle_frame':'recorded scout_chassis_link, renamed base_link only in in-process odometry',
        'integration':'all scans with exact-time TF, no latest-pose fallback',
        'ht_output_period_s':.5,'history_initialization':'empty per bag',
        'drift_compensation':False,'overlap_clearance':False,
        'self_filter_horizontal_padding_m':a.self_filter_horizontal_padding_m,
        'self_filter_vertical_bounds_unchanged':True,
        'calibration_file':str(a.calibration_file),
        'wheel_occlusion':profile['lidar_self_filter'].get('wheel_occlusion',{'enabled':False}),
        'surface_registration':a.surface_registration,
        'surface_registration_scope':'Map input only; recorded odometry/TF is not rewritten; not a physical localization calibration',
        'effective_scalar_parameters':{k:v for k,v in vars(param).items()
            if v is None or isinstance(v,(str,int,float,bool))},
        'parameter_limit':'Offline drift/overlap disabled as in preceding stable experiment; not full online launch',
        'sources':{}}
    for f in [Path(__file__),ROOT/'tools/ht_cupy_bridge/cupy_to_ht.py',ROOT/'tools/ht_cupy_bridge/historical_elevation.py',ROOT/'src/ht_scout_bridge/config/scout_extrinsics.yaml',ROOT/'src/ht_scout_bridge/ht_scout_bridge/geometry.py']:
        freeze['sources'][str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
    freeze['sources'][str(a.calibration_file)]=hashlib.sha256(a.calibration_file.read_bytes()).hexdigest()
    from elevation_mapping_cupy import elevation_mapping as mapper_module
    mapper_source=Path(mapper_module.__file__)
    for f in [mapper_source,mapper_source.with_name('parameter.py'),
              mapper_source.with_name('deterministic_fusion.py'),mapper_source.with_name('surface_registration.py')]:
        if f.is_file():freeze['sources'][str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
    (a.output/'FREEZE.json').write_text(json.dumps(freeze,indent=2)+'\n')
    rows=[];scans=[];last=None;next_map=None;first=None
    native_file=(a.output/'native_stream.pkl').open('wb')
    try:
        for scan,(receipt,data) in enumerate(c.execute('select timestamp,data from messages where topic_id=? order by timestamp',(topics['/rslidar_points'],))):
            m=deserialize_message(data,PointCloud2);ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec
            row={'scan':scan,'receipt_ns':receipt,'stamp_ns':ns}
            try:
                sensor=matrix(buf.lookup_transform('map',m.header.frame_id,Time(nanoseconds=ns)))
                vehicle=matrix(buf.lookup_transform('map','scout_chassis_link',Time(nanoseconds=ns)))
            except Exception as e:
                row.update(status='SKIPPED_NO_EXACT_TIME_TF',reason=str(e));scans.append(row);continue
            if last is not None and ns<=last:
                row.update(status='SKIPPED_NONMONOTONIC_SOURCE_STAMP');scans.append(row);continue
            xyz=read_points_numpy(m,field_names=('x','y','z'),skip_nans=False).reshape(-1,3)
            keep=self_filter_keep_mask(xyz,profile['lidar_self_filter'],recorded)
            old_keep=self_filter_keep_mask(xyz,baseline_filter,recorded)
            endpoint_keep=self_filter_keep_mask(xyz,endpoint_filter,recorded)
            assert not np.any(keep&~old_keep)
            assert not np.any(keep&~endpoint_keep)
            begun=time.perf_counter();mapping.move_to(vehicle[:3,3],vehicle[:3,:3])
            if last is not None:
                param.time_interval=(ns-last)/1e9;mapping.update_time();mapping.update_variance()
            mapping.input_pointcloud(xyz[keep].copy(),['x','y','z'],sensor[:3,:3].copy(),sensor[:3,3].copy(),0.,0.,observation_stamp=ns/1e9)
            cp.cuda.get_current_stream().synchronize()
            row.update(status='INTEGRATED',kept_points=int(keep.sum()),raw_points=len(xyz),extra_removed_points=int((old_keep&~keep).sum()),integration_s=time.perf_counter()-begun)
            row['wheel_occlusion_removed_points']=int((endpoint_keep&~keep).sum())
            row['surface_registration']=dict(getattr(mapping,'last_surface_registration',{'status':'UNAVAILABLE'}))
            scans.append(row);last=ns;first=ns if first is None else first
            next_map=ns if next_map is None else next_map
            if ns < next_map:continue
            next_map=ns+500_000_000
            proxy.last_integrated_stamp=Time(nanoseconds=ns);ElevationMappingNode.publish_map(proxy,'raw');src=native.pop()
            pickle.dump(serialize_message(src),native_file,protocol=5)
            odom=Odometry();odom.header=src.header;odom.child_frame_id='base_link'
            odom.pose.pose.position.x,odom.pose.pose.position.y,odom.pose.pose.position.z=map(float,vehicle[:3,3])
            q=Rotation.from_matrix(vehicle[:3,:3]).as_quat()
            odom.pose.pose.orientation.x,odom.pose.pose.orientation.y,odom.pose.pose.orientation.z,odom.pose.pose.orientation.w=map(float,q)
            clock[0]=ns+30_000_000;node.on_odometry(odom)
            begun=time.perf_counter();node.on_map(src);elapsed=time.perf_counter()-begun
            item={'scan':scan,'stamp_ns':ns,'t_s':(ns-first)/1e9,'ht_s':elapsed,'output':bool(ht_out)}
            if ht_out:
                ht=ht_out.pop();hd=layers(ht);local=layers(hist_out.pop())
                yaw=Rotation.from_matrix(vehicle[:3,:3]).as_euler('xyz')[2]
                file=f'frame_{len(rows):04d}.npz'
                gp=global_points(node.history,ns/1e9)
                np.savez_compressed(a.output/'frames'/file,global_xyz=gp,robot=np.r_[vehicle[:3,3],yaw],
                    stamp_ns=ns,center=[ht.info.pose.position.x,ht.info.pose.position.y],resolution=ht.info.resolution,
                    local_center=[src.info.pose.position.x,src.info.pose.position.y],local_elevation=local['elevation'],
                    native_elevation=layers(src)['elevation'],**hd)
                item.update(file=file,global_cells=len(gp),ht_valid=int((hd['ht_valid']>=.5).sum()))
            rows.append(item)
            print(a.bag.name,'scan',scan,'HT',len(rows),item,flush=True)
        if node.history is not None:node.history.save(a.output/'history_final.npz')
    finally:
        native_file.close();node.destroy_node();rclpy.try_shutdown();c.close()
        (a.output/'RESULTS.json').write_text(json.dumps({'frames':rows,'scans':scans,'diagnostics':node.diagnostics,
            'integrated':sum(s['status']=='INTEGRATED' for s in scans),'input_scans':len(scans),
            'outputs':sum(r['output'] for r in rows)},indent=2)+'\n')


if __name__=='__main__':main()
