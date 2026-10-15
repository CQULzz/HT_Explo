#!/usr/bin/env python3
"""Compare two offline elevation/HT replays without equating unknown to free.

The old replay contains a reflected CuPy->GridMap coordinate convention and a
faulty history lattice. Its published world labels therefore cannot identify
the same terrain cell as the corrected replay. Matched times and native-map
statistics are useful input diagnostics, not an exploration performance test
or a physical cell-by-cell truth comparison.
"""
from __future__ import annotations

import argparse
import csv
from functools import lru_cache
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'axes.unicode_minus': False,
                     'font.size': 10})

COORDINATE_CAVEAT = (
    '旧数据存在 CuPy→GridMap 双轴镜像和历史索引错误；旧图保留其发布坐标，'
    '不能把新旧相同 XY 格子当作同一块真实地面。比较仅为同一车辆记录的离线输入诊断。')
CHANNEL_CAVEAT = ('HT 八通道的车辆方向标定尚未完成；八通道平均仅用于诊断，'
                   '不能替代实际 XYθ 方向硬约束。')
MARKERS = [
    {'name': '真实立柱', 'key': 'true_mesh_column', 'xy': [3.066563, 9.768132], 't_s': 25.,
     'meaning': 'Garage 网格的 0.5×0.5 m 立柱；修正后的世界坐标可用于几何核对。'},
    {'name': '旧报告的异常峰格', 'key': 'legacy_reported_peak',
     'xy': [12.383040935672513, 74.80994152046783], 't_s': 167.,
     'meaning': '旧图标注的异常峰位置；旧坐标有镜像错误，不能当作原始回波的真实位置。'},
    {'name': '旧报告的跨楼层格', 'key': 'legacy_reported_cross_floor',
     'xy': [3.2953216374269005, 54.26023391812865], 't_s': 595.,
     'meaning': '旧历史图标注的跨楼层平均例子；旧图与新图相同标注 XY 不代表同一回波。'},
]


def finite_number(value):
    value = float(value)
    return value if np.isfinite(value) else None


class Replay:
    def __init__(self, folder):
        self.folder = Path(folder).resolve()
        self.origin = json.loads((self.folder/'original/measurement_started.json').read_text())['wall_time']
        self.all_frames = json.loads((self.folder/'snapshots/index.json').read_text())['frames']
        self.frames = []
        self.skipped = []
        for item in self.all_frames:
            with np.load(self.folder/'snapshots'/item['file']) as data:
                history_skew = abs(float(data['history_stamp'])-float(data['ht_stamp']))
                geometry_skew = float(np.max(abs(data['history_geometry']-data['ht_geometry'])))
            if history_skew > 1e-5 or geometry_skew > 1e-6:
                self.skipped.append({'file': item['file'], 'history_skew_s': history_skew,
                                     'geometry_max_skew': geometry_skew})
                continue
            self.frames.append(item)
        self.times = np.array([float(f['ht_stamp'])-self.origin for f in self.frames])
        if not len(self.frames):
            raise RuntimeError(f'No exactly synchronized history/HT snapshots in {self.folder}')
        rows = list(csv.DictReader((self.folder/'original/timeseries.csv').open()))
        self.pose_times = np.array([float(row['t_s']) for row in rows])
        self.pose_xy = np.array([[float(row['x_m']), float(row['y_m'])] for row in rows])

    @lru_cache(maxsize=4)
    def load(self, index):
        with np.load(self.folder/'snapshots'/self.frames[index]['file']) as data:
            names = ['history_elevation', 'history_variance', 'history_geometry',
                     'ht_geometry', 'ht_ht_valid'] + [f'ht_ht_dir_{k}' for k in range(8)]
            names += [name for name in ['history_elevation_raw', 'history_input_valid',
                                         'history_rejected'] if name in data]
            return {name: data[name].copy() for name in names}

    def nearest(self, time_s):
        index = int(np.argmin(abs(self.times-time_s)))
        return index, float(self.times[index])

    def robot_at(self, time_s):
        return np.array([np.interp(time_s, self.pose_times, self.pose_xy[:, axis])
                         for axis in range(2)])

    def metadata(self):
        formal = self.times[self.times >= 0]
        stats_file = self.folder/'cupy_processing_stats.json'
        processing = json.loads(stats_file.read_text()) if stats_file.exists() else None
        return {'folder': str(self.folder), 'snapshot_count': len(self.all_frames),
                'exact_history_ht_snapshot_count': len(self.frames),
                'skipped_unsynchronized': self.skipped,
                'time_min_s': float(self.times.min()), 'time_max_s': float(self.times.max()),
                'formal_snapshot_gap_max_s': float(np.max(np.diff(formal))) if len(formal)>1 else None,
                'processing': processing}


def fields(data):
    probabilities = np.stack([data[f'ht_ht_dir_{k}'] for k in range(8)])
    valid = (data['ht_ht_valid'] >= .5) & np.all(np.isfinite(probabilities), axis=0)
    mean = np.mean(np.where(np.isfinite(probabilities), probabilities, 0), axis=0)
    mean[~valid] = np.nan
    return probabilities, valid, mean


def state_metrics(data, selection=None):
    probabilities, valid, mean = fields(data)
    selected = np.ones(valid.shape, bool) if selection is None else np.asarray(selection, bool)
    total = int(selected.sum())
    if total == 0:
        return {'cells': 0, 'valid_fraction': None, 'unknown_fraction': None,
                'mean8_low_area_fraction': None, 'mean8_high_area_fraction': None}
    valid_selected = selected & valid
    low = valid_selected & (mean < .5)
    high = valid_selected & (mean >= .5)
    count = int(valid_selected.sum())
    return {
        'cells': total, 'valid_cells': count, 'unknown_cells': total-count,
        'mean8_low_cells': int(low.sum()), 'mean8_high_cells': int(high.sum()),
        'valid_fraction': count/total, 'unknown_fraction': (total-count)/total,
        'mean8_low_area_fraction': float(low.sum()/total),
        'mean8_high_area_fraction': float(high.sum()/total),
        'mean8_low_among_valid_fraction': float(low.sum()/count) if count else None,
        'all8_pass_area_fraction': float((valid_selected & np.all(probabilities >= .5, axis=0)).sum()/total),
        'any_channel_low_area_fraction': float((valid_selected & np.any(probabilities < .5, axis=0)).sum()/total),
        'mean8_probability_median': finite_number(np.median(mean[valid_selected])) if count else None,
    }


def coordinate_grids(shape, geometry):
    cx, cy, resolution = geometry
    return np.meshgrid(cx + ((shape[0]-1)/2-np.arange(shape[0]))*resolution,
                       cy + ((shape[1]-1)/2-np.arange(shape[1]))*resolution, indexing='ij')


def native_plane(ax, values, geometry, cmap, limits):
    cx, cy, resolution = geometry
    nx, ny = values.shape
    return ax.imshow(values[::-1, ::-1].T, origin='lower', interpolation='nearest',
                     extent=[cx-nx*resolution/2, cx+nx*resolution/2,
                             cy-ny*resolution/2, cy+ny*resolution/2],
                     cmap=cmap, vmin=limits[0], vmax=limits[1], aspect='equal')


def color_map(name):
    cmap = plt.get_cmap(name).copy()
    cmap.set_bad('#bfc3c6')
    return cmap


def pair_at(before, after, target, max_pair_skew, max_target_skew=3.):
    left, left_t = before.nearest(target)
    right, right_t = after.nearest(target)
    if abs(left_t-right_t)>max_pair_skew or max(abs(left_t-target), abs(right_t-target))>max_target_skew:
        return None
    return {'target_s': float(target), 'before_index': left, 'after_index': right,
            'before_t_s': left_t, 'after_t_s': right_t, 'pair_skew_s': abs(left_t-right_t)}


def comparison_maps(before, after, targets, max_skew, output):
    selections = [pair_at(before, after, target, max_skew) for target in targets]
    for kind, filename in [('ht', 'ht_native_grid_before_after.png'),
                           ('elevation', 'elevation_native_grid_before_after.png')]:
        fig, axes = plt.subplots(2, len(targets), figsize=(6*len(targets), 11),
                                 constrained_layout=True, squeeze=False)
        for column, (target, pair) in enumerate(zip(targets, selections)):
            if pair is None:
                for row in range(2):
                    axes[row, column].text(.5, .5, '没有满足时间对齐要求的地图', ha='center',
                                           va='center', transform=axes[row, column].transAxes)
                    axes[row, column].axis('off')
                continue
            for row, (replay, key, title) in enumerate([(before, 'before', '修改前（旧发布坐标）'),
                                                       (after, 'after', '修改后（修正世界坐标）')]):
                data = replay.load(pair[f'{key}_index'])
                if kind == 'ht':
                    values = fields(data)[2]
                    geometry = data['ht_geometry']
                    cmap, limits = color_map('RdYlGn'), (0, 1)
                else:
                    values, geometry = data['history_elevation'], data['history_geometry']
                    cmap = color_map('terrain')
                    limits = (-.05, 1.8) if target < 400 else (-.1, 4.5)
                ax = axes[row, column]
                image = native_plane(ax, values, geometry, cmap, limits)
                ax.plot(*replay.robot_at(pair[f'{key}_t_s']), 'b+', ms=10, mew=2)
                metrics = state_metrics(data)
                stats = (f"低概率 {100*metrics['mean8_low_area_fraction']:.1f}% | "
                         f"高概率 {100*metrics['mean8_high_area_fraction']:.1f}% | "
                         f"未知 {100*metrics['unknown_fraction']:.1f}%")
                ax.set(title=f"{title}，t={pair[f'{key}_t_s']:.3f}s\n{stats}",
                       xlabel='发布坐标 X (m)', ylabel='发布坐标 Y (m)')
                fig.colorbar(image, ax=ax, shrink=.70,
                             label='八通道平均概率（灰色=未知）' if kind=='ht' else '高程 (m)，超色阶饱和显示')
        fig.suptitle(('HT 原生栅格：逐格最近邻显示；蓝十字是同一 TARE 记录中的车辆\n'
                      if kind=='ht' else '历史局部高程：修改前后同列使用相同高程色阶\n') +
                     '旧坐标镜像及索引错误使两图不能逐格当作同一真实地形；未重新执行探索', fontsize=13)
        fig.savefig(output/filename, dpi=210)
        plt.close(fig)
    return selections


def region_probe(replay, index, xy, radius_m=.30):
    data = replay.load(index)
    hx, hy = coordinate_grids(data['history_elevation'].shape, data['history_geometry'])
    tx, ty = coordinate_grids(data['ht_ht_valid'].shape, data['ht_geometry'])
    history_region = np.hypot(hx-xy[0], hy-xy[1]) <= radius_m
    ht_region = np.hypot(tx-xy[0], ty-xy[1]) <= radius_m
    z = data['history_elevation'][history_region]
    known_z = z[np.isfinite(z)]
    result = {'t_s': float(replay.times[index]), 'radius_m': radius_m,
              'history_cells_in_region': int(history_region.sum()),
              'observed_height_cells': int(known_z.size),
              'height_median_m': finite_number(np.median(known_z)) if known_z.size else None,
              'height_min_m': finite_number(np.min(known_z)) if known_z.size else None,
              'height_max_m': finite_number(np.max(known_z)) if known_z.size else None,
              'ht_state': state_metrics(data, ht_region)}
    cx, cy, resolution = data['history_geometry']
    nx, ny = data['history_elevation'].shape
    row = int(np.floor((nx-1)/2-(xy[0]-cx)/resolution+.5))
    col = int(np.floor((ny-1)/2-(xy[1]-cy)/resolution+.5))
    inside = 0 <= row < nx and 0 <= col < ny
    result['center_cell_height_m'] = finite_number(data['history_elevation'][row, col]) if inside else None
    for name in ['history_rejected', 'history_input_valid']:
        if name in data and inside:
            result[name.replace('history_', 'center_cell_')] = finite_number(data[name][row, col])
    if 'history_elevation_raw' in data and inside:
        result['center_cell_raw_height_m'] = finite_number(data['history_elevation_raw'][row, col])
    return result


def marker_maps(before, after, max_skew, output):
    results = []
    fig, axes = plt.subplots(len(MARKERS), 4, figsize=(20, 15), constrained_layout=True)
    for row, marker in enumerate(MARKERS):
        pair = pair_at(before, after, marker['t_s'], max_skew)
        entry = dict(marker)
        entry['pair'] = pair
        results.append(entry)
        if pair is None:
            for ax in axes[row]:
                ax.text(.5, .5, f"{marker['name']}：没有同期地图", ha='center', va='center', transform=ax.transAxes)
                ax.axis('off')
            continue
        for column, (replay, key, title) in enumerate([(before, 'before', '修改前'),
                                                     (after, 'after', '修改后')]):
            data = replay.load(pair[f'{key}_index'])
            entry[key] = region_probe(replay, pair[f'{key}_index'], marker['xy'])
            for offset, kind in [(0, 'height'), (2, 'probability')]:
                ax = axes[row, column+offset]
                if kind == 'height':
                    values, geometry = data['history_elevation'], data['history_geometry']
                    limits = (-.05, 1.8) if marker['t_s']<400 else (-.1, 4.5)
                    cmap = color_map('terrain')
                else:
                    values, geometry = fields(data)[2], data['ht_geometry']
                    cmap, limits = color_map('RdYlGn'), (0, 1)
                image = native_plane(ax, values, geometry, cmap, limits)
                x, y = marker['xy']
                ax.plot(x, y, 'm+', ms=10, mew=2)
                ax.set(xlim=(x-1.5, x+1.5), ylim=(y-1.5, y+1.5),
                       title=f"{marker['name']}：{title}，t={pair[f'{key}_t_s']:.2f}s\n"
                             + ('高程' if kind=='height' else '八通道平均；灰色=未知'),
                       xlabel='发布坐标 X (m)', ylabel='发布坐标 Y (m)')
                fig.colorbar(image, ax=ax, shrink=.65)
    fig.suptitle('标注坐标周围 3×3 m 原生栅格；紫十字为标注点\n'
                 '旧镜像坐标仅作诊断索引：旧报告峰值/跨楼层标注不能当作已配准的同一物理点', fontsize=13)
    fig.savefig(output/'annotated_regions_before_after.png', dpi=210)
    plt.close(fig)
    return results


def history_modes(folder):
    path = folder/'global_historical_elevation.npz'
    if not path.exists():
        return None
    with np.load(path) as data:
        z = data['elevation_modes'] if 'elevation_modes' in data else data['elevation'][:, None]
        finite = np.isfinite(z)
        count = finite.sum(axis=1)
        largest = np.max(np.where(finite, z, -np.inf), axis=1)
        smallest = np.min(np.where(finite, z, np.inf), axis=1)
        return {'schema_version': int(data['schema_version']) if 'schema_version' in data else 1,
                'tiles': int(z.shape[0]), 'observed_xy_cells': int((count>0).sum()),
                'observed_height_modes': int(finite.sum()),
                'multi_surface_xy_cells': int((count>1).sum()),
                'height_separation_over_1_5m_xy_cells': int(((count>1)&(largest-smallest>1.5)).sum())}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('before', type=Path)
    ap.add_argument('after', type=Path)
    ap.add_argument('--output', type=Path)
    ap.add_argument('--target-times', type=float, nargs='+', default=[25., 167., 595.])
    ap.add_argument('--max-pair-skew-s', type=float, default=1.)
    args = ap.parse_args()
    before, after = Replay(args.before), Replay(args.after)
    output = (args.output or after.folder/'surface_fix_comparison').resolve()
    output.mkdir(parents=True, exist_ok=True)
    start = max(0., float(before.times.min()), float(after.times.min()))
    finish = min(float(before.times.max()), float(after.times.max()))
    matched = []
    for target in np.arange(np.ceil(start), np.floor(finish)+1.):
        pair = pair_at(before, after, target, args.max_pair_skew_s, max_target_skew=1.)
        if pair is None:
            continue
        pair['before'] = state_metrics(before.load(pair['before_index']))
        pair['after'] = state_metrics(after.load(pair['after_index']))
        matched.append(pair)
    selected = comparison_maps(before, after, args.target_times, args.max_pair_skew_s, output)
    markers = marker_maps(before, after, args.max_pair_skew_s, output)
    metric_keys = ['unknown_fraction', 'mean8_low_area_fraction', 'mean8_high_area_fraction']
    summary = {'matched_seconds': len(matched), 'before': {}, 'after': {}}
    for key in ['before', 'after']:
        summary[key] = {metric: float(np.mean([row[key][metric] for row in matched])) if matched else None
                        for metric in metric_keys}
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), constrained_layout=True)
    for ax, key, title in [(axes[0], 'before', '修改前'), (axes[1], 'after', '修改后')]:
        if matched:
            ax.stackplot([row['target_s'] for row in matched],
                         [row[key]['mean8_low_area_fraction'] for row in matched],
                         [row[key]['mean8_high_area_fraction'] for row in matched],
                         [row[key]['unknown_fraction'] for row in matched],
                         colors=['#c64737', '#419956', '#bfc3c6'],
                         labels=['有效且八通道均值<0.5', '有效且八通道均值≥0.5', '未知/不支持'])
        ax.set(title=title, ylabel='当前局部图全部栅格的面积比例', ylim=(0, 1), xlabel='原始实验时间 (s)')
        ax.grid(alpha=.15)
        ax.legend(loc='upper right')
    fig.suptitle('同一车辆记录、按实验秒匹配：红 / 绿 / 未知必须分开统计\n'
                 '未知增加不算通行改善；输入坐标已修正，面积统计不代表逐格物理真值', fontsize=13)
    fig.savefig(output/'matched_time_state_fractions.png', dpi=180)
    plt.close(fig)
    payload = {'coordinate_caveat': COORDINATE_CAVEAT, 'channel_caveat': CHANNEL_CAVEAT,
               'fraction_definition': '分母为当前 HT 图全部栅格；红+绿+未知=1；没有将 NaN 算作绿色。',
               'before': before.metadata(), 'after': after.metadata(),
               'matched_time_summary': summary, 'matched_time_metrics': matched,
               'selected_pairs': selected, 'world_marker_probes': markers,
               'global_history_before': history_modes(before.folder),
               'global_history_after': history_modes(after.folder)}
    (output/'comparison_metrics.json').write_text(json.dumps(payload, ensure_ascii=False,
                                                               indent=2, allow_nan=False)+'\n')
    def pct(value):
        return f'{100*value:.2f}%' if value is not None else '无同期样本'
    report = [
        '# 高程及 HT 修正：同一原始记录的离线对照', '', COORDINATE_CAVEAT, '', CHANNEL_CAVEAT, '',
        '这两次回放复用原版 TARE 的同一次车辆行驶。车辆轨迹、探索里程和探索收益不会因离线地图处理而改变；本对照没有验证修改后 HT 控制车辆的探索效果。', '',
        f"严格同期的历史图/HT 快照：修改前 {len(before.frames)}/{len(before.all_frames)}，修改后 {len(after.frames)}/{len(after.all_frames)}。不一致快照已排除。按整数实验秒匹配 {len(matched)} 组，允许两次快照最大相差 {args.max_pair_skew_s:.2f} s。", '',
        '| 当前图面积比例，按匹配秒平均 | 修改前 | 修改后 |', '|---|---:|---:|',
        f"| 有效且八通道均值 <0.5 | {pct(summary['before']['mean8_low_area_fraction'])} | {pct(summary['after']['mean8_low_area_fraction'])} |",
        f"| 有效且八通道均值 ≥0.5 | {pct(summary['before']['mean8_high_area_fraction'])} | {pct(summary['after']['mean8_high_area_fraction'])} |",
        f"| 未知/不支持 | {pct(summary['before']['unknown_fraction'])} | {pct(summary['after']['unknown_fraction'])} |", '',
        '三项分母均为全部 HT 栅格，合计 100%。未知增多不能说成红区得到修复；有效区域减少也会改变“有效区域内的红色比例”，所以主表采用总面积分母。', '',
        '图采用原生栅格、最近邻显示。概率固定 0–1；灰色表示未知。高程每列的修改前后使用相同色阶，超色阶值饱和显示。', '',
        '- [六张 HT 原生栅格](ht_native_grid_before_after.png)',
        '- [六张高程原生栅格](elevation_native_grid_before_after.png)',
        '- [红、绿、未知随时间](matched_time_state_fractions.png)',
        '- [立柱及旧报告标注点周围地图](annotated_regions_before_after.png)',
        '- [全部指标及时间对齐记录](comparison_metrics.json)', '',
        '真实立柱世界中心为 (3.066563, 9.768132) m。旧报告的异常峰和跨楼层点作为旧发布坐标保留；其新旧地图读数不能证明同一物理回波的高度得到修正。跨楼层保真应结合新历史图的分层数、当前车辆地面参考和同一时刻真实点云确认。', '',
    ]
    (output/'REPORT.md').write_text('\n'.join(report))
    print(json.dumps({'output': str(output), 'summary': summary}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
