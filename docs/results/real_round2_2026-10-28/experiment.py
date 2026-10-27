"""Offline round two: identical HT inputs, timed arrivals, and raw cloud filters."""
import argparse
from pathlib import Path
import json
import sys
import time
import threading
import pickle
import gzip
import sqlite3
import hashlib
import numpy as np

ROOT=Path(__file__).resolve().parents[3]


def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--stage',choices=['ht','timed','cloud'],required=True)
    p.add_argument('--bridge-dir',type=Path,default=ROOT/'tools/ht_cupy_bridge')
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--commit',required=True)
    p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    p.add_argument('--quality-backend',choices=['numpy','numba','auto'],default='numpy')
    p.add_argument('--input',type=Path,help='Explicit serialized-map input for an independent rebuild')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(a.bridge_dir))
    import replay_real_archive as replay
    replay.current_commit=lambda:a.commit
    # Override only declared execution parameters in both frozen code versions.
    # The baseline's source bytes are preserved; the live node is checked too.
    original_init=replay.rclpy.init
    def init(args=None,**kwargs):
        options=[s.replace('ht_device:=cpu','ht_device:='+a.device)
                   .replace('ht_quality_backend:=numpy','ht_quality_backend:='+a.quality_backend) for s in (args or [])]
        return original_init(args=options,**kwargs)
    replay.rclpy.init=init
    actual=[];original_node_init=replay.CupyToHt.__init__
    def node_init(self):
        original_node_init(self)
        assert str(self.device)==a.device
        actual.append({'device':str(self.device),'quality_backend':self.quality_backend,
                       'cpu_fused_batchnorm':getattr(self,'cpu_fuse_bn',False)})
    replay.CupyToHt.__init__=node_init
    source=a.input or a.archive/'validation/jetson_scout_2026-10-23/quality_optimization/live_input.pkl'
    if a.stage=='ht':
        # recompute creates its own fresh subdirectory.
        replay.recompute(source,a.output/'maps')
        path=a.output/'maps/index.json';metadata=json.loads(path.read_text())
        metadata['actual_execution']=actual[-1]
        metadata['parameters'].update(ht_device=a.device,ht_quality_backend=actual[-1]['quality_backend'],
                                      ht_cpu_fuse_bn=actual[-1]['cpu_fused_batchnorm'])
        save(path,metadata);return
    if a.stage=='timed':
        import rclpy
        from rclpy.serialization import deserialize_message
        from rclpy.time import Time
        from grid_map_msgs.msg import GridMap
        from nav_msgs.msg import Odometry
        from types import SimpleNamespace
        raw=pickle.loads(source.read_bytes())
        maps=[deserialize_message(b,GridMap) for b in raw['maps']]
        odoms=[deserialize_message(b,Odometry) for b in raw['odometry']]
        events=sorted([(replay.stamp(m),'odom',m) for m in odoms]+[(replay.stamp(m),'map',m) for m in maps],key=lambda v:v[0])
        rclpy.init(args=['--ros-args','-p','ht_device:=cpu','-p','ht_quality_backend:=numpy',
                        '-p','surface_sensor_ground_offset_m:=0.23479','-p','odometry_child_frame:=base_link','-p','ht_small_hole_repair:=true'])
        n=replay.CupyToHt();start=time.monotonic();epoch=events[0][0];published=[];done=threading.Event();errors=[]
        n.get_clock=lambda:SimpleNamespace(now=lambda:Time(nanoseconds=epoch+int((time.monotonic()-start+.03)*1e9)))
        n.pub=SimpleNamespace(publish=lambda m:published.append(replay.stamp(m)),get_subscription_count=lambda:0)
        n.history_pub=SimpleNamespace(get_subscription_count=lambda:0)
        def worker():
            try:
                while True:
                    m=n.pending_maps.take()
                    if m is not None:n.on_map(m)
                    elif done.is_set():break
                    else:time.sleep(.001)
            except BaseException as e:errors.append(repr(e))
        thread=threading.Thread(target=worker);thread.start()
        try:
            for stamp,kind,m in events:
                wait=(stamp-epoch)/1e9-(time.monotonic()-start)
                if wait>0:time.sleep(wait)
                if kind=='odom':n.on_odometry(m)
                else:n.enqueue_map(m)
            done.set();thread.join(timeout=10)
            if thread.is_alive() or errors:raise RuntimeError(str(errors) or 'worker failed to stop')
            result={'scope':'Six-second trace at recorded arrival cadence; in-process pending queue, not DDS or navigation',
                    'commit':a.commit,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
                    'input_maps':len(maps),'outputs':len(published),'pending_replaced':n.pending_maps.replaced,
                    'published_source_stamps':published,'elapsed_wall_s':time.monotonic()-start,
                    'input_fault':n.input_odometry.fault,'diagnostics':n.diagnostics}
            result['actual_execution']=actual[-1]
            save(a.output/'timed.json',result)
            print({k:v for k,v in result.items() if k not in ['diagnostics','published_source_stamps']},flush=True)
        finally:
            done.set();thread.join(timeout=10);n.destroy_node();rclpy.try_shutdown()
        return
    sys.path.insert(0,str(ROOT/'src/ht_scout_bridge'))
    from ht_scout_bridge.geometry import load_calibration,self_filter_keep_mask
    from sensor_msgs_py.point_cloud2 import read_points_numpy
    from sensor_msgs.msg import PointCloud2
    from rclpy.serialization import deserialize_message
    profile,b,l=load_calibration(ROOT/'src/ht_scout_bridge/config/scout_extrinsics.yaml')
    base_from_lidar=np.linalg.inv(b)@l
    old={'enabled':True,'min_xyz':[-1,-.7,-.9],'max_xyz':[.2,.7,.2]}
    bag=a.archive/'validation/arm_vehicle/results/demo_20261011_225010/rosbag'
    frames=[];records=[];next_receipt=None;first=None
    for database in sorted(bag.glob('*.db3'),key=lambda x:int(x.stem.split('_')[-1])):
        c=sqlite3.connect('file:'+str(database)+'?mode=ro&immutable=1',uri=True)
        topic=c.execute("select id from topics where name='/rslidar_points'").fetchone()[0]
        begin=c.execute('select timestamp from messages where topic_id=? order by timestamp limit 1',(topic,)).fetchone()[0]
        end=c.execute('select timestamp from messages where topic_id=? order by timestamp desc limit 1',(topic,)).fetchone()[0]
        if next_receipt is None:next_receipt=begin
        while next_receipt<=end:
            row=c.execute('select timestamp,data from messages where topic_id=? and timestamp>=? order by timestamp limit 1',(topic,next_receipt)).fetchone()
            if row is None:break
            receipt,blob=row;m=deserialize_message(blob,PointCloud2)
            xyz=read_points_numpy(m,field_names=('x','y','z'),skip_nans=False).reshape(-1,3)
            # Same exact production mask function, same points and source geometry.
            t=time.perf_counter();before=self_filter_keep_mask(xyz,old);old_ms=(time.perf_counter()-t)*1000
            t=time.perf_counter();after=self_filter_keep_mask(xyz,profile['lidar_self_filter'],base_from_lidar);new_ms=(time.perf_counter()-t)*1000
            base_xyz=xyz@base_from_lidar[:3,:3].T+base_from_lidar[:3,3]
            finite=np.isfinite(xyz).all(1)
            low=finite&(xyz[:,2]>=-1.1)&(xyz[:,2]<=-.7)&(np.hypot(base_xyz[:,0],base_xyz[:,1])<=1.5)
            inside_model=finite&~after
            first=replay.stamp(m) if first is None else first
            name=f'cloud_{len(frames):04d}.npz'
            np.savez_compressed(a.output/name,xyz=xyz,before=before,after=after,low=low)
            frames.append({'file':name,'t_s':(replay.stamp(m)-first)/1e9,'stamp_ns':replay.stamp(m),'receipt_ns':receipt,
                           'finite_points':int(finite.sum()),'low_points':int(low.sum()),
                           'old_low_kept':int((low&before).sum()),'new_low_kept':int((low&after).sum()),
                           'old_kept_inside_model':int((inside_model&before).sum()),
                           'old_filter_ms':old_ms,'new_filter_ms':new_ms,
                           'input_cdr_sha256':hashlib.sha256(blob).hexdigest()})
            records.append(('/rslidar_points',receipt,blob));next_receipt+=5_000_000_000
        c.close();print('cloud source',database.name,'snapshots',len(frames),flush=True)
    with gzip.open(a.output/'selected_original_clouds.pkl.gz','wb',compresslevel=3) as f:pickle.dump(records,f,protocol=5)
    save(a.output/'index.json',{'scope':'Selected original lidar scans; low-height returns are terrain candidates, not ground-truth labels; no elevation rebuilding',
        'commit':a.commit,'source':str(bag),'sample_period_s':5,'frames':frames,
        'legacy_filter':old,'physical_filter':profile['lidar_self_filter'],'base_from_lidar':base_from_lidar.tolist(),
        'low_return_definition':'rslidar z in [-1.1,-0.7]m and base XY radius <=1.5m',
        'no_vehicle_motion':True,'calibration_unchanged':True})


if __name__=='__main__':main()
