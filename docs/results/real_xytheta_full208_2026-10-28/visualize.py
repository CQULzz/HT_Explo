#!/usr/bin/env python3
"""Plot frozen C++ route queries; no vehicle, controller or map inference is run.

Example (after sourcing scripts/source_real_scout.sh)::
  python3 docs/results/real_xytheta_full208_2026-10-28/visualize.py \
    --data /path/to/new_round --maps /path/to/208/maps --output /path/to/plots

The recorded group keeps each recorded start yaw and varies only the goal.
Counterfactual heading probes change start yaw and are never counted as drives.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tools/ht_cupy_bridge'))
import replay_real_archive as replay

RECORDED = re.compile(r'^recorded_(frame_\d+)_goal_(\d+)deg$')
COUNTERFACTUAL = re.compile(r'^counterfactual_heading_(frame_\d+)_yaw_(\d+)deg$')
GROUPS = ('recorded', 'counterfactual_heading', 'synthetic')
GROUP_NAMES = ('记录位姿/固定目标', '反事实车头探针', '合成对照')
VARIANTS = ('before', 'after')
VARIANT_NAMES = ('修改前', '修改后')
COLORS = ('#537fa0', '#e39740')


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')


def finite(value):
    v = float(value)
    return v if math.isfinite(v) else None


def group(label):
    if RECORDED.fullmatch(label):
        return 'recorded'
    if COUNTERFACTUAL.fullmatch(label):
        return 'counterfactual_heading'
    if label.startswith('synthetic_'):
        return 'synthetic'
    raise ValueError(f'Unknown query group: {label}')


def load_results(data):
    results = {v: json.loads((data / f'{v}.json').read_text()) for v in VARIANTS}
    if results['before']['parameters'] != results['after']['parameters']:
        raise ValueError('Compared parameters differ')
    lookups = {}
    for variant, result in results.items():
        rows = result['queries']
        lookup = {row['label']: row for row in rows}
        if len(lookup) != len(rows):
            raise ValueError(f'Duplicate labels in {variant}')
        for row in rows:
            group(row['label'])
            if row.get('error'):
                raise ValueError(f'Runner error must not be silently plotted: {row}')
            if row.get('reached') and not (row.get('all_segments_permitted') and
                                           row.get('independent_recheck_passed')):
                raise ValueError(f'Unchecked successful route: {row["label"]}')
        lookups[variant] = lookup
    if lookups['before'].keys() != lookups['after'].keys():
        raise ValueError('Compared labels differ')
    for label, old in lookups['before'].items():
        new = lookups['after'][label]
        for key in ('map_sha256', 'start', 'goal', 'map_stamp_ns'):
            if old[key] != new[key]:
                raise ValueError(f'Compared input differs: {label}: {key}')
    return results, lookups


def extract_frames(meta, maps):
    """Raw map diagnostics, deliberately separate from production poseSupport."""
    items = [x for x in meta['maps'] if x.get('kind', 'recorded') == 'recorded'
             and re.fullmatch(r'frame_\d+', x['label'])]
    items.sort(key=lambda x: int(x['label'].split('_')[-1]))
    if len({x['label'] for x in items}) != len(items):
        raise ValueError('Duplicate recorded map metadata')
    first_stamp = min(int(x['stamp_ns']) for x in items)
    records = []
    for item in items:
        path = maps / (item['label'] + '.npz')
        source_sha = digest(path)
        expected = item.get('input_sha256') or item.get('input_npz_sha256')
        if expected and source_sha != expected:
            raise ValueError(f'NPZ digest mismatch: {path}')
        with np.load(path, allow_pickle=False) as z:
            probabilities = np.asarray(z['probabilities'], float)
            valid = np.asarray(z['ht_valid'], float)
            physical = np.asarray(z['ht_observation_valid'], float)
            obstacle = np.asarray(z['ht_obstacle'], float)
            start = np.asarray(item['start'], float)
            if not np.allclose(z['robot'], start, rtol=0, atol=1e-7):
                raise ValueError(f'NPZ recorded pose differs: {path}')
            n, m = valid.shape
            if probabilities.shape != (8, n, m):
                raise ValueError(f'Expected 8 directional channels: {path}')
            if physical.shape != valid.shape or obstacle.shape != valid.shape:
                raise ValueError(f'Physical layer shape mismatch: {path}')
            resolution = float(z['resolution'])
            center = np.asarray(z['center'], float)
            yaw = float(item.get('map_yaw', 0))
            c, s = math.cos(yaw), math.sin(yaw)
            delta = start[:2] - center
            local = np.array([c*delta[0]+s*delta[1], -s*delta[0]+c*delta[1]])
            row, col = np.floor(np.array([n/2, m/2])-local/resolution).astype(int)
            if not (0 <= row < n and 0 <= col < m):
                raise ValueError(f'Recorded pose outside map: {path}')
            ii, jj = np.indices((n, m))
            xx, yy = (n/2-ii-.5)*resolution, (m/2-jj-.5)*resolution
            wx, wy = center[0]+c*xx-s*yy, center[1]+s*xx+c*yy
            body = (wx-start[0])**2 + (wy-start[1])**2 <= .6**2
            observed = np.isfinite(physical) & (physical >= .5)
            context = np.isfinite(valid) & (valid >= .5)
            occupied = np.isfinite(obstacle) & (obstacle >= .5)
            channel = int(math.floor(((start[2]-yaw) % (2*math.pi))/(math.pi/4)+.5)) % 8
            p = probabilities[:, row, col]
            records.append(dict(
                label=item['label'], stamp_ns=int(item['stamp_ns']),
                t_s=(int(item['stamp_ns'])-first_stamp)/1e9,
                input_npz=str(path), input_npz_sha256=source_sha,
                input_cdr_sha256=item.get('sha256'), start=start.tolist(),
                map_yaw=yaw, center=center.tolist(), resolution_m=resolution,
                center_cell=[int(row), int(col)], center_direction_probabilities=[finite(x) for x in p],
                nearest_recorded_heading_channel=channel,
                nearest_recorded_heading_T=finite(p[channel]),
                center_max_T=finite(np.nanmax(p)) if np.isfinite(p).any() else None,
                center_context_valid=bool(context[row, col]),
                center_physical_valid=bool(observed[row, col]),
                center_obstacle=bool(occupied[row, col]),
                body_radius_m=.6, body_cells=int(body.sum()),
                body_physical_unknown=int((body & ~observed).sum()),
                body_context_invalid=int((body & ~context).sum()),
                body_obstacle=int((body & occupied).sum()),
                body_obstacle_layer_nonfinite=int((body & ~np.isfinite(obstacle)).sum()),
                body_obstacle_and_physical_unknown=int((body & occupied & ~observed).sum())))
    return records


def summarize(results, records):
    summary = {'scope': 'Frozen recorded HT fields and actual C++ fixed route queries; no new driving, '
                        'no TARE viewpoint selection, no exploration volume/distance comparison.',
               'recorded_maps': len(records), 'recorded_duration_s': records[-1]['t_s'],
               'independence_note': 'Each recorded pose is shared by eight goal directions; '
                                    '208 recorded poses / 1664 queries are not 1664 independent experiments.',
               'counterfactual_note': 'Start-yaw probes on a subset of frames only; not observed vehicle headings. '
                                      'A permitted hypothetical heading does not prove the vehicle can rotate '
                                      'there from its recorded configuration.',
               'physical_support_note': 'ht_observation_valid includes existing nearest-measurement support; '
                                        'it is not proof of a direct return in every cell.',
               'body_diagnostics_note': 'Circle cell counts are raw NPZ diagnostics, not a Python substitute '
                                        'for production obstacle/unknown footprint inflation and poseSupport.',
               'groups': {}}
    for variant in VARIANTS:
        summary['groups'][variant] = {}
        for kind in GROUPS:
            rows = [q for q in results[variant]['queries'] if group(q['label']) == kind]
            timing = np.asarray([q['search_wall_ms'] for q in rows], float)
            summary['groups'][variant][kind] = dict(
                queries=len(rows), reached=sum(bool(q.get('reached')) for q in rows),
                map_count=len({q['map_sha256'] for q in rows}),
                start_support=dict(Counter(q.get('start_support', 'MISSING') for q in rows)),
                termination=dict(Counter(q.get('termination', 'MISSING') for q in rows)),
                search_wall_ms_median=finite(np.median(timing)) if timing.size else None,
                search_wall_ms_p95=finite(np.percentile(timing, 95)) if timing.size else None,
                source_stamp_unchanged=all(q.get('source_stamp_unchanged', False) for q in rows))
    return summary


def main_support(lookup, labels):
    values = {}
    for label, row in lookup.items():
        match = RECORDED.fullmatch(label)
        if match:
            frame = match[1]
            state = row['start_support']
            if frame in values and values[frame] != state:
                raise ValueError(f'Goal direction changed the same start support: {label}')
            values[frame] = state
    if set(values) != set(labels):
        raise ValueError('Recorded result frames and input metadata differ')
    return [values[label] for label in labels]


def time_edges(t):
    if len(t) == 1:
        return np.array([t[0]-.5, t[0]+.5])
    return np.r_[t[0]-(t[1]-t[0])/2, (t[:-1]+t[1:])/2, t[-1]+(t[-1]-t[-2])/2]


def comparisons(out, results, summary, records, plt):
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), dpi=150)
    t = np.array([r['t_s'] for r in records])
    for offset, variant, name, color in zip([-.18, .18], VARIANTS, VARIANT_NAMES, COLORS):
        counts = summary['groups'][variant]
        heights = [counts[k]['reached'] for k in GROUPS]
        bars = axes[0, 0].bar(np.arange(3)+offset, heights, .36, label=name, color=color)
        for bar, kind in zip(bars, GROUPS):
            axes[0, 0].annotate(f'{counts[kind]["reached"]}/{counts[kind]["queries"]}',
                              (bar.get_x()+bar.get_width()/2, bar.get_height()),
                              xytext=(0, 4), textcoords='offset points', ha='center', fontsize=9)
    axes[0, 0].set(xticks=range(3), xticklabels=GROUP_NAMES, ylabel='成功查询数', title='固定查询成功率（严格分组）')
    axes[0, 0].set_ylim(0, max(3, axes[0, 0].get_ylim()[1]*1.18)); axes[0, 0].legend()
    states = sorted({q['start_support'] for v in VARIANTS for q in results[v]['queries']
                     if group(q['label']) == 'recorded'})
    for offset, variant, name, color in zip([-.18, .18], VARIANTS, VARIANT_NAMES, COLORS):
        counts = summary['groups'][variant]['recorded']['start_support']
        axes[0, 1].bar(np.arange(len(states))+offset, [counts.get(k, 0) for k in states], .36, label=name, color=color)
    axes[0, 1].set(xticks=range(len(states)), xticklabels=states, ylabel='查询数', title='真实记录位姿：生产起点检查')
    axes[0, 1].legend()
    axes[0, 2].plot(t, [r['center_max_T'] for r in records], label='中心八方向最大 T', color='#326b9c')
    axes[0, 2].plot(t, [r['nearest_recorded_heading_T'] for r in records], label='记录车头最近通道 T', color='#cf7b30')
    axes[0, 2].axhline(.5, color='#b43b3b', ls='--', label='0.5 硬门槛')
    axes[0, 2].set(ylabel='原始预测 T', ylim=(-.03, 1.03), title='概率维度；不能代替物理支撑检查')
    axes[0, 2].legend(fontsize=8)
    for key, name, color in [('body_physical_unknown', '物理支撑未知', '#708dba'),
                             ('body_context_invalid', 'HT 上下文无效', '#a579b7')]:
        axes[1, 0].plot(t, [r[key] for r in records], label=name, color=color)
    axes[1, 0].set(ylabel='0.6m 圈内格子数', title='缺测维度（两项可重叠）'); axes[1, 0].legend(fontsize=8)
    axes[1, 1].plot(t, [r['body_obstacle'] for r in records], label='ht_obstacle≥0.5', color='#b03e44')
    axes[1, 1].plot(t, [r['body_obstacle_layer_nonfinite'] for r in records], label='障碍层非有限值', color='#777777', ls=':')
    axes[1, 1].set(ylabel='0.6m 圈内格子数', title='障碍维度；不混作概率或缺测'); axes[1, 1].legend(fontsize=8)
    for variant, name, color in zip(VARIANTS, VARIANT_NAMES, COLORS):
        medians = []
        for frame in records:
            values = [q['search_wall_ms'] for q in results[variant]['queries']
                      if q['label'].startswith('recorded_'+frame['label']+'_goal_')]
            medians.append(float(np.median(values)))
        axes[1, 2].plot(t, medians, label=name, color=color)
    axes[1, 2].set(ylabel='8 个目标查询中位数 / ms', title='实际搜索耗时；起点拒绝不等于完成找路')
    axes[1, 2].legend(fontsize=8)
    for ax in axes.flat:
        ax.grid(alpha=.2)
    for ax in [axes[0, 2], *axes[1, :]]:
        ax.set_xlabel('记录时间 / s')
    fig.suptitle('最新冻结 XYθ 代码：全帧固定查询离线复测（没有新行驶或探索收益）', fontsize=16)
    fig.text(.5, .017, f'{len(records)} 个记录位姿，每个 8 个目标；查询数不是独立实车试验次数。'
             '反事实与合成组另列；0.6m 圈统计不替代 C++ poseSupport。', ha='center', fontsize=10)
    fig.tight_layout(rect=[0, .055, 1, .95]); fig.savefig(out/'comparisons.png'); plt.close(fig)


def direction_heatmap(out, records, plt):
    fig, axes = plt.subplots(2, 1, figsize=(15, 6.4), dpi=150,
                             gridspec_kw={'height_ratios': [5, 1]}, sharex=True)
    t = np.array([r['t_s'] for r in records]); edges = time_edges(t)
    values = np.asarray([r['center_direction_probabilities'] for r in records], float).T
    color = axes[0].pcolormesh(edges, np.arange(9)*45-22.5, values,
                               vmin=0, vmax=1, cmap='RdYlGn', shading='flat')
    axes[0].plot(t, [r['nearest_recorded_heading_channel']*45 for r in records],
                 '.', color='#1b60bd', ms=2.6, label='记录车头最近通道')
    axes[0].set(yticks=np.arange(8)*45, ylabel='车头通道 θ / °',
                title='车位中心八通道原始预测 T（无效上下文的预测也展示；有效性另列）')
    axes[0].legend(loc='upper right', fontsize=9)
    fig.colorbar(color, ax=axes[0], label='原始预测 T')
    flags = np.asarray([[r['center_context_valid'] for r in records],
                        [r['center_physical_valid'] for r in records]], float)
    axes[1].pcolormesh(edges, np.arange(3), flags, vmin=0, vmax=1, cmap='Greys_r', shading='flat')
    axes[1].set(yticks=[.5, 1.5], yticklabels=['HT 上下文有效', '中心物理支撑'],
                xlabel='记录时间 / s')
    axes[1].set_title('下方标志：白=有效，黑=无效；中心支撑不代表整个车体范围安全', fontsize=10)
    fig.suptitle('同一记录位置的 T(x,y,θ)：概率热图不是路径，也不是生产支撑结果', fontsize=15)
    fig.tight_layout(rect=[0, 0, 1, .94]); fig.savefig(out/'direction_heatmap.png'); plt.close(fig)


def support_heatmap(out, lookups, records, plt):
    from matplotlib.colors import BoundaryNorm, ListedColormap
    from matplotlib.patches import Patch
    labels = [r['label'] for r in records]; columns = {label: i for i, label in enumerate(labels)}
    states = sorted({r['start_support'] for v in VARIANTS for r in lookups[v].values()})
    palette = {'UNKNOWN': '#9ca7b4', 'BLOCKED': '#c55555', 'KNOWN': '#41965e', 'STARTUP': '#d6a13d'}
    cmap = ListedColormap([palette.get(k, '#7d69ad') for k in states]); cmap.set_bad('#ffffff')
    norm = BoundaryNorm(np.arange(len(states)+1)-.5, len(states)); encode = {s: i for i, s in enumerate(states)}
    fig, axes = plt.subplots(2, 2, figsize=(16, 6.5), dpi=150,
                             gridspec_kw={'width_ratios': [1, 1.6]})
    edges = time_edges(np.array([r['t_s'] for r in records]))
    for row, variant, name in zip(range(2), VARIANTS, VARIANT_NAMES):
        genuine = main_support(lookups[variant], labels)
        values = np.array([[encode[x] for x in genuine]], float)
        axes[row, 0].pcolormesh(edges, [0, 1], values, cmap=cmap, norm=norm, shading='flat')
        axes[row, 0].set(yticks=[.5], yticklabels=[name], title='主组：真实记录角；每帧取一次起点检查')
        probe = np.full((8, len(labels)), np.nan)
        for label, result in lookups[variant].items():
            match = COUNTERFACTUAL.fullmatch(label)
            if not match:
                continue
            frame, deg = match[1], int(match[2])
            if frame not in columns or deg not in range(0, 360, 45):
                raise ValueError(f'Unexpected counterfactual query: {label}')
            probe[deg//45, columns[frame]] = encode[result['start_support']]
        axes[row, 1].pcolormesh(edges, np.arange(9)*45-22.5, np.ma.masked_invalid(probe),
                                cmap=cmap, norm=norm, shading='flat')
        axes[row, 1].set(yticks=np.arange(8)*45, ylabel='假设起点车头 / °',
                         title=f'{name}：反事实角度探针（仅查询帧着色，白=未查询）')
    for ax in axes.flat:
        ax.set_xlabel('记录时间 / s')
    fig.legend(handles=[Patch(facecolor=cmap(i), label=s) for i, s in enumerate(states)] +
                       [Patch(facecolor='white', edgecolor='#999999', label='未查询')],
               loc='lower center', ncol=len(states)+1, frameon=False)
    fig.suptitle('C++ HtCostMap::poseSupport 实测结果；不以 T 阈值在 Python 中补算', fontsize=15)
    fig.tight_layout(rect=[0, .08, 1, .94]); fig.savefig(out/'support_heatmap.png'); plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', required=True, type=Path)
    parser.add_argument('--maps', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    data, maps, out = args.data.resolve(), args.maps.resolve(), args.output.resolve()
    results, lookups = load_results(data)
    meta_path = data/'input/metadata.json'
    meta = json.loads(meta_path.read_text())
    records = extract_frames(meta, maps)
    if not records:
        raise ValueError('No recorded maps')
    for variant in VARIANTS:
        supports = main_support(lookups[variant], [r['label'] for r in records])
        for record, state in zip(records, supports):
            record.setdefault('production_recorded_start_support', {})[variant] = state
    summary = summarize(results, records)
    out.mkdir(parents=True, exist_ok=False)
    dump(out/'frame_diagnostics.json', dict(
        scope='Raw NPZ center/circle diagnostics, separate from production poseSupport.',
        metadata_sha256=digest(meta_path), records=records))
    dump(out/'plot_summary.json', summary)
    plt = replay.plot_setup()
    comparisons(out, results, summary, records, plt)
    direction_heatmap(out, records, plt)
    support_heatmap(out, lookups, records, plt)
    print(json.dumps({'output': str(out), 'recorded_frames': len(records),
                      'groups': summary['groups']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
