#!/usr/bin/env python3
"""Numerical comparisons of repeated recorded native GridMaps, not CDR padding.

No CUDA, mapper, HT model, driver, controller or ROS node is started. This reads
trusted local pickle experiment archives containing serialized GridMaps only.
"""
from __future__ import annotations

import argparse
from itertools import combinations
import hashlib
import json
from pathlib import Path
import pickle

import numpy as np
from grid_map_msgs.msg import GridMap
from rclpy.serialization import deserialize_message


def sha(path):
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(2**20), b''):
            result.update(block)
    return result.hexdigest()


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def stamp(message):
    return message.header.stamp.sec * 10**9 + message.header.stamp.nanosec


def load(path):
    with path.open('rb') as stream:
        archive = pickle.load(stream)
    messages = [deserialize_message(data, GridMap) for data in archive['maps']]
    assert len(messages) == 208
    return archive['odometry'], messages


def compare(messages_a, messages_b, pair):
    frames, totals = [], {}
    for index, (a, b) in enumerate(zip(messages_a, messages_b, strict=True)):
        assert a.header == b.header and a.info == b.info, (pair, index, 'geometry/time')
        assert a.layers == b.layers == ['elevation', 'variance', 'observation_age']
        assert a.outer_start_index == b.outer_start_index and a.inner_start_index == b.inner_start_index
        fields = {}
        for name, first, second in zip(a.layers, a.data, b.data, strict=True):
            assert first.layout == second.layout
            x, y = np.asarray(first.data, np.float32), np.asarray(second.data, np.float32)
            assert x.shape == y.shape
            both = np.isfinite(x) & np.isfinite(y)
            differences = np.abs(x[both].astype(np.float64) - y[both].astype(np.float64))
            bits_x, bits_y = x.view(np.uint32), y.view(np.uint32)
            row = {'elements': int(x.size), 'finite_pairs': int(both.sum()),
                   'bit_differences': int(np.count_nonzero(bits_x != bits_y)),
                   'nan_location_differences': int(np.count_nonzero(np.isnan(x) != np.isnan(y))),
                   'finite_values_different': int(np.count_nonzero(x[both] != y[both])),
                   'max_abs': float(differences.max()) if differences.size else 0.,
                   'sum_abs': float(differences.sum())}
            fields[name] = row
            total = totals.setdefault(name, {key: 0 for key in row})
            for key, value in row.items():
                total[key] = max(total[key], value) if key == 'max_abs' else total[key] + value
        frames.append({'index': index, 'stamp_ns': stamp(a),
                       't_s': (stamp(a) - stamp(messages_a[0])) / 1e9, 'fields': fields})
    for total in totals.values():
        total['mean_abs_finite'] = total['sum_abs'] / total['finite_pairs'] if total['finite_pairs'] else 0.
    return {'pair': pair, 'frames': frames, 'aggregates': totals,
            'native_arrays_bit_identical': all(total['bit_differences'] == 0 for total in totals.values()),
            'headers_layout_geometry_and_stamps_identical': True}


def summarize_backend(folder, backend):
    declared = read(folder / 'SUMMARY.json')
    assert declared['backend'] == backend and declared['raw_scans'] == 415
    assert declared['maps_per_instance'] == 208 and declared['repetitions'] == 3
    archives = [folder / f'run_{index}/native_maps.pkl' for index in range(3)]
    odometry, messages = [], []
    for path in archives:
        odom, maps = load(path)
        odometry.append(odom)
        messages.append(maps)
    assert odometry[0] == odometry[1] == odometry[2], 'Source pose bytes changed across repetitions'
    pairs = [compare(messages[a], messages[b], [a, b]) for a, b in combinations(range(3), 2)]
    durations = [entry['integration_s'] * 1000 for row in declared['rows'][1:]
                 for entry in row['instances']]
    timing = {'samples': len(durations), 'first_scan_each_instance_excluded': True,
              'median_ms': float(np.median(durations)), 'p95_ms': float(np.percentile(durations, 95)),
              'max_ms': float(max(durations)),
              'scope': 'GPU-synchronized integration only; CPU copying/compression excluded, not live end-to-end latency'}
    summary = {'backend': backend, 'repetitions': 3, 'raw_scans': 415, 'maps_per_instance': 208,
               'summary_sha256': sha(folder / 'SUMMARY.json'),
               'native_archives_sha256': [sha(path) for path in archives],
               'all_internal_state_hashes_bit_identical': declared['all_internal_states_bit_identical'],
               'all_native_arrays_bit_identical': all(pair['native_arrays_bit_identical'] for pair in pairs),
               'different_internal_scan_indices': declared['different_scan_indices'],
               'changed_layer_step_counts': declared['changed_layer_step_counts'],
               'pairs': pairs, 'timing': timing,
               'source_sha256': declared['source_sha256'], 'mask': declared['mask'],
               'source_duration_s': declared['source_duration_s']}
    return summary, messages[0], odometry[0], declared


def plot(output, result, source_rows):
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt, font_manager
    font = Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus'] = False
    fig, axes = plt.subplots(2, 3, figsize=(17, 9), dpi=150)
    for backend, label, color in [('legacy', '旧融合', '#c47730'),
                                  ('deterministic', '确定性融合', '#277eaa')]:
        values = result['backends'][backend]
        pairs = values['pairs']
        times = [row['t_s'] for row in pairs[0]['frames']]
        for axis, field, metric, title, ylabel in [
            (axes[0, 0], 'elevation', 'max_abs', '三实例之间最大高程差', '绝对差 / m'),
            (axes[0, 1], 'observation_age', 'max_abs', '观测年龄差（源时间）', '绝对差 / s'),
            (axes[0, 2], 'elevation', 'nan_location_differences', '缺测位置不一致', '格数 / 帧')]:
            series = np.max([[row['fields'][field][metric] for row in pair['frames']]
                             for pair in pairs], axis=0)
            axis.plot(times, series, color=color, label=label)
            axis.set(title=title, xlabel='原录包时间 / s', ylabel=ylabel)
        axes[1, 0].bar(label, values['timing']['median_ms'], color=color)
        axes[1, 0].scatter([label], [values['timing']['p95_ms']], color=color, marker='_', s=180)
        hashes = set(values['different_internal_scan_indices'])
        diff = [int(row['scan'] in hashes) for row in source_rows[backend]]
        origin = source_rows[backend][0]['stamp_ns']
        raw_times = [(row['stamp_ns'] - origin) / 1e9 for row in source_rows[backend]]
        axes[1, 1].plot(raw_times, np.cumsum(diff), color=color, label=label)
    axes[1, 0].set(title='离线整合耗时：柱=中位，短线=P95', ylabel='GPU同步整合 / ms')
    axes[1, 1].set(title='内部任意状态不一致的累计扫描数', xlabel='原录包时间 / s', ylabel='扫描数')
    reference = source_rows['deterministic']
    origin = reference[0]['stamp_ns']
    axes[1, 2].plot([(row['stamp_ns']-origin)/1e9 for row in reference],
                    [row['kept_points'] for row in reference], color='#727d88')
    axes[1, 2].set(title='六实例均使用同一过滤后点集', xlabel='原录包时间 / s', ylabel='点数 / 扫描')
    for axis in axes.flat:
        axis.grid(alpha=.2)
    for axis in [*axes[0], axes[1, 1]]:
        axis.legend()
    fig.suptitle('相同415扫描、三次独立实例：旧CuPy与确定性CuPy重复性对照', fontsize=18)
    fig.text(.5, .012, '上排每帧取三种实例配对的最大差；不比较CDR对齐填充。耗时不含CPU诊断复制/压缩，不等于实车端到端频率。',
             ha='center', fontsize=11)
    fig.tight_layout(rect=[0, .04, 1, .95])
    fig.savefig(output / 'mapping_repeatability.png')
    plt.close(fig)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--data', required=True, type=Path)
    cli.add_argument('--output', required=True, type=Path)
    args = cli.parse_args()
    summaries, representatives, poses, rows = {}, {}, {}, {}
    for backend in ['legacy', 'deterministic']:
        summary, maps, odometry, declared = summarize_backend(args.data / backend, backend)
        summaries[backend], representatives[backend], poses[backend], rows[backend] = summary, maps, odometry, declared['rows']
    assert summaries['legacy']['source_sha256'] == summaries['deterministic']['source_sha256']
    assert summaries['legacy']['mask'] == summaries['deterministic']['mask'] == 'after'
    assert poses['legacy'] == poses['deterministic']
    for old, new in zip(rows['legacy'], rows['deterministic'], strict=True):
        for key in ['scan', 'stamp_ns', 'raw_cdr_sha256', 'mask_sha256', 'kept_points']:
            assert old[key] == new[key], (key, old['scan'])
    stable = summaries['deterministic']
    assert stable['all_internal_state_hashes_bit_identical'], 'Deterministic internal states diverged'
    assert stable['all_native_arrays_bit_identical'], 'Deterministic published fields diverged'
    representative = compare(representatives['legacy'], representatives['deterministic'], ['legacy_0', 'deterministic_0'])
    result = {'scope': 'Identical recorded inputs, three fresh instances per backend; no vehicle motion',
              'source_stamps_poses_mask_and_raw_bytes_paired': True, 'backends': summaries,
              'representative_treatment_comparison': representative,
              'limits': ['Three repetitions establish this input/hardware result, not universal determinism across GPUs.',
                         'Candidate also restores FP32 geometry and ordered FP64 reductions; not solely a thread ordering change.',
                         'Native map repeatability is separate from HT calibration and route feasibility.']}
    args.output.mkdir(parents=True, exist_ok=False)
    write(args.output / 'RESULTS.json', result)
    plot(args.output, result, rows)
    brief = {backend: {'exact_internal': value['all_internal_state_hashes_bit_identical'],
                       'exact_native': value['all_native_arrays_bit_identical'],
                       'max_pairwise_elevation_difference_m': max(pair['aggregates']['elevation']['max_abs'] for pair in value['pairs']),
                       'timing': value['timing']}
             for backend, value in summaries.items()}
    write(args.output / 'BRIEF.json', brief)
    print(json.dumps(brief, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
