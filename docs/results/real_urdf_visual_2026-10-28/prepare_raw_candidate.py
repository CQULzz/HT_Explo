#!/usr/bin/env python3
"""Prepare trusted recorded raw inputs for a geometry-only old/new comparison.

Never starts ROS nodes, devices, simulation or controllers. Only mask fields
change; raw CDR, registration R/t, source stamps and all recorded odometry stay
unaltered. Pickle inputs must be trusted local experiment archives.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import pickle
import time

import numpy as np
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points_numpy


def digest(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(2 ** 20), b''):
            h.update(block)
    return h.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def immutable_record_sha(record):
    return digest(pickle.dumps({key: value for key, value in record.items()
                                if key not in ('before', 'after')}, protocol=5))


def bytes_list_sha(values):
    h = hashlib.sha256()
    for value in values:
        require(isinstance(value, bytes), 'Recorded odometry must remain original serialized bytes')
        h.update(len(value).to_bytes(8, 'little'))
        h.update(value)
    return h.hexdigest()


def timing_summary(values):
    return {'mean_ms': float(np.mean(values) * 1000),
            'median_ms': float(np.median(values) * 1000),
            'p95_ms': float(np.percentile(values, 95) * 1000),
            'max_ms': float(np.max(values) * 1000)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--old-profile', required=True, type=Path)
    parser.add_argument('--new-profile', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    repo, source = args.repo.resolve(), args.source.resolve()
    old_path, new_path = args.old_profile.resolve(), args.new_profile.resolve()
    output = args.output.resolve()
    require(not output.exists(), 'Use a completely new output directory; no overwrite/resume')
    geometry_path = repo / 'src/ht_scout_bridge/ht_scout_bridge/geometry.py'
    spec = importlib.util.spec_from_file_location('frozen_geometry_for_raw_candidate', geometry_path)
    geometry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(geometry)
    old_profile, old_base, old_lidar = geometry.load_calibration(old_path)
    new_profile, new_base, new_lidar = geometry.load_calibration(new_path)
    old_filter, new_filter = old_profile['lidar_self_filter'], new_profile['lidar_self_filter']
    require(len(old_filter['boxes']) == 9 and len(new_filter['boxes']) == 14, 'Expected old 9/new 14 boxes')
    require(new_filter['boxes'][:9] == old_filter['boxes'], 'Existing boxes changed')
    require(new_filter['cylinders'] == old_filter['cylinders'] and len(old_filter['cylinders']) == 4,
            'Existing wheel cylinders changed')
    for key in ('frames', 'transforms'):
        require(old_profile[key] == new_profile[key], f'{key} changed')
    for key in old_filter:
        if key != 'boxes':
            require(old_filter[key] == new_filter[key], f'Existing filter setting changed: {key}')
    np.testing.assert_array_equal(old_base, new_base)
    np.testing.assert_array_equal(old_lidar, new_lidar)
    base_from_lidar = np.linalg.inv(old_base) @ old_lidar
    # Save complete profile snapshots so later production edits do not affect
    # the serialized comparison or conceal which geometry generated its masks.
    source_sha, old_sha, new_sha = file_sha(source), file_sha(old_path), file_sha(new_path)
    completion = new_filter.get('visual_completion_candidate', {})
    if completion:
        require(completion['candidate_old_config_sha256'] == old_sha, 'Candidate was generated from another old config')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'old_profile.yaml').write_bytes(old_path.read_bytes())
    (output / 'new_profile.yaml').write_bytes(new_path.read_bytes())
    partial = output / 'selected_raw_inputs.pkl.gz.partial'
    target = output / 'selected_raw_inputs.pkl.gz'
    frames, immutable_hashes = [], []
    all_removed = []
    old_times, new_times = [], []
    source_header = None
    try:
        with gzip.open(source, 'rb') as reader, gzip.open(partial, 'wb', compresslevel=3) as writer:
            source_header = pickle.load(reader)
            require(source_header['format'] == 'recorded_lidar_rebuild_v1', 'Unsupported raw input stream')
            require(source_header['source_calibration'] == old_profile, 'Source stream calibration/profile differs from old config')
            np.testing.assert_allclose(np.asarray(source_header['base_from_lidar']), base_from_lidar, atol=1e-12, rtol=0)
            require(len(source_header['odometry']) == len(source_header['original_lidar_odometry']) == 2077,
                    'Expected all 2077 original/pose-only odometry messages')
            header = deepcopy(source_header)
            header['pose_scope'] = source_header['pose_scope'] + (
                '; geometry candidate replay preserves all source pose bytes; '
                'NaN twist remains explicitly unmeasured and must never be used as valid control odometry')
            header['candidate_scope'] = (
                'Geometry-only old/new mask comparison: before=previous 9 boxes + 4 cylinders, '
                'after=those unchanged shapes + 5 base_link visual AABBs. Raw sensor CDR, '
                'source/receipt times, R/t, TF and odometry bytes are unchanged. '
                'No new vehicle motion, probability modification or control odometry is asserted.')
            header['mask_variant_profiles'] = {'before': old_profile, 'after': new_profile}
            header['mask_variant_provenance'] = {
                'source_gzip': str(source), 'source_gzip_sha256': source_sha,
                'old_profile_sha256': old_sha, 'new_profile_sha256': new_sha,
                'geometry_source_sha256': file_sha(geometry_path),
                'original_before_semantics': 'Legacy rslidar axis-aligned box; masks replaced only for the new controlled comparison',
                'original_after_semantics': '9 boxes + 4 cylinders; recomputed and checked bitwise before reuse',
                'base_from_lidar_unchanged': True}
            for key in ('odometry', 'original_lidar_odometry'):
                require(header[key] == source_header[key], f'{key} changed')
            pickle.dump(header, writer, protocol=5)
            while True:
                try:
                    original = pickle.load(reader)
                except EOFError:
                    break
                index = len(frames)
                require(isinstance(original, dict) and isinstance(original['raw_cdr'], bytes), 'Invalid raw record')
                message = deserialize_message(original['raw_cdr'], PointCloud2)
                stamp = message.header.stamp.sec * 10 ** 9 + message.header.stamp.nanosec
                require(message.header.frame_id == 'rslidar' and stamp == original['stamp_ns'], 'Raw source frame/stamp changed')
                xyz = read_points_numpy(message, field_names=('x', 'y', 'z'), skip_nans=False).reshape(-1, 3)
                old_saved = np.asarray(original['after'])
                require(old_saved.dtype == np.bool_ and old_saved.shape == (len(xyz),), 'Original mask format mismatch')
                started = time.perf_counter()
                old_mask = geometry.self_filter_keep_mask(xyz, old_filter, base_from_lidar)
                old_elapsed = time.perf_counter() - started
                np.testing.assert_array_equal(old_mask, old_saved)
                started = time.perf_counter()
                new_mask = geometry.self_filter_keep_mask(xyz, new_filter, base_from_lidar)
                new_elapsed = time.perf_counter() - started
                require(not np.any(new_mask & ~old_mask), 'New mask resurrects a previously filtered point')
                removed = old_mask & ~new_mask
                # Coordinates here are diagnostic base_link coordinates only;
                # original sensor bytes and registration matrices remain exact.
                body_xyz = np.asarray(xyz, dtype=float) @ base_from_lidar[:3, :3].T + base_from_lidar[:3, 3]
                extra = body_xyz[removed].copy()
                if len(extra):
                    all_removed.append(extra)
                unchanged_sha = immutable_record_sha(original)
                record = dict(original)
                record['before'], record['after'] = old_mask, new_mask
                require(immutable_record_sha(record) == unchanged_sha, 'Non-mask record values changed')
                require(record['raw_cdr'] == original['raw_cdr'], 'Raw CDR bytes changed')
                for key in ('R', 't'):
                    require(np.asarray(record[key]).dtype == np.asarray(original[key]).dtype and
                            np.asarray(record[key]).tobytes() == np.asarray(original[key]).tobytes(), f'{key} bits changed')
                pickle.dump(record, writer, protocol=5)
                immutable_hashes.append(unchanged_sha)
                old_times.append(old_elapsed)
                new_times.append(new_elapsed)
                frames.append({'index': index, 'stamp_ns': int(original['stamp_ns']),
                               'receipt_ns': int(original['receipt_ns']), 'pose_skew_s': float(original['pose_skew_s']),
                               'raw_cdr_sha256': digest(original['raw_cdr']), 'points': len(xyz),
                               'old_kept': int(old_mask.sum()), 'new_kept': int(new_mask.sum()),
                               'additional_candidate_removals': int(removed.sum()),
                               'removed_base_min_xyz': extra.min(axis=0).tolist() if len(extra) else None,
                               'removed_base_max_xyz': extra.max(axis=0).tolist() if len(extra) else None,
                               'removed_base_min_z': float(extra[:, 2].min()) if len(extra) else None,
                               'old_recomputed_mask_exactly_matches_source_after': True,
                               'new_mask_is_subset_of_old': True,
                               'old_mask_sha256': digest(old_mask.tobytes()), 'new_mask_sha256': digest(new_mask.tobytes()),
                               'immutable_nonmask_record_sha256': unchanged_sha,
                               'old_mask_seconds': old_elapsed, 'new_mask_seconds': new_elapsed})
                if len(frames) % 50 == 0:
                    print(f'Prepared {len(frames)} preserved raw scans', flush=True)
        require(len(frames) == 415, f'Expected 415 scans, found {len(frames)}')
        total = sum(row['additional_candidate_removals'] for row in frames)
        require(total == 1032, f'Expected exactly 1032 additional candidate removals, found {total}')
        # Independently read back the produced stream before giving it its final
        # usable filename; retain a partial file and failure evidence on error.
        with gzip.open(partial, 'rb') as check:
            checked_header = pickle.load(check)
            for key in ('odometry', 'original_lidar_odometry'):
                require(checked_header[key] == source_header[key], f'Output {key} bytes changed')
            for index, expected in enumerate(immutable_hashes):
                record = pickle.load(check)
                require(immutable_record_sha(record) == expected, f'Output non-mask fields changed: frame {index}')
                require(digest(record['before'].tobytes()) == frames[index]['old_mask_sha256'], 'Output old mask changed')
                require(digest(record['after'].tobytes()) == frames[index]['new_mask_sha256'], 'Output new mask changed')
            try:
                pickle.load(check)
            except EOFError:
                pass
            else:
                raise ValueError('Output contains unexpected extra records')
        combined = np.concatenate(all_removed)
        partial.rename(target)
        index = {'status': 'complete', 'created_utc': datetime.now(timezone.utc).isoformat(),
                 'scope': header['candidate_scope'], 'pose_scope': header['pose_scope'],
                 'source': str(source), 'source_sha256': source_sha, 'output': str(target),
                 'output_sha256': file_sha(target), 'old_profile_sha256': old_sha, 'new_profile_sha256': new_sha,
                 'geometry_source_sha256': file_sha(geometry_path),
                 'accepted_scans': len(frames), 'odometry': len(header['odometry']),
                 'original_lidar_odometry': len(header['original_lidar_odometry']),
                 'odometry_bytes_sha256': bytes_list_sha(header['odometry']),
                 'original_lidar_odometry_bytes_sha256': bytes_list_sha(header['original_lidar_odometry']),
                 'all_source_times_raw_cdr_registration_and_odometry_preserved': True,
                 'all_old_masks_bitwise_match_original_after': True, 'all_new_masks_subset_of_old': True,
                 'additional_candidate_removals': total,
                 'scans_with_additional_removals': sum(row['additional_candidate_removals'] > 0 for row in frames),
                 'maximum_additional_removals_per_scan': max(row['additional_candidate_removals'] for row in frames),
                 'last_scan_additional_removals': frames[-1]['additional_candidate_removals'],
                 'removed_base_min_xyz': combined.min(axis=0).tolist(),
                 'removed_base_max_xyz': combined.max(axis=0).tolist(),
                 'removed_base_min_z': float(combined[:, 2].min()),
                 'old_filter_timings': timing_summary(old_times), 'new_filter_timings': timing_summary(new_times),
                 'timing_limit': 'Sequential desktop preprocessing measurements, not ARM or realtime guarantees',
                 'removal_limit': 'Visual-AABB candidate points have no per-point vehicle truth; this input preparation alone does not establish HT or navigation improvement',
                 'frames': frames}
        write_json(output / 'INDEX.json', index)
        write_json(output / 'MASK_COMPARISON.json', {key: value for key, value in index.items() if key != 'frames'})
        np.savez_compressed(output / 'additional_candidate_points_base.npz', points=combined)
        print(json.dumps({key: index[key] for key in ('status', 'accepted_scans', 'additional_candidate_removals',
                                                     'scans_with_additional_removals', 'removed_base_min_z', 'output_sha256')}), flush=True)
    except Exception as error:
        write_json(output / 'FAILURE.json', {'status': 'failed', 'error': str(error),
                                            'completed_frames': len(frames), 'source_sha256': source_sha,
                                            'old_profile_sha256': old_sha, 'new_profile_sha256': new_sha,
                                            'partial_output': str(partial)})
        raise


if __name__ == '__main__':
    main()
