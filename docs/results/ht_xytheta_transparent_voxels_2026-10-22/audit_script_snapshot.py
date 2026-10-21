#!/usr/bin/env python3
"""Read recorded eight-heading fields directly and compare them without inference."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
import numpy as np
import rosbag2_py
from grid_map_msgs.msg import GridMap
from rclpy.serialization import deserialize_message


def plot_snapshot(best, output):
    font = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    font_manager.fontManager.addfont(font); plt.rcParams['font.family'] = font_manager.FontProperties(fname=font).get_name()
    plt.rcParams['axes.unicode_minus'] = False
    nx, ny = best['valid'].shape; res = best['resolution']
    x = best['center_x'] + np.linspace(-nx / 2, nx / 2, nx + 1) * res
    y = best['center_y'] + np.linspace(-ny / 2, ny / 2, ny + 1) * res
    fig, axes = plt.subplots(3, 3, figsize=(17, 15), layout='constrained')
    cmap = plt.get_cmap('RdYlGn').copy(); cmap.set_bad('#555c65')
    difference_cmap = plt.get_cmap('magma').copy(); difference_cmap.set_bad('#555c65')
    for k, ax in enumerate(axes.flat):
        field = best['scores'][k] if k < 8 else np.ptp(best['scores'], axis=0)
        field = np.ma.array(field, mask=~best['valid'])[::-1, ::-1].T
        m = ax.pcolormesh(x, y, field, shading='flat', cmap=cmap if k < 8 else difference_cmap,
                          vmin=0, vmax=1, edgecolors=(.05, .05, .05, .13), linewidth=.05, rasterized=True)
        ax.set(title=f'θ = {k * 45}°' if k < 8 else '同一格跨方向差：max(T) − min(T)', xlabel='地图 X / m', ylabel='地图 Y / m')
        ax.set_aspect('equal'); bar = fig.colorbar(m, ax=ax, fraction=.046, pad=.02)
        bar.set_label('已发布HT分数' if k < 8 else '方向差值')
    fig.suptitle(f"Campus 同一帧八方向 HT 原始栅格，t={best['time_s']:.2f}s\n同一地形、同一 XY 范围、同一 0～1 色标；灰色为无效，未插值、未逐层归一化", fontsize=16)
    fig.savefig(output / 'eight_directions.png', dpi=180)
    fig.savefig(output / 'eight_directions.pdf'); plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--trial', required=True, type=Path)
    ap.add_argument('--output', required=True, type=Path)
    ap.add_argument('--time', type=float, default=30.)
    ap.add_argument('--plot-only', action='store_true', help='Replot the existing snapshot without rereading or changing statistics.')
    a = ap.parse_args()
    if a.plot_only:
        with np.load(a.output / 'snapshot.npz') as saved:
            plot_snapshot({key: saved[key] for key in saved.files}, a.output)
        return
    if a.output.exists():
        raise RuntimeError('Use a new output directory; existing evidence is not overwritten')
    a.output.mkdir(parents=True)
    bag = a.trial / 'evidence_bag'
    origin = json.loads((a.trial / 'current/measurement_started.json').read_text())['wall_time']
    def raw_state():
        return {p.name: dict(bytes=p.stat().st_size, mtime_ns=p.stat().st_mtime_ns)
                for p in sorted(bag.glob('*.mcap'))}
    before = raw_state()
    reader = rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(bag), storage_id='mcap'), rosbag2_py.ConverterOptions('', ''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local']))
    rows = []; best = None; nearest = float('inf')
    pair_abs = np.zeros((8, 8)); pair_max = np.zeros((8, 8)); cell_count = 0; range_sum = 0.; distinct = 0
    occupied_count = 0; occupied_nonzero = 0
    while reader.has_next():
        _, raw, ns = reader.read_next(); t = ns / 1e9 - origin
        if not 0 <= t < 600:
            continue
        msg = deserialize_message(raw, GridMap)
        nx = round(msg.info.length_x / msg.info.resolution); ny = round(msg.info.length_y / msg.info.resolution)
        def layer(name):
            values = np.asarray(msg.data[msg.layers.index(name)].data, np.float32).reshape((nx, ny), order='F')
            return np.roll(values, (-msg.outer_start_index, -msg.inner_start_index), (0, 1))
        p = np.stack([layer('ht_dir_' + str(k)) for k in range(8)])
        valid = (layer('ht_valid') > .5) & np.isfinite(p).all(axis=0)
        obstacle = (layer('ht_obstacle') > .5) & valid if 'ht_obstacle' in msg.layers else np.zeros_like(valid)
        values = p[:, valid]; count = values.shape[1]
        if not count:
            continue
        spread = np.ptp(values, axis=0)
        for k in range(8):
            diffs = np.abs(values - values[k])
            pair_abs[k] += diffs.sum(axis=1, dtype=np.float64)
            pair_max[k] = np.maximum(pair_max[k], diffs.max(axis=1))
        cell_count += count; range_sum += float(spread.sum(dtype=np.float64)); distinct += int((spread > .05).sum())
        occupied_count += int(obstacle.sum()); occupied_nonzero += int(np.any(p[:, obstacle] != 0, axis=0).sum())
        rows.append(dict(time_s=t, valid_cells=count, mean_direction_range=float(spread.mean()),
                         p95_direction_range=float(np.quantile(spread, .95)), max_direction_range=float(spread.max()),
                         fraction_range_over_005=float(np.mean(spread > .05)),
                         all_eight_equal=bool(np.all(spread <= 1e-7)), mae_0_vs_180=float(np.abs(values[0] - values[4]).mean())))
        if abs(t - a.time) < nearest:
            nearest = abs(t - a.time)
            best = dict(time_s=t, scores=p.copy(), valid=valid.copy(), obstacle=obstacle.copy(),
                        resolution=msg.info.resolution, center_x=msg.info.pose.position.x, center_y=msg.info.pose.position.y,
                        source_stamp=msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9,
                        frame_id=msg.header.frame_id)
    if not rows:
        raise RuntimeError('No valid recorded HT maps')
    after = raw_state()
    summary = dict(map_count=len(rows), all_eight_equal_map_count=sum(r['all_eight_equal'] for r in rows),
                   valid_cell_frame_count=cell_count, pooled_mean_direction_range=range_sum / cell_count,
                   pooled_fraction_direction_range_over_005=distinct / cell_count,
                   pooled_pairwise_mean_absolute_difference=(pair_abs / cell_count).tolist(),
                   pairwise_max_absolute_difference=pair_max.tolist(),
                   occupied_cell_frames=occupied_count, occupied_cells_with_nonzero_output=occupied_nonzero,
                   snapshot_time_s=best['time_s'], snapshot_target_time_s=a.time,
                   raw_files_unchanged=before == after, raw_files=before,
                   metadata_sha256=hashlib.file_digest((bag / 'metadata.yaml').open('rb'), 'sha256').hexdigest(),
                   scope='Recorded final scores, common valid mask. Nonidentical channels do not prove physical accuracy or directional calibration.')
    (a.output / 'audit.json').write_text(json.dumps(summary, indent=2) + '\n')
    with (a.output / 'per_map.csv').open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
    np.savez_compressed(a.output / 'snapshot.npz', **best)

    plot_snapshot(best, a.output)
    print(json.dumps({k: summary[k] for k in ('map_count', 'all_eight_equal_map_count', 'pooled_mean_direction_range',
          'pooled_fraction_direction_range_over_005', 'occupied_cells_with_nonzero_output', 'raw_files_unchanged')}, indent=2))


if __name__ == '__main__':
    main()
