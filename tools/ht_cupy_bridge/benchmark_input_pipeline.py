#!/usr/bin/env python3
"""Offline bridge-byte parity and throughput against frozen pre-change code.

Reads exact source-time TF directly from SQLite. No bag player, controller or
executor. Geometry service timings exclude disk, deserialization and hashing.
"""
import argparse
from array import array
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import pickle
import platform
import sqlite3
import sys
import time

import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.serialization import deserialize_message,serialize_message
from rclpy.time import Time
from tf2_ros import Buffer,TransformException
from tf2_msgs.msg import TFMessage
from sensor_msgs.msg import PointCloud2
from grid_map_msgs.msg import GridMap
from scipy.spatial.transform import Rotation
from threadpoolctl import threadpool_info,threadpool_limits


def summary(values):
    return dict(zip(['median_ms','p95_ms','max_ms'],map(float,np.percentile(values,[50,95,100])*1000)))


def canonical(value):
    """All message fields and exact array bytes, excluding CDR alignment pads.

    CDR serializers may leave alignment padding unspecified. Comparing the
    entire serialized envelope can falsely reject identical ROS messages.
    Float array bytes retain NaN payloads and signed zeros in this check.
    """
    if hasattr(value,'get_fields_and_field_types'):
        return tuple((name,canonical(getattr(value,name))) for name in value.get_fields_and_field_types())
    if isinstance(value,array):return ('array',value.typecode,value.itemsize,value.tobytes())
    if isinstance(value,np.ndarray):return ('ndarray',value.dtype.str,value.shape,value.tobytes())
    if isinstance(value,(list,tuple)):return tuple(canonical(v) for v in value)
    return value


def message_hash(msg):
    return hashlib.sha256(pickle.dumps(canonical(msg),protocol=5)).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-package',type=Path,required=True)
    p.add_argument('--bag',type=Path,required=True)
    p.add_argument('--native-stream',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--baseline-blas-threads',type=int,default=28)
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    root=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(root/'src/ht_scout_bridge'))
    from ht_scout_bridge import geometry as current
    spec=importlib.util.spec_from_file_location('baseline_scout',a.baseline_package/'__init__.py',
                    submodule_search_locations=[str(a.baseline_package)])
    package=importlib.util.module_from_spec(spec);sys.modules['baseline_scout']=package;spec.loader.exec_module(package)
    original=importlib.import_module('baseline_scout.geometry')
    profile,base,lidar=current.load_calibration(root/'src/ht_scout_bridge/config/scout_extrinsics.yaml')
    base_from_lidar=np.linalg.inv(base)@lidar
    database=sqlite3.connect(a.bag.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)
    buffer=Buffer(cache_time=Duration(seconds=180.))
    for name in ['/tf_static','/tf']:
        for (data,) in database.execute('select data from messages where topic_id=(select id from topics where name=?) order by timestamp',(name,)):
            for transform in deserialize_message(data,TFMessage).transforms:
                if name=='/tf_static':buffer.set_transform_static(transform,'recorded')
                else:buffer.set_transform(transform,'recorded')
    def pose_at(msg):
        t=buffer.lookup_transform('map',msg.header.frame_id,Time.from_msg(msg.header.stamp))
        q,v=t.transform.rotation,t.transform.translation
        pose=np.eye(4);pose[:3,:3]=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();pose[:3,3]=[v.x,v.y,v.z]
        return pose
    def before(msg,pose):
        filtered=original.transform_cloud(msg,np.eye(4),profile['lidar_self_filter'],base_from_lidar)
        return filtered,original.transform_cloud(filtered,pose)
    def after(msg,pose):
        return current.transform_cloud_pair(msg,pose,profile['lidar_self_filter'],base_from_lidar)
    report={'scope':__doc__,'architecture':platform.machine(),'blas_pools_initial':threadpool_info(),
            'input':str(a.bag),'pointclouds':[],'cloud_differences':[],'skipped_no_exact_tf':[],
            'cloud_timing_runs':[],'elevation_differences':[],'elevation_timing_runs':[]}
    saved=[]
    for i,(data,) in enumerate(database.execute('select data from messages where topic_id=(select id from topics where name=?) order by timestamp',('/rslidar_points',))):
        msg=deserialize_message(data,PointCloud2)
        try:pose=pose_at(msg)
        except TransformException as e:
            report['skipped_no_exact_tf'].append({'index':i,'reason':str(e)});continue
        with threadpool_limits(limits=a.baseline_blas_threads,user_api='blas'):ref=before(msg,pose)
        with threadpool_limits(limits=1,user_api='blas'):result=after(msg,pose)
        ref_bytes=[serialize_message(m) for m in ref];new_bytes=[serialize_message(m) for m in result]
        ref_hashes=[message_hash(m) for m in ref];new_hashes=[message_hash(m) for m in result]
        equal=ref_hashes==new_hashes
        row={'index':i,'stamp_ns':msg.header.stamp.sec*10**9+msg.header.stamp.nanosec,
             'input_points':msg.height*msg.width,'kept_points':result[0].width,
             'source_CDR_sha256':hashlib.sha256(data).hexdigest(),
             'baseline_canonical_sha256':ref_hashes,
             'candidate_canonical_sha256':new_hashes,
             'cdr_envelope_equal':ref_bytes==new_bytes}
        report['pointclouds'].append(row)
        if not equal:report['cloud_differences'].append(i)
        if i%20==0:saved.append((msg,pose))
        if i in (20,320,640) or not equal:
            for variant,values in [('baseline',ref_bytes),('candidate',new_bytes)]:
                for kind,value in zip(['filtered','registered'],values):
                    (a.output/f'scan_{i:04d}_{variant}_{kind}.cdr').write_bytes(value)
        if i%100==0:print('cloud parity',i,'equal',equal,flush=True)
    (a.output/'CLOUD_PARITY.json').write_text(json.dumps(report,indent=2)+'\n')
    assert len(report['pointclouds'])==641 and len(report['skipped_no_exact_tf'])==2
    assert not report['cloud_differences'],report['cloud_differences']
    for repetition in range(3):
        for name,fn,threads in [('original_28_threads',before,a.baseline_blas_threads),
                                ('original_1_thread',before,1),('candidate_1_thread',after,1)]:
            values=[]
            with threadpool_limits(limits=threads,user_api='blas'):
                for msg,pose in saved[:3]:fn(msg,pose)
                for msg,pose in saved:
                    started=time.perf_counter();fn(msg,pose);values.append(time.perf_counter()-started)
            row={'variant':name,'repetition':repetition+1,'samples':len(values),'service_s':values,**summary(values)}
            report['cloud_timing_runs'].append(row);print({k:v for k,v in row.items() if k!='service_s'},flush=True)
    maps=[]
    with a.native_stream.open('rb') as stream:
        while True:
            try:maps.append(deserialize_message(pickle.load(stream),GridMap))
            except EOFError:break
    # These maps already use the map frame, so conversion needs no substitute
    # TF. This measures validation/packing, not a complete online TF chain.
    assert len(maps)==117
    rclpy.init()
    try:
        from baseline_scout.node import ScoutInputs as OriginalInputs
        from ht_scout_bridge.node import ScoutInputs as CurrentInputs
        reference_hashes=[]
        for name,cls in [('baseline',OriginalInputs),('candidate',CurrentInputs)]:
            node=cls();values=[]
            try:
                for repetition in range(3):
                    values=[]
                    for i,msg in enumerate(maps):
                        source=message_hash(msg)
                        started=time.perf_counter();converted=node.convert_elevation(msg);values.append(time.perf_counter()-started)
                        packed=serialize_message(converted)
                        if repetition==0:
                            h=message_hash(converted)
                            if name=='baseline':reference_hashes.append(h)
                            elif h!=reference_hashes[i]:report['elevation_differences'].append(i)
                        assert message_hash(msg)==source
                    row={'variant':name,'repetition':repetition+1,'service_s':values,**summary(values)}
                    report['elevation_timing_runs'].append(row)
                    print({k:v for k,v in row.items() if k!='service_s'},flush=True)
            finally:node.destroy_node()
    finally:rclpy.try_shutdown()
    assert not report['elevation_differences'],report['elevation_differences']
    report['elevation_frames']=len(maps);report['elevation_baseline_sha256']=reference_hashes
    report['summary']={}
    for group in ['cloud_timing_runs','elevation_timing_runs']:
        report['summary'][group]={}
        for name in sorted({row['variant'] for row in report[group]}):
            report['summary'][group][name]=summary([v for row in report[group] if row['variant']==name for v in row['service_s']])
    report['source_sha256']={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [Path(current.__file__),Path(original.__file__),Path(__file__)]}
    database.close();(a.output/'RESULTS.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report['summary'],indent=2),flush=True)


if __name__=='__main__':main()
