#!/usr/bin/env python3
"""Reproduce recorded HT outputs and test sensitivity to height texture offline.

These are diagnostic counterfactuals, not changes to the driving pipeline.
"""
import argparse
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter, median_filter
import torch

BRIDGE = Path('/home/lzz/my test/ht_cupy_bridge_ws')
sys.path.insert(0, str(BRIDGE))
from model import load_student_model

plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'axes.unicode_minus': False})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('replay', type=Path)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    frames = json.loads((args.replay / 'snapshots/index.json').read_text())['frames']
    origin = json.loads((args.replay / 'original/measurement_started.json').read_text())['wall_time']
    times = np.array([f['ht_stamp'] - origin for f in frames])
    rows = list(csv.DictReader((args.replay / 'original/timeseries.csv').open()))
    pose_t = np.array([float(r['t_s']) for r in rows])
    pose_x = np.array([float(r['x_m']) for r in rows])
    pose_y = np.array([float(r['y_m']) for r in rows])
    pose_yaw = np.unwrap([float(r['yaw_rad']) for r in rows])
    torch.set_num_threads(2)
    model = load_student_model(str(BRIDGE / 'student_best_epoch_weights.pth'), torch.device('cpu'))

    def infer(z):
        with torch.inference_mode():
            return torch.softmax(model(torch.from_numpy(z.astype(np.float32)[None, None])), dim=2)[0, :, 1].numpy()

    results = []
    for target in [26, 50, 100, 200, 300, 400, 595]:
        i = int(np.argmin(abs(times - target)))
        with np.load(args.replay / 'snapshots' / frames[i]['file']) as d:
            assert abs(float(d['history_stamp'] - d['ht_stamp'])) < 1e-6
            assert np.max(abs(d['history_geometry'] - d['ht_geometry'])) < 1e-6
            z = d['history_elevation']
            observed = np.isfinite(z) & np.isfinite(d['history_variance']) & (d['history_variance'] < 1)
            _, nearest = distance_transform_edt(~observed, return_indices=True)
            filled = z[tuple(nearest)]
            valid = d['ht_ht_valid'] >= .5
            recorded = np.stack([d[f'ht_ht_dir_{k}'] for k in range(8)])
            variants = {
                'original': filled,
                'median_3_cells': median_filter(filled, size=3, mode='nearest'),
                'gaussian_sigma_1_cell': gaussian_filter(filled, sigma=1, mode='nearest'),
                'gaussian_sigma_2_cells': gaussian_filter(filled, sigma=2, mode='nearest'),
                'constant_plane': np.full_like(filled, np.nanmedian(z)),
            }
            predictions = {name: infer(h) for name, h in variants.items()}
            cx, cy, res = d['ht_geometry']
            n, m = valid.shape
            xx, yy = np.meshgrid(cx + (n/2 - np.arange(n) - .5)*res,
                                 cy + (m/2 - np.arange(m) - .5)*res, indexing='ij')
            robot = np.array([np.interp(times[i], pose_t, pose_x), np.interp(times[i], pose_t, pose_y), np.interp(times[i], pose_t, pose_yaw)])
            radius = np.hypot(xx-robot[0], yy-robot[1])
            entry = {'file': frames[i]['file'], 't_s': times[i], 'pose': robot.tolist(),
                     'resolution_m': float(res), 'support_fraction': float(valid.mean()),
                     'reproduction_max_error': float(np.max(abs(predictions['original'][:, valid] - recorded[:, valid]))),
                     'variants': {}}
            for name, p in predictions.items():
                mean_p = p.mean(axis=0)
                metric = {'channel0_low_fraction': float((p[0, valid] < .5).mean()),
                          'mean8_low_fraction': float((mean_p[valid] < .5).mean()),
                          'any_channel_low_fraction': float((p[:, valid] < .5).any(axis=0).mean()),
                          'radial_bins': []}
                for lo, hi in [(0, 2), (2, 4), (4, 6), (6, 8)]:
                    mask = valid & (radius >= lo) & (radius < hi)
                    if mask.any():
                        metric['radial_bins'].append({'lo_m': lo, 'hi_m': hi, 'n': int(mask.sum()),
                            'channel0_low_fraction': float((p[0, mask] < .5).mean()),
                            'mean8_low_fraction': float((mean_p[mask] < .5).mean()),
                            'mean8_median_probability': float(np.median(mean_p[mask]))})
                entry['variants'][name] = metric
            results.append(entry)
            if target == 26:
                fig, axes = plt.subplots(2, 3, figsize=(16, 11), constrained_layout=True)
                cmap = plt.get_cmap('RdYlGn').copy(); cmap.set_bad('#bfc3c6')
                def plane(ax, values, geometry, color_map, lo, hi):
                    x, y, r = geometry; a, b = values.shape
                    return ax.imshow(values[::-1, ::-1].T, origin='lower', interpolation='nearest',
                                     extent=[x-a*r/2, x+a*r/2, y-b*r/2, y+b*r/2],
                                     cmap=color_map, vmin=lo, vmax=hi)
                im = plane(axes[0,0], z, d['history_geometry'], 'terrain', .04, .20)
                fig.colorbar(im, ax=axes[0,0], label='高程 (m)；超范围饱和显示')
                axes[0,0].set_title('实际历史高程：逐格显示')
                jump = np.maximum.reduce([abs(filled-np.roll(filled, shift, axis)) for shift in [-1,1] for axis in [0,1]])*1000
                im = plane(axes[0,1], jump, d['history_geometry'], 'magma', 0, 30)
                fig.colorbar(im, ax=axes[0,1], label='相邻格最大高度差 (mm)')
                axes[0,1].set_title('输入中的密集高度差纹理')
                panels = [(axes[0,2], 'original', '原始 HT 通道 0'),
                          (axes[1,0], 'median_3_cells', '仅诊断：3×3 格中值处理后'),
                          (axes[1,1], 'gaussian_sigma_1_cell', '仅诊断：σ=1 格平滑后'),
                          (axes[1,2], 'gaussian_sigma_2_cells', '仅诊断：σ=2 格平滑后')]
                for ax, name, title in panels:
                    im = plane(ax, np.where(valid, predictions[name][0], np.nan), d['ht_geometry'], cmap, 0, 1)
                    ax.set_title(title)
                fig.colorbar(im, ax=[p[0] for p in panels], label='HT 概率（固定 0–1）')
                for ax in axes.flat:
                    ax.plot(*robot[:2], 'bo', ms=5)
                    ax.arrow(robot[0], robot[1], .9*np.cos(robot[2]), .9*np.sin(robot[2]), color='blue', width=.035, length_includes_head=True)
                    ax.arrow(robot[0], robot[1], -.9*np.cos(robot[2]), -.9*np.sin(robot[2]), color='black', width=.035, length_includes_head=True)
                    ax.set(xlabel='Map X (m)', ylabel='Map Y (m)')
                fig.suptitle(f't={times[i]:.2f}s；蓝箭头车头，黑箭头实际倒车方向\n平滑仅用于查因，不能据此把未知或真实障碍放行；通道0角度尚待标定')
                fig.savefig(args.output/'height_texture_counterfactual.png', dpi=180)
                plt.close(fig)
            print(json.dumps({'t_s': entry['t_s'], 'error': entry['reproduction_max_error'],
                              'mean8_low': {k: v['mean8_low_fraction'] for k,v in entry['variants'].items()}}, ensure_ascii=False), flush=True)
    (args.output/'counterfactual_metrics.json').write_text(json.dumps(results, ensure_ascii=False, indent=2)+'\n')


if __name__ == '__main__':
    main()
