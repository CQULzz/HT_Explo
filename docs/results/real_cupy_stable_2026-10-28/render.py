#!/usr/bin/env python3
"""Compare actual offline old/new CuPy+HT fields and C++ XYtheta query outputs.

This program reads serialized results only: no driver, controller, ROS node,
vehicle simulation, model inference or physical actuation is started.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess

import numpy as np


def read(path):
    return json.loads(Path(path).read_text())


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for data in iter(lambda: stream.read(8*1024*1024), b''):
            digest.update(data)
    return digest.hexdigest()


def finite(value):
    value = float(value)
    return value if math.isfinite(value) else None


def number(value):
    return 'NaN' if value is None else f'{value:.3f}'


def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+'\n')


def setup():
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt, font_manager
    font = Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus'] = False
    return plt


def grid(z):
    n, m = z['ht_valid'].shape
    r = float(z['resolution'])
    ii, jj = np.indices((n, m))
    # Producer contract: canonical yaw=0 GridMap; row and column decrease X,Y.
    x = z['center'][0]+(n/2-ii-.5)*r
    y = z['center'][1]+(m/2-jj-.5)*r
    return x, y


def diagnostics(path, frame):
    with np.load(path, allow_pickle=False) as z:
        x, y = grid(z)
        robot = z['robot']
        n, m = z['ht_valid'].shape
        cell = np.floor(np.array([n/2, m/2])-(robot[:2]-z['center'])/float(z['resolution'])).astype(int)
        if not (0 <= cell[0] < n and 0 <= cell[1] < m):
            raise ValueError(f'Robot outside HT map: {path}')
        scores = z['probabilities'][:, cell[0], cell[1]]
        heading = int(math.floor((float(robot[2]) % (2*math.pi))/(math.pi/4)+.5)) % 8
        distance = (x-robot[0])**2 + (y-robot[1])**2
        body = distance <= .6**2
        known = np.isfinite(z['ht_observation_valid']) & (z['ht_observation_valid'] >= .5)
        valid = np.isfinite(z['ht_valid']) & (z['ht_valid'] >= .5)
        obstacle = np.isfinite(z['ht_obstacle']) & (z['ht_obstacle'] >= .5)
        heights = z['ht_elevation'][(distance <= 1.) & np.isfinite(z['ht_elevation'])]
        height_quantiles = [finite(x) for x in np.quantile(heights, [.05, .5, .95])] if len(heights) else [None]*3
        return dict(file=path.name, npz_sha256=sha(path), stamp_ns=int(frame['stamp_ns']),
                    t_s=float(frame['t_s']), robot=robot.tolist(), center=z['center'].tolist(),
                    center_cell=cell.tolist(), center_direction_T=[finite(x) for x in scores],
                    nearest_recorded_heading_channel=heading, nearest_recorded_heading_T=finite(scores[heading]),
                    center_max_T=finite(np.nanmax(scores)) if np.isfinite(scores).any() else None,
                    center_context_valid=bool(valid[tuple(cell)]),
                    center_physical_valid=bool(known[tuple(cell)]),
                    body_radius_m=.6, body_cells=int(body.sum()),
                    body_physical_unknown=int((body & ~known).sum()),
                    body_context_invalid=int((body & ~valid).sum()), body_obstacle=int((body & obstacle).sum()),
                    body_obstacle_nonfinite=int((body & ~np.isfinite(z['ht_obstacle'])).sum()),
                    near_1m_height_p05_p50_p95_m=height_quantiles,
                    near_1m_height_span_p95_p05_m=finite(height_quantiles[2]-height_quantiles[0]) if len(heights) else None)


def query_group(label):
    if label.startswith('recorded_'):
        return 'recorded'
    if label.startswith('counterfactual_heading_'):
        return 'counterfactual_heading'
    if label.startswith('synthetic_'):
        return 'synthetic'
    raise ValueError(f'Unrecognized query label: {label}')


def load_queries(paths):
    result = {role: read(path) for role, path in paths.items()}
    if result['before']['parameters'] != result['after']['parameters']:
        raise ValueError('Old/new C++ parameters differ')
    parameters = result['after']['parameters']
    if parameters.get('ht_validity_radius') != .6 or parameters.get('ht_min_probability') != .5:
        raise ValueError('This diagnostic caption requires the frozen 0.6m radius / 0.5 threshold')
    lookup = {}
    hashes = {}
    for role, data in result.items():
        lookup[role] = {r['label']: r for r in data['queries']}
        if len(lookup[role]) != len(data['queries']):
            raise ValueError(f'Duplicate query labels: {role}')
        for row in data['queries']:
            query_group(row['label'])
            if row.get('error'):
                raise ValueError(f'Actual C++ runner error: {row}')
            source = Path(row['map_file'])
            if source not in hashes:
                hashes[source] = sha(source)
            if hashes[source] != row['map_sha256']:
                raise ValueError(f'C++ input CDR digest mismatch: {source}')
            if row['reached'] and not (row.get('all_segments_permitted') and row.get('independent_recheck_passed')):
                raise ValueError(f'Unchecked successful path: {row["label"]}')
    if lookup['before'].keys() != lookup['after'].keys():
        raise ValueError('Old/new query labels differ')
    for label, row in lookup['before'].items():
        for key in ['start', 'goal', 'map_stamp_ns']:
            if row[key] != lookup['after'][label][key]:
                raise ValueError(f'Compared geometric input differs: {label}: {key}')
    return result, lookup


def summarize_queries(results):
    summary = {}
    for role, data in results.items():
        summary[role] = {}
        for group in ['recorded', 'counterfactual_heading', 'synthetic']:
            rows = [r for r in data['queries'] if query_group(r['label']) == group]
            summary[role][group] = dict(queries=len(rows), reached=sum(bool(r['reached']) for r in rows),
                start_support=dict(Counter(r['start_support'] for r in rows)),
                termination=dict(Counter(r['termination'] for r in rows)))
    return summary


def query_for_frame(lookup, filename):
    stem = Path(filename).stem
    preferred = f'recorded_{stem}_goal_000deg'
    if preferred in lookup:
        return lookup[preferred]
    rows = sorted((r for label, r in lookup.items() if label.startswith(f'recorded_{stem}_goal_')),
                  key=lambda r: r['label'])
    return rows[0] if rows else None


def attach_support(records, lookups):
    for role in ['before', 'after']:
        for record in records[role]:
            prefix = f'recorded_{Path(record["file"]).stem}_goal_'
            rows = [r for label, r in lookups[role].items() if label.startswith(prefix)]
            if not rows:
                raise ValueError(f'No actual C++ query for {role}/{record["file"]}')
            states = {r['start_support'] for r in rows}
            if len(states) != 1:
                raise ValueError('Goal direction changed the same recorded start support')
            record['production_start_support'] = next(iter(states))
            record['actual_recorded_queries'] = len(rows)
            record['actual_recorded_reached'] = sum(bool(r['reached']) for r in rows)


def series_figure(out, records, query_summary, plt):
    fig, axes = plt.subplots(2, 3, figsize=(16, 9), dpi=150)
    colors = {'before': '#547b9d', 'after': '#dd8e39'}
    for role, name in [('before', '修改前'), ('after', '确定性 CuPy 候选')]:
        rows = records[role]; t = [r['t_s'] for r in rows]; color = colors[role]
        for ax, key in [(axes[0, 0], 'body_physical_unknown'), (axes[0, 1], 'body_context_invalid'),
                        (axes[0, 2], 'body_obstacle'), (axes[1, 0], 'nearest_recorded_heading_T'),
                        (axes[1, 1], 'near_1m_height_span_p95_p05_m')]:
            ax.plot(t, [r[key] for r in rows], color=color, label=name)
    titles = ['0.6m 圈物理支撑未知', '0.6m 圈 HT 上下文无效', '0.6m 圈 ht_obstacle 格数',
              '记录车头最近通道的中心 T', '车旁 1m 内高程 P95−P05', '真实记录姿态的 C++ 起点判定']
    for ax, title in zip(axes.flat, titles):
        ax.set_title(title, fontsize=12); ax.grid(alpha=.2)
    for ax in axes.flat[:5]:
        ax.set_xlabel('原录包时间 / s'); ax.legend(fontsize=9)
    for ax in axes[0]:
        ax.set_ylabel('格数（不同维度不可相加）')
    axes[1, 0].set_ylabel('T'); axes[1, 0].set_ylim(-.03, 1.03)
    axes[1, 0].axhline(.5, color='#ab3b3b', ls='--', label='0.5 门槛')
    axes[1, 1].set_ylabel('m')
    states = sorted({r['production_start_support'] for role in records for r in records[role]})
    for role, name, offset in [('before', '修改前', -.18), ('after', '候选', .18)]:
        counts = Counter(r['production_start_support'] for r in records[role])
        bars = axes[1, 2].bar(np.arange(len(states))+offset, [counts[s] for s in states], .36,
                              color=colors[role], label=name)
        for bar in bars:
            axes[1, 2].text(bar.get_x()+bar.get_width()/2, bar.get_height(), str(int(bar.get_height())),
                            ha='center', va='bottom', fontsize=9)
    axes[1, 2].set(xticks=range(len(states)), xticklabels=states, ylabel='记录帧数（每帧一次）'); axes[1, 2].legend()
    total = len(records['after'])
    success = query_summary['after']['recorded']
    fig.suptitle('同一历史点云与位姿：旧 CuPy 融合 vs 确定性 CuPy 候选', fontsize=17)
    fig.text(.5, .02, f'没有新行驶；{total} 帧，每帧多个目标共享同一起点。候选真实主组成功 '
             f'{success["reached"]}/{success["queries"]}；结果不能解释成新的探索收益。', ha='center', fontsize=10)
    fig.tight_layout(rect=[0, .06, 1, .95]); fig.savefig(out/'timeseries_comparison.png'); plt.close(fig)


def body_xy(z):
    x, y = grid(z); dx, dy = x-z['robot'][0], y-z['robot'][1]; yaw = z['robot'][2]
    return dx*np.cos(yaw)+dy*np.sin(yaw), -dx*np.sin(yaw)+dy*np.cos(yaw)


def last_figures(out, folders, frames, records, plt):
    from matplotlib.patches import Circle
    fig, axes = plt.subplots(2, 3, figsize=(16, 10), dpi=150)
    fields = {}
    for role in ['before', 'after']:
        with np.load(folders[role]/frames[role][-1]['file'], allow_pickle=False) as z:
            fields[role] = {k: np.array(z[k]) for k in z.files}
    allheight = []
    for z in fields.values():
        bx, by = body_xy(z); mask = bx*bx+by*by <= 1.8**2
        allheight.extend(z['ht_elevation'][mask & np.isfinite(z['ht_elevation'])])
    lo, hi = np.quantile(allheight, [.02, .98]) if allheight else (-1., 1.)
    hi = max(float(hi), float(lo)+.01)
    for row, role in enumerate(['before', 'after']):
        z = fields[role]; bx, by = body_xy(z); record = records[role][-1]
        image = axes[row, 0].pcolormesh(bx, by, z['ht_elevation'], cmap='terrain', vmin=lo, vmax=hi, shading='nearest', rasterized=True)
        fig.colorbar(image, ax=axes[row, 0], label='地图高程 / m（前后同色标）')
        axes[row, 0].add_patch(Circle((0, 0), .6, fill=False, color='black', ls='--'))
        axes[row, 0].set(xlim=(-1.8, 1.8), ylim=(-1.8, 1.8), aspect='equal', xlabel='车体 X / m', ylabel='车体 Y / m',
                         title=f'{role}：末帧高程，圈半径 0.6m')
        physical = np.isfinite(z['ht_observation_valid']) & (z['ht_observation_valid'] >= .5)
        axes[row, 1].pcolormesh(bx, by, physical.astype(float), vmin=0, vmax=1, cmap='Greens', shading='nearest')
        obstacle = np.where(z['ht_obstacle'] >= .5, 1., np.nan)
        from matplotlib.colors import ListedColormap
        axes[row, 1].pcolormesh(bx, by, obstacle, cmap=ListedColormap(['#a12636']), shading='nearest')
        axes[row, 1].add_patch(Circle((0, 0), .6, fill=False, color='black', ls='--'))
        axes[row, 1].set(xlim=(-1.8, 1.8), ylim=(-1.8, 1.8), aspect='equal', xlabel='车体 X / m', ylabel='车体 Y / m',
                         title=f'绿=物理支撑，红=障碍；白=缺测\n圈内未知 {record["body_physical_unknown"]}，障碍 {record["body_obstacle"]}')
        axes[row, 2].bar(np.arange(8)*45, record['center_direction_T'], width=30, color='#6789a9')
        axes[row, 2].axhline(.5, color='#bb3434', ls='--'); axes[row, 2].set(ylim=(0, 1), xticks=np.arange(8)*45,
            xlabel='车头通道 / °', ylabel='中心原始 T', title=f'实际 C++ 起点：{record["production_start_support"]}\n中心 T 不能替代完整车体检查')
    fig.suptitle('末帧实际输出：高程、物理层和 HT 概率分开检查', fontsize=17)
    fig.tight_layout(rect=[0, 0, 1, .95]); fig.savefig(out/'last_maps_height_probabilities.png'); plt.close(fig)


def model_geometry(out, geometry_paths, plt):
    if not any(geometry_paths.values()):
        return None
    import yaml
    from matplotlib.patches import Rectangle
    fig, axes = plt.subplots(1, 2, figsize=(13, 6), dpi=150)
    metadata = {}
    for role, path in geometry_paths.items():
        if path is None:
            continue
        data = yaml.safe_load(path.read_text()); layer = data['lidar_self_filter']; boxes = layer['boxes']
        color = '#507fa4' if role == 'before' else '#d67e38'
        for box in boxes:
            lo, hi = np.asarray(box['min_xyz']), np.asarray(box['max_xyz'])
            for ax, dims in zip(axes, [(0, 1), (0, 2)]):
                i, j = dims
                ax.add_patch(Rectangle((lo[i], lo[j]), hi[i]-lo[i], hi[j]-lo[j], fill=False, color=color,
                                       alpha=.7, linewidth=.9))
                ax.update_datalim([[lo[i], lo[j]], [hi[i], hi[j]]])
        axes[0].plot([], [], color=color, label=f'{role}: {len(boxes)} boxes')
        metadata[role] = dict(file=str(path), sha256=sha(path), boxes=boxes, cylinders=layer.get('cylinders', []),
                              note='Displayed base_link self-filter boxes, including configured engineering margin; '
                                   'not proof of actual historical attachment geometry.')
    for ax, ylabel in zip(axes, ['车体 Y / m', '车体 Z / m']):
        ax.autoscale_view(); ax.set(xlabel='车体 X / m', ylabel=ylabel, aspect='equal'); ax.grid(alpha=.2)
    axes[0].legend()
    fig.suptitle('实际配置的过滤 AABB 投影；两侧使用同一车体过滤模型', fontsize=14)
    fig.tight_layout(rect=[0, 0, 1, .93]); fig.savefig(out/'self_filter_geometry.png'); plt.close(fig)
    return metadata


def voxel(ax, z, plt, halfwidth=1.85, stride=12, alpha=.085):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    n, m = z['ht_valid'].shape; r = float(z['resolution'])
    ii, jj = np.meshgrid(np.arange(stride//2, n, stride), np.arange(stride//2, m, stride), indexing='ij')
    xx = z['center'][0]+(n/2-ii-.5)*r; yy = z['center'][1]+(m/2-jj-.5)*r
    robot = z['robot']; valid = np.isfinite(z['ht_valid'][ii, jj]) & (z['ht_valid'][ii, jj] >= .5)
    inside = valid & (abs(xx-robot[0]) <= halfwidth) & (abs(yy-robot[1]) <= halfwidth)
    p = z['probabilities'][:, ii, jj]
    k, i, j = np.where(np.broadcast_to(inside, p.shape) & np.isfinite(p))
    width = stride*r*.97
    vertex = np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]], float)
    vertices = vertex[None]*np.array([width, width, 45.])[None,None]
    vertices = vertices+np.stack([xx[i,j]-width/2, yy[i,j]-width/2, k*45.], axis=1)[:,None]
    faces = np.array([[0,1,2,3],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])
    rgba = plt.get_cmap('RdYlGn')(p[k,i,j]); rgba[:,3] = alpha
    if len(k):
        ax.add_collection3d(Poly3DCollection(vertices[:,faces].reshape(-1,4,3), facecolors=np.repeat(rgba, 6, axis=0),
                                             edgecolors=(.45,.55,.6,.055), linewidths=.12, zsort='average'))
    ax.set(xlim=(robot[0]-halfwidth, robot[0]+halfwidth), ylim=(robot[1]-halfwidth, robot[1]+halfwidth),
           zlim=(0,360), zticks=[0,90,180,270,360], xlabel='X / m', ylabel='Y / m', zlabel='θ / °')
    ax.tick_params(labelsize=7); ax.view_init(23, -62); ax.set_box_aspect((1, 1, 1.1))
    return stride*r


def plot_path(ax, row):
    if not row or not row.get('poses'):
        return
    poses = np.asarray(row['poses'], float)
    theta = np.degrees(poses[:,2]) % 360
    breaks = np.where(np.abs(np.diff(theta)) > 180)[0]+1
    for segment in np.split(np.column_stack([poses[:,:2], theta]), breaks):
        ax.plot(segment[:,0], segment[:,1], segment[:,2], color='#168cde', lw=2.5)


def video(out, folders, frames, records, lookups, plt, ffmpeg, sample_every, frame_hold,
          voxel_stride=4, voxel_alpha=.03):
    selected = sorted(set(list(range(0, len(frames['after']), sample_every))+[len(frames['after'])-1]))
    folder = out/'video_frames'; folder.mkdir()
    timeline = ['ffconcat version 1.0']; manifest = []
    for num, index in enumerate(selected):
        fig = plt.figure(figsize=(16, 9), dpi=120, facecolor='#f3f6f8')
        for col, role, name in [(0, 'before', '旧 CuPy 融合'), (1, 'after', '确定性 CuPy 候选')]:
            with np.load(folders[role]/frames[role][index]['file'], allow_pickle=False) as f:
                z = {k: np.array(f[k]) for k in f.files}
            record = records[role][index]; row = query_for_frame(lookups[role], record['file'])
            ax = fig.add_axes([.015+col*.5, .24, .48, .63], projection='3d')
            display_resolution = voxel(ax, z, plt, stride=voxel_stride, alpha=voxel_alpha); plot_path(ax, row)
            ax.scatter([z['robot'][0]], [z['robot'][1]], [math.degrees(z['robot'][2])%360], c='#145a9f', s=32, depthshade=False)
            ax.set_title(f'{name} | {row["termination"] if row else "NO_QUERY"}\n'
                         f'生产起点检查：{record["production_start_support"]}', fontsize=13)
            text = (f'0.6m 圈：缺物理支撑 {record["body_physical_unknown"]}/{record["body_cells"]} 格；'
                    f'HT 上下文无效 {record["body_context_invalid"]}；障碍 {record["body_obstacle"]}\n'
                    f'中心最大 T={number(record["center_max_T"])}；记录车头通道 T={number(record["nearest_recorded_heading_T"])}\n'
                    +(f'实际 C++ 查询：{row["label"]}；路径 {row.get("path_length_m",0):.2f}m'
                      if row else '该帧无实际查询，不补造路径'))
            fig.text(.035+col*.5, .16, text, fontsize=10, va='top', linespacing=1.7)
            manifest.append(dict(frame_index=index, role=role, source_npz_sha256=record['npz_sha256'],
                                 query_label=row['label'] if row else None,
                                 termination=row['termination'] if row else None,
                                 display_voxel_xy_m=display_resolution, display_voxel_theta_deg=45,
                                 display_voxel_stride=voxel_stride, display_voxel_alpha=voxel_alpha))
        time = records['after'][index]['t_s']
        fig.suptitle(f'同一历史点云重新建图 → HT → 实际 C++ XYθ 查询 | 原录包 t={time:.1f}s', fontsize=16, y=.98)
        from matplotlib.cm import ScalarMappable
        from matplotlib.colors import Normalize
        color_ax = fig.add_axes([.425, .925, .15, .010])
        legend = fig.colorbar(ScalarMappable(norm=Normalize(0, 1), cmap='RdYlGn'), cax=color_ax, orientation='horizontal', ticks=[0, .5, 1])
        legend.ax.tick_params(labelsize=8)
        legend.set_label('通行概率 T（固定0–1色标）', fontsize=8)
        fig.text(.5, .035, '没有新行驶；视频为地图快照对比，不是实车录像。未知透明；蓝点是记录姿态；蓝线仅在实际产生路径时显示。\n'
                 f'显示格约{display_resolution:.2f}m×45°，原图{float(z["resolution"]):.2f}m；颜色=T，保留0.5硬门槛。反事实朝向可行不证明车辆能转过去。',
                 ha='center', fontsize=10)
        image = folder/f'{num:04d}.png'; fig.savefig(image); plt.close(fig)
        timeline.extend([f"file 'video_frames/{num:04d}.png'", f'duration {frame_hold:.9f}'])
        if num in [0, len(selected)-1]:
            shutil.copy2(image, out/('video_first.png' if num == 0 else 'video_last.png'))
        print('render', num+1, '/', len(selected), flush=True)
    timeline.append(f"file 'video_frames/{len(selected)-1:04d}.png'")
    concat = out/'timeline.ffconcat'; concat.write_text('\n'.join(timeline)+'\n')
    target = out/'HT_CuPy_stable_xytheta_comparison.mp4'; duration = len(selected)*frame_hold
    command = [ffmpeg,'-hide_banner','-loglevel','error','-n','-f','concat','-safe','0','-i',str(concat),
               '-an','-vf','fps=20','-t',str(duration),'-c:v','libx264','-preset','fast','-crf','20',
               '-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
    subprocess.run(command, check=True)
    decode = subprocess.run([ffmpeg,'-v','error','-i',str(target),'-f','null','-'], capture_output=True, text=True)
    if decode.returncode or decode.stderr:
        raise RuntimeError('Full video decode failed: '+decode.stderr)
    write(out/'video_validation.json', dict(video=target.name, sha256=sha(target), bytes=target.stat().st_size,
        encoding='H264/yuv420p/20fps', duration_s=duration, selected_snapshots=len(selected),
        display_voxel_stride=voxel_stride, display_voxel_alpha=voxel_alpha,
        scope='Paired offline snapshots and saved actual C++ paths only; no executed vehicle motion.',
        full_decode_passed=True, ffmpeg_command=command, frames=manifest))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data', type=Path, required=True)
    p.add_argument('--before-queries', type=Path, required=True)
    p.add_argument('--after-queries', type=Path, required=True)
    p.add_argument('--before-geometry', type=Path)
    p.add_argument('--after-geometry', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ffmpeg', help='Absolute ffmpeg path; required unless --figures-only')
    p.add_argument('--figures-only', action='store_true')
    p.add_argument('--sample-every', type=int, default=10)
    p.add_argument('--frame-hold', type=float, default=1.5)
    p.add_argument('--voxel-stride', type=int, default=4,
                   help='XY display sampling stride; does not change source grids or planning')
    p.add_argument('--voxel-alpha', type=float, default=.03,
                   help='Display cube face opacity in [0,1]; does not change probabilities')
    p.add_argument('--expected-frames', type=int, default=208)
    a = p.parse_args()
    if not a.figures_only and not a.ffmpeg:
        p.error('--ffmpeg is required for video')
    if a.sample_every < 1 or a.frame_hold <= 0:
        p.error('Invalid sampling/hold interval')
    if a.voxel_stride < 1 or not math.isfinite(a.voxel_alpha) or not 0 <= a.voxel_alpha <= 1:
        p.error('--voxel-stride must be positive and --voxel-alpha must be finite in [0,1]')
    folders = {role: a.data/f'ht_{role}/maps' for role in ['before','after']}
    indices = {role: read(folder/'index.json') for role, folder in folders.items()}
    frames = {role: [f for f in index['frames'] if f.get('output')] for role, index in indices.items()}
    if not all(len(rows) == a.expected_frames for rows in frames.values()):
        raise ValueError(f'Incomplete data: { {k:len(v) for k,v in frames.items()} }')
    records = {role: [diagnostics(folders[role]/f['file'], f) for f in rows] for role, rows in frames.items()}
    for old, new in zip(records['before'], records['after']):
        if old['stamp_ns'] != new['stamp_ns'] or old['file'] != new['file']:
            raise ValueError('Old/new map samples do not align')
        if not np.allclose(old['robot'], new['robot'], rtol=0, atol=1e-8):
            raise ValueError('Old/new historical poses differ')
    paths = {'before': a.before_queries, 'after': a.after_queries}
    results, lookup = load_queries(paths); attach_support(records, lookup)
    query_summary = summarize_queries(results)
    a.output.mkdir(parents=True, exist_ok=False)
    plt = setup(); series_figure(a.output, records, query_summary, plt)
    last_figures(a.output, folders, frames, records, plt)
    geometry = model_geometry(a.output, {'before': a.before_geometry, 'after': a.after_geometry}, plt)
    summary = dict(scope='Same sampled historical point clouds and poses, legacy/deterministic CuPy fusion with identical geometry filtering; '
                         'new CuPy+HT fields and frozen C++ fixed-goal checks, not closed-loop navigation.',
        source_index_sha256={role: sha(folder/'index.json') for role,folder in folders.items()},
        query_results_sha256={role:sha(path) for role,path in paths.items()},
        parameters=results['after']['parameters'], frames_per_variant=len(records['after']),
        duration_s=records['after'][-1]['t_s']-records['after'][0]['t_s'],
        query_groups=query_summary, first={role:rows[0] for role,rows in records.items()},
        last={role:rows[-1] for role,rows in records.items()}, geometry=geometry,
        frames=records,
        limitations=['Raw body-circle diagnostics do not reproduce production inflated-footprint poseSupport.',
                     'Physical support includes existing nearest-observation support, not direct LiDAR hits in every cell.',
                     'Repeated goal directions at one pose are correlated queries, not independent driving trials.',
                     'Counterfactual headings are hypothetical; no feasible rotation from recorded yaw is established.',
                     'Synthetic controls are separate from recorded field results.',
                     'No model threshold, unknown policy or recorded source time is changed by this plotting program.'])
    write(a.output/'RESULTS.json', summary)
    if not a.figures_only:
        video(a.output, folders, frames, records, lookup, plt, a.ffmpeg, a.sample_every, a.frame_hold,
              a.voxel_stride, a.voxel_alpha)
    print(json.dumps({'output':str(a.output), 'query_groups':query_summary,
                      'last':summary['last']}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
