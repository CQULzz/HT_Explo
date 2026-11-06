"""Render saved matched CMU runs as plots and time-aligned 2D video."""
from pathlib import Path
import csv
import hashlib
import json
import numpy as np
import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path('/home/lzz/HT_cmu_pair_cycle10_20261106')
OUT = Path('/home/lzz/HT_cmu_baseline_audit_20261106/analysis')
OUT.mkdir(exist_ok=True)
RUNTIME = Path('/home/lzz/HT_cmu_indoor_cycle9_20261106/runtime')
CASES = [('p03_ht42', 'HT', '#d73c32'), ('p02_tare42', 'Modified fork (HT off) + CMU', '#186fc0')]
POINTS = np.load(RUNTIME / 'local_map.npy')
WALLS = POINTS[(POINTS[:, 2] > .15) & (POINTS[:, 2] < 2.8)]
DATA = {}
for label, name, color in CASES:
    run = ROOT / 'runs' / label
    rows = [r for r in csv.DictReader((run / 'metrics.csv').open()) if float(r['elapsed_sim']) >= 0]
    values = {key: np.array([float(r[key]) for r in rows]) for key in
              ['elapsed_sim', 'x', 'y', 'distance_m', 'observed_free_volume_m3', 'v_cmd', 'w_cmd']}
    DATA[label] = (rows, values)

fig, axes = plt.subplots(2, 3, figsize=(16, 9))
for ax in axes[0, :2]:
    ax.scatter(WALLS[::3, 0], WALLS[::3, 1], s=.18, color='#999999', rasterized=True)
    ax.set_aspect('equal')
    ax.set(xlabel='World x (m)', ylabel='World y (m)')
for label, name, color in CASES:
    rows, values = DATA[label]
    for ax in axes[0, :2]:
        ax.plot(values['x'], values['y'], color=color, lw=1.8, label=name)
        ax.scatter(values['x'][-1], values['y'][-1], color=color, s=22)
    axes[0, 2].plot(values['elapsed_sim'], values['distance_m'], color=color, label=name)
    axes[1, 0].plot(values['elapsed_sim'], values['observed_free_volume_m3'], color=color, label=name)
    axes[1, 2].plot(values['elapsed_sim'], values['v_cmd'], color=color, label=name + ' v')
    axes[1, 2].plot(values['elapsed_sim'], values['w_cmd'], color=color, ls=':', alpha=.7, label=name + ' yaw')
xs = np.concatenate([v['x'] for _, v in DATA.values()])
ys = np.concatenate([v['y'] for _, v in DATA.values()])
xmin, xmax = float(xs.min()) - 3, float(xs.max()) + 3
ymin, ymax = float(ys.min()) - 3, float(ys.max()) + 3
axes[0, 0].set(title='Native CMU indoor environment', xlim=(-3, 129), ylim=(-31, 71))
axes[0, 1].set(title='Matched route detail', xlim=(xmin, xmax), ylim=(ymin, ymax))
axes[0, 2].set(title='Actual cumulative XY distance', xlabel='Elapsed simulation (s)', ylabel='Distance (m)')
axes[1, 0].set(title='Source-second sampled free volume', xlabel='Elapsed simulation (s)', ylabel='Ray/voxel union (m3)')
events = [json.loads(line) for line in (ROOT / 'runs/p03_ht42/events.jsonl').open()]
performance = [e for e in events if e['topic'] == 'ht_performance']
rows, values = DATA['p03_ht42']
start = float(rows[0]['sim_time']) - float(rows[0]['elapsed_sim'])
axes[1, 1].plot([e['time'] - start for e in performance],
                [json.loads(e['data'])['source_age_at_publish_s'] for e in performance], color=CASES[0][2], label='HT source age')
axes[1, 1].axhline(1, color='black', ls='--', label='HT 1 s gate')
axes[1, 1].set(title='HT producer source age', xlabel='Elapsed simulation (s)', ylabel='Age (s)', ylim=(0, 1.05))
axes[1, 2].set(title='Published simulation commands', xlabel='Elapsed simulation (s)', ylabel='v (m/s), yaw (rad/s)')
for ax in axes.flat:
    ax.grid(alpha=.2)
    ax.legend(fontsize=8)
fig.suptitle('CMU indoor + Scout integration diagnostic / upstream TARE baseline unverified')
fig.tight_layout()
fig.savefig(OUT / 'INTEGRATION_DIAGNOSTIC.png', dpi=160)
plt.close(fig)

