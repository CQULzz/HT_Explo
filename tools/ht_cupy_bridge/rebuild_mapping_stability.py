#!/usr/bin/env python3
"""Repeated offline native CuPy rebuilds on one immutable recorded scan stream.

This is a mapping experiment, not a ROS bag player or vehicle controller. Each
instance starts empty. Raw CDR, point order, calibrated poses and source times
are identical across instances. Serialized diagnostic streams preserve every
scan's internal state so a late difference can be traced to its first cause.
Only trusted local pickle archives may be supplied.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path
import pickle
import threading
import time
from types import SimpleNamespace

import cupy as cp
import numpy as np
from rclpy.serialization import deserialize_message, serialize_message
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points_numpy
from elevation_mapping_cupy import ElevationMap, Parameter
from elevation_mapping_cupy.elevation_mapping_ros import ElevationMappingNode


def file_sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            result.update(block)
    return result.hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def snapshot(mapping):
    names = ['elevation_map', 'observation_stamps', 'normal_map', 'new_map', 'center']
    return {name: cp.asnumpy(getattr(mapping, name)).copy() for name in names}


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--input', type=Path, required=True)
    cli.add_argument('--package-dir', type=Path, required=True)
    cli.add_argument('--output', type=Path, required=True)
    cli.add_argument('--backend', choices=['legacy', 'deterministic'], required=True)
    cli.add_argument('--repetitions', type=int, default=3)
    cli.add_argument('--mask', choices=['before', 'after'], default='after')
    args = cli.parse_args()
    if args.repetitions < 3:
        cli.error('At least three fresh instances are required for this experiment')
    args.output.mkdir(parents=True, exist_ok=False)
    plugin = args.output / 'plugins.yaml'
    plugin.write_text('min_filter:\n  enable: false\n')
    instances = []
    diagnostic_streams = []
    all_rows = []
    with gzip.open(args.input, 'rb') as reader:
        header = pickle.load(reader)
        for number in range(args.repetitions):
            folder = args.output / f'run_{number}'
            folder.mkdir()
            param = Parameter(use_chainer=False, resolution=.04, map_length=11.64,
                              weight_file=str(args.package_dir / 'config/core/weights.dat'),
                              plugin_config_file=str(plugin), enable_drift_compensation=False,
                              enable_overlap_clearance=False,
                              enable_deterministic_fusion=args.backend == 'deterministic')
            param.subscriber_cfg = {'scan': {'data_type': 'pointcloud'}}
            param.update()
            mapping = ElevationMap(param)
            assert mapping.fusion_backend == args.backend
            n = mapping.cell_n - 2
            assert n == 291
            captured = []
            node = SimpleNamespace(map_translation=True, map=mapping, last_integrated_stamp=None,
                map_access_lock=threading.RLock(), map_data=np.empty((n, n), np.float32), map_frame='map',
                publisher_configs={'raw': {'layers': ['elevation', 'variance', 'observation_age'],
                                           'basic_layers': ['elevation']}},
                map_publishers={'raw': SimpleNamespace(publish=captured.append)})
            parameters = {k: v for k, v in vars(param).items()
                          if isinstance(v, (str, int, float, bool))}
            write(folder / 'PARAMETERS.json', parameters)
            instances.append((mapping, node, captured, [], folder))
            diagnostic = gzip.open(folder / 'internal_states.pkl.gz', 'wb', compresslevel=1)
            pickle.dump({'format': 'cupy_internal_states_v1', 'backend': args.backend,
                         'scope': 'Every recorded scan, native arrays, not manufactured observations'},
                        diagnostic, protocol=5)
            diagnostic_streams.append(diagnostic)
        first = last = None
        index = 0
        try:
            while True:
                try:
                    record = pickle.load(reader)
                except EOFError:
                    break
                source = deserialize_message(record['raw_cdr'], PointCloud2)
                xyz = read_points_numpy(source, field_names=('x', 'y', 'z'), skip_nans=False).reshape(-1, 3)
                keep = record[args.mask]
                assert keep.dtype == np.bool_ and keep.shape == (len(xyz),)
                filtered = xyz[keep]
                stamp = record['stamp_ns'] / 1e9
                first = stamp if first is None else first
                row = {'scan': index, 'stamp_ns': record['stamp_ns'],
                       'raw_cdr_sha256': hashlib.sha256(record['raw_cdr']).hexdigest(),
                       'mask_sha256': hashlib.sha256(keep.tobytes()).hexdigest(),
                       'kept_points': len(filtered), 'instances': []}
                for number, (mapping, node, captured, maps, folder) in enumerate(instances):
                    started = time.perf_counter()
                    mapping.move_to(record['t'].copy(), record['R'].copy())
                    if last is not None:
                        mapping.param.time_interval = stamp - last
                        mapping.update_time()
                        mapping.update_variance()
                    mapping.input_pointcloud(filtered.copy(), ['x', 'y', 'z'],
                        record['R'].copy(), record['t'].copy(), 0., 0., observation_stamp=stamp)
                    cp.cuda.get_current_stream().synchronize()
                    integration_s = time.perf_counter() - started
                    internal = snapshot(mapping)
                    hashes = {name: hashlib.sha256(array.tobytes()).hexdigest()
                              for name, array in internal.items()}
                    pickle.dump({'scan': index, 'stamp_ns': record['stamp_ns'], **internal},
                                diagnostic_streams[number], protocol=5)
                    if index % 2 == 0:
                        node.last_integrated_stamp = Time(nanoseconds=record['stamp_ns'])
                        ElevationMappingNode.publish_map(node, 'raw')
                        message = captured.pop()
                        assert message.layers == ['elevation', 'variance', 'observation_age']
                        maps.append(serialize_message(message))
                    row['instances'].append({'run': number, 'integration_s': integration_s,
                                             'internal_state_sha256': hashes})
                all_rows.append(row)
                index += 1
                last = stamp
                if index % 25 == 0:
                    print(args.backend, index, 'raw scans x', args.repetitions, 'instances', flush=True)
        finally:
            for stream in diagnostic_streams:
                stream.close()
    assert index == 415 and last is not None
    for mapping, node, captured, maps, folder in instances:
        assert len(maps) == 208
        (folder / 'native_maps.pkl').write_bytes(pickle.dumps(
            {'maps': maps, 'odometry': header['odometry']}, protocol=5))
    different_steps = []
    different_names = {}
    for row in all_rows:
        reference = row['instances'][0]['internal_state_sha256']
        changed = {name for entry in row['instances'][1:]
                   for name in reference if entry['internal_state_sha256'][name] != reference[name]}
        if changed:
            different_steps.append(row['scan'])
            for name in changed:
                different_names[name] = different_names.get(name, 0) + 1
    summary = {'scope': 'Offline identical-input repeated mapping; no HT/controller/vehicle movement',
               'backend': args.backend, 'source': str(args.input.resolve()),
               'source_sha256': file_sha(args.input), 'mask': args.mask,
               'repetitions': args.repetitions, 'raw_scans': index, 'maps_per_instance': 208,
               'source_duration_s': last - first, 'all_internal_states_bit_identical': not different_steps,
               'different_scan_indices': different_steps, 'changed_layer_step_counts': different_names,
               'rows': all_rows,
               'timing_limit': 'Integration includes GPU synchronization, excludes CPU diagnostic copies/compression; offline, not live end-to-end latency'}
    write(args.output / 'SUMMARY.json', summary)
    print({k: v for k, v in summary.items() if k not in ('rows', 'different_scan_indices')}, flush=True)


if __name__ == '__main__':
    main()
