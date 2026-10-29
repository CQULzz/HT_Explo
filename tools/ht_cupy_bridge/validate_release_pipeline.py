#!/usr/bin/env python3
"""Frozen offline scan-to-HT comparison. No DDS executor, playback or control.

Every exact-time-TF scan generates a map. Service time includes cloud pair,
CuPy integration/export, elevation adapter and HT. Disk/CDR decoding, TF lookup,
comparison and archive compression are excluded. This is not ARM or online
queue performance; both variants use one BLAS worker to isolate code changes.
"""
import argparse
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import platform
import sqlite3
import sys
import threading
import time
from types import SimpleNamespace as S

import cupy as cp
import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.serialization import deserialize_message
from rclpy.time import Time
from scipy.spatial.transform import Rotation
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points_numpy
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer,TransformException
from nav_msgs.msg import Odometry
from elevation_mapping_cupy import ElevationMap,Parameter
from ament_index_python.packages import get_package_share_directory
from threadpoolctl import threadpool_limits


def load(name,path,package=False):
    spec=importlib.util.spec_from_file_location(name,path,
        submodule_search_locations=[str(path.parent)] if package else None)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module)
    return module


def matrix(tf):
    q,p=tf.transform.rotation,tf.transform.translation
    t=np.eye(4);t[:3,:3]=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();t[:3,3]=[p.x,p.y,p.z]
    return t


def arrays(msg):
    n=round(msg.info.length_x/msg.info.resolution)
    return {name:np.roll(np.asarray(data.data,np.float32).reshape((n,n),order='F'),
            (-msg.outer_start_index,-msg.inner_start_index),(0,1)) for name,data in zip(msg.layers,msg.data)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--variant',choices=['baseline','candidate'],required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--reference',type=Path)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=False);(args.output/'frames').mkdir()
    plan=json.loads(args.plan.read_text());root=Path(__file__).resolve().parents[2]
    module_dir=Path(plan['baseline_ht']) if args.variant=='baseline' else root/'tools/ht_cupy_bridge'
    sys.path.insert(0,str(module_dir))
    ht=importlib.import_module('cupy_to_ht')
    package=Path(plan['baseline_scout']) if args.variant=='baseline' else root/'src/ht_scout_bridge/ht_scout_bridge'
    load('experiment_scout',package/'__init__.py',True)
    geometry=importlib.import_module('experiment_scout.geometry');inputs=importlib.import_module('experiment_scout.node')
    if args.variant=='baseline':publisher=load('experiment_mapper',Path(plan['baseline_mapper'])).ElevationMappingNode
    else:
        from elevation_mapping_cupy.elevation_mapping_ros import ElevationMappingNode as publisher
    rclpy.init(args=['--ros-args','-p','ht_device:=cuda','-p','ht_quality_backend:=numba',
        '-p','surface_sensor_ground_offset_m:=0.23479','-p','odometry_child_frame:=base_link','-p','ht_small_hole_repair:=true'])
    bridge=ht.CupyToHt();adapter=inputs.ScoutInputs();clock=[0]
    bridge.get_clock=lambda:S(now=lambda:Time(nanoseconds=clock[0]))
    outputs=[];bridge.pub=S(publish=outputs.append,get_subscription_count=lambda:1)
    bridge.history_pub=S(get_subscription_count=lambda:0)
    if hasattr(bridge,'performance_pub'):bridge.performance_pub=S(publish=lambda _:None)
    captured=[None];prepare=ht.prepare_ht_context
    def capture(*a,**kw):
        result=prepare(*a,**kw);captured[0]=result[0];return result
    ht.prepare_ht_context=capture
    limit=threadpool_limits(limits=1,user_api='blas')
    db=sqlite3.connect(Path(plan['source_bag']).as_uri()+'?mode=ro&immutable=1',uri=True)
    buffer=Buffer(cache_time=Duration(seconds=180.))
    for name in ['/tf_static','/tf']:
        for (data,) in db.execute('select data from messages where topic_id=(select id from topics where name=?) order by timestamp',(name,)):
            for t in deserialize_message(data,TFMessage).transforms:
                if name=='/tf_static':buffer.set_transform_static(t,'recorded')
                else:buffer.set_transform(t,'recorded')
    profile,base,lidar=geometry.load_calibration(root/'src/ht_scout_bridge/config/scout_extrinsics.yaml')
    extrinsics=np.linalg.inv(base)@lidar
    assert np.allclose(matrix(buffer.lookup_transform('scout_chassis_link','rslidar',Time())),extrinsics,atol=1e-7)
    plugin=args.output/'plugins.yaml';plugin.write_text('min_filter:\n  enable: false\n')
    weights=Path(get_package_share_directory('elevation_mapping_cupy'))/'config/core/weights.dat'
    if not weights.is_file():raise FileNotFoundError(weights)
    param=Parameter(use_chainer=False,resolution=.04,map_length=11.64,weight_file=str(weights),
        plugin_config_file=str(plugin),enable_deterministic_fusion=True,enable_drift_compensation=False,
        enable_overlap_clearance=False)
    if hasattr(param,'enable_surface_registration'):param.enable_surface_registration=False
    param.subscriber_cfg={'scan':{'data_type':'pointcloud'}};param.update();mapping=ElevationMap(param)
    assert mapping.fusion_backend=='deterministic'
    native=[];proxy=S(map_translation=True,map=mapping,last_integrated_stamp=None,map_access_lock=threading.RLock(),
        map_data=np.empty((291,291),np.float32),map_frame='map',
        publisher_configs={'raw':{'layers':['elevation','variance','observation_age'],'basic_layers':['elevation']}},
        map_publishers={'raw':S(publish=native.append,get_subscription_count=lambda:1)})
    report={'scope':__doc__,'variant':args.variant,'architecture':platform.machine(),'rows':[],'skips':[],
        'comparison':{'frames':0,'native_mismatches':0,'non_probability_mismatches':0,'geometry_mismatches':0,
                      'height_mismatches':0,'threshold_flips':0,'max_probability_error':0.},
        'sources':{str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(__file__),Path(ht.__file__),Path(geometry.__file__),Path(inputs.__file__)]}}
    (args.output/'FREEZE.json').write_text(json.dumps({**report,'plan':plan},indent=2)+'\n')
    last=None;wall=time.perf_counter()
    try:
        for index,(data,) in enumerate(db.execute('select data from messages where topic_id=(select id from topics where name=?) order by timestamp',('/rslidar_points',))):
            msg=deserialize_message(data,PointCloud2);ns=msg.header.stamp.sec*10**9+msg.header.stamp.nanosec
            try:
                sensor=matrix(buffer.lookup_transform('map',msg.header.frame_id,Time(nanoseconds=ns)))
                body=matrix(buffer.lookup_transform('map','scout_chassis_link',Time(nanoseconds=ns)))
            except TransformException as e:report['skips'].append({'scan':index,'reason':str(e)});continue
            started=time.perf_counter()
            if args.variant=='baseline':
                filtered=geometry.transform_cloud(msg,np.eye(4),profile['lidar_self_filter'],extrinsics)
                registered=geometry.transform_cloud(filtered,sensor)
            else:filtered,registered=geometry.transform_cloud_pair(msg,sensor,profile['lidar_self_filter'],extrinsics)
            cloud_done=time.perf_counter()
            xyz=read_points_numpy(filtered,field_names=('x','y','z'),skip_nans=False).reshape(-1,3)
            mapping.move_to(body[:3,3],body[:3,:3])
            if last is not None:param.time_interval=(ns-last)/1e9;mapping.update_time();mapping.update_variance()
            mapping.input_pointcloud(xyz.copy(),['x','y','z'],sensor[:3,:3].copy(),sensor[:3,3].copy(),0.,0.,observation_stamp=ns/1e9)
            cp.cuda.get_current_stream().synchronize();last=ns
            proxy.last_integrated_stamp=Time(nanoseconds=ns);publisher.publish_map(proxy,'raw');source=native.pop()
            mapper_done=time.perf_counter();source=adapter.convert_elevation(source);adapter_done=time.perf_counter()
            odom=Odometry();odom.header=source.header;odom.child_frame_id='base_link'
            odom.pose.pose.position.x,odom.pose.pose.position.y,odom.pose.pose.position.z=map(float,body[:3,3])
            q=Rotation.from_matrix(body[:3,:3]).as_quat()
            odom.pose.pose.orientation.x,odom.pose.pose.orientation.y,odom.pose.pose.orientation.z,odom.pose.pose.orientation.w=map(float,q)
            clock[0]=ns+30_000_000;bridge.on_odometry(odom);bridge.on_map(source);finished=time.perf_counter()
            assert len(outputs)==1,f'No unique HT output for scan {index}'
            result=outputs.pop();layers=arrays(result);src=arrays(source)
            saved={'stamp_ns':ns,'source_center':[source.info.pose.position.x,source.info.pose.position.y],
                'center':[result.info.pose.position.x,result.info.pose.position.y],'resolution':result.info.resolution,
                'height':captured[0],**{'native_'+k:v for k,v in src.items()},**layers}
            if args.reference:
                with np.load(args.reference/'frames'/f'scan_{index:04d}.npz') as ref:
                    cmp=report['comparison'];cmp['frames']+=1
                    for k,v in saved.items():
                        before=ref[k]
                        if k.startswith('ht_dir_'):
                            finite=np.isfinite(v)&np.isfinite(before)
                            cmp['non_probability_mismatches']+=int(not np.array_equal(np.isfinite(v),np.isfinite(before)))
                            cmp['threshold_flips']+=int(np.count_nonzero((v[finite]>=.5)!=(before[finite]>=.5)))
                            cmp['max_probability_error']=max(cmp['max_probability_error'],float(np.max(np.abs(v[finite]-before[finite]),initial=0)))
                        elif not np.array_equal(v,before,equal_nan=True):
                            group='native_mismatches' if k.startswith('native_') else ('height_mismatches' if k=='height' else ('non_probability_mismatches' if k.startswith('ht_') else 'geometry_mismatches'))
                            cmp[group]+=1
            np.savez_compressed(args.output/'frames'/f'scan_{index:04d}.npz',**saved)
            report['rows'].append({'scan':index,'stamp_ns':ns,'kept_points':filtered.width,'service_s':finished-started,
                'cloud_s':cloud_done-started,'mapping_and_publish_s':mapper_done-cloud_done,
                'adapter_s':adapter_done-mapper_done,'ht_s':finished-adapter_done,
                'diagnostic':bridge.diagnostics[-1]})
            if len(report['rows'])%50==0:print(args.variant,'outputs',len(report['rows']),'service_ms',round(1000*(finished-started),2),'comparison',report['comparison'],flush=True)
        assert len(report['rows'])==641 and len(report['skips'])==2
    finally:
        report['wall_s_including_archive']=time.perf_counter()-wall
        values=report['rows'][plan['exclude_first_integrated_scans']:]
        report['summary']={}
        for name in ['service_s','cloud_s','mapping_and_publish_s','adapter_s','ht_s']:
            times=[r[name] for r in values]
            if times:report['summary'][name]=dict(zip(['median_ms','p95_ms','max_ms'],map(float,np.percentile(times,[50,95,100])*1000)))
        report['processing_capacity_hz']=len(values)/sum(r['service_s'] for r in values) if values else None
        (args.output/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
        adapter.destroy_node();bridge.destroy_node();rclpy.try_shutdown();db.close()
    print(json.dumps({'summary':report['summary'],'comparison':report['comparison'],'processing_capacity_hz':report['processing_capacity_hz']},indent=2),flush=True)


if __name__=='__main__':main()
