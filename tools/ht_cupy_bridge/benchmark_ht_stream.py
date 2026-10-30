#!/usr/bin/env python3
"""Measure the HT consumer against an already reconstructed native stream.

Direct callbacks only: no bag player, executor, simulated time publisher or
control output. Source timestamps/TF are retained. Service time excludes file
I/O and is not the vehicle publication rate or an ARM performance claim.
"""
import argparse
import cProfile
import hashlib
import json
from pathlib import Path
import pickle
import platform
import sqlite3
import sys
import time
from types import SimpleNamespace

import numpy as np
import rclpy
from rclpy.duration import Duration
from rclpy.serialization import deserialize_message
from rclpy.time import Time
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer
import torch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stream', type=Path, required=True)
    parser.add_argument('--bag', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--module-dir', type=Path, default=Path(__file__).parent)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--capture-context', action='store_true')
    parser.add_argument('--save-frames', action='store_true')
    parser.add_argument('--profile', action='store_true')
    parser.add_argument('--device', choices=['cpu', 'cuda'], default='cuda')
    parser.add_argument('--parameter', action='append', default=[])
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    if args.save_frames:(args.output/'frames').mkdir()
    sys.path.insert(0, str(args.module_dir.resolve()))
    from cupy_to_ht import CupyToHt

    ros_args = ['--ros-args']
    parameters = ['ht_device:='+args.device, 'ht_quality_backend:=numba',
                  'surface_sensor_ground_offset_m:=0.23479',
                  'odometry_child_frame:=base_link', 'ht_small_hole_repair:=true']
    for param in parameters + args.parameter:
        ros_args += ['-p', param]
    rclpy.init(args=ros_args)
    node = CupyToHt()
    clock = [0]
    node.get_clock = lambda: SimpleNamespace(now=lambda: Time(nanoseconds=clock[0]))
    outputs = []
    node.pub = SimpleNamespace(publish=outputs.append, get_subscription_count=lambda: 0)
    node.history_pub = SimpleNamespace(publish=lambda _: None, get_subscription_count=lambda: 0)
    # A performance topic, when present, also remains in-process.
    if hasattr(node, 'performance_pub'):
        node.performance_pub = SimpleNamespace(publish=lambda _: None)
    buffer = Buffer(cache_time=Duration(seconds=180.))
    database = sqlite3.connect(args.bag.resolve().as_uri()+'?mode=ro&immutable=1', uri=True)
    for name in ['/tf_static', '/tf']:
        for (data,) in database.execute(
                'select data from messages where topic_id=(select id from topics where name=?) order by timestamp', (name,)):
            for transform in deserialize_message(data, TFMessage).transforms:
                if name == '/tf_static':
                    buffer.set_transform_static(transform, 'recorded')
                else:
                    buffer.set_transform(transform, 'recorded')
    database.close()
    rows, captured = [], []
    hook = None
    if args.capture_context:
        hook = node.model.register_forward_pre_hook(
            lambda _model, inputs: captured.append(inputs[0].detach().cpu().numpy()[0, 0].copy()))
    profile = cProfile.Profile()
    comparison = {'frames': 0, 'max_probability_error': 0., 'threshold_flips': 0,
                  'mask_or_geometry_mismatches': 0, 'non_probability_mismatches': 0}
    try:
        with args.stream.open('rb') as stream:
            index = 0
            while True:
                try:
                    source = deserialize_message(pickle.load(stream), GridMap)
                except EOFError:
                    break
                ns = source.header.stamp.sec*10**9+source.header.stamp.nanosec
                vehicle = buffer.lookup_transform('map', 'scout_chassis_link', Time(nanoseconds=ns))
                odometry = Odometry()
                odometry.header = source.header
                odometry.child_frame_id = 'base_link'
                odometry.pose.pose.position.x = vehicle.transform.translation.x
                odometry.pose.pose.position.y = vehicle.transform.translation.y
                odometry.pose.pose.position.z = vehicle.transform.translation.z
                odometry.pose.pose.orientation = vehicle.transform.rotation
                clock[0] = ns+30_000_000
                node.on_odometry(odometry)
                if args.profile:
                    profile.enable()
                cpu_started = time.thread_time()
                started = time.perf_counter()
                node.on_map(source)
                elapsed = time.perf_counter()-started
                cpu_elapsed = time.thread_time()-cpu_started
                if args.profile:
                    profile.disable()
                if not outputs:
                    raise RuntimeError(f'No HT output at source {ns}')
                result = outputs.pop()
                layers = {name: np.asarray(data.data, np.float32).reshape(241, 241, order='F')
                          for name, data in zip(result.layers, result.data)}
                row = dict(node.diagnostics[-1], direct_callback_s=elapsed,
                           direct_callback_thread_cpu_s=cpu_elapsed)
                rows.append(row)
                if args.reference:
                    with np.load(args.reference/'frames'/f'frame_{index:04d}.npz') as ref:
                        comparison['frames'] += 1
                        if (int(ref['stamp_ns']) != ns or float(ref['resolution']) != result.info.resolution
                                or not np.array_equal(ref['center'], [result.info.pose.position.x, result.info.pose.position.y])):
                            comparison['mask_or_geometry_mismatches'] += 1
                        for name, value in layers.items():
                            before = ref[name]
                            if name.startswith('ht_dir_'):
                                finite = np.isfinite(value) & np.isfinite(before)
                                comparison['mask_or_geometry_mismatches'] += int(not np.array_equal(np.isfinite(value), np.isfinite(before)))
                                comparison['threshold_flips'] += int(np.count_nonzero((value[finite] >= .5) != (before[finite] >= .5)))
                                comparison['max_probability_error'] = max(comparison['max_probability_error'], float(np.max(np.abs(value[finite]-before[finite]), initial=0)))
                            elif not np.array_equal(value, before, equal_nan=True):
                                comparison['non_probability_mismatches'] += 1
                if args.capture_context:
                    np.savez_compressed(args.output/f'context_{index:04d}.npz',
                                        height=captured.pop(), stamp_ns=ns)
                if args.save_frames:
                    np.savez_compressed(args.output/'frames'/f'frame_{index:04d}.npz',
                        stamp_ns=ns,resolution=result.info.resolution,
                        center=[result.info.pose.position.x,result.info.pose.position.y],**layers)
                index += 1
        summary = {}
        for key in ['fusion_and_quality_s', 'support_and_history_publish_s', 'network_inference_s',
                    'ht_serialize_publish_s', 'elapsed_s', 'direct_callback_s']:
            values = np.array([row[key] for row in rows[5:]])
            summary[key] = dict(zip(['median', 'p95', 'max'], map(float, [np.median(values), np.percentile(values, 95), np.max(values)])))
        report = {'scope': __doc__, 'warmup_frames_excluded': 5, 'frames': len(rows),
                  'architecture': platform.machine(), 'torch': torch.__version__,
                  'device': str(node.device), 'parameters': parameters+args.parameter,
                  'runtime_manifest':getattr(node,'runtime_manifest',None),
                  'stream': str(args.stream), 'summary': summary, 'comparison': comparison,
                  'source_sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in args.module_dir.glob('*.py')}, 'diagnostics': rows}
        (args.output/'RESULTS.json').write_text(json.dumps(report, indent=2)+'\n')
        if args.profile:
            profile.dump_stats(str(args.output/'profile.pstats'))
        print(json.dumps({k: report[k] for k in ['frames', 'summary', 'comparison']}, indent=2))
    finally:
        if hook is not None:
            hook.remove()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
