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

ROOT = Path(__file__).parent
OUT = ROOT / 'analysis'
OUT.mkdir(exist_ok=True)
RUNTIME = Path('/home/lzz/HT_cmu_indoor_cycle9_20261106/runtime')
CASES = [('p03_ht42', 'HT', '#d73c32'), ('p02_tare42', 'TARE + CMU', '#186fc0')]
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
fig.suptitle('CMU indoor + Scout / seed 42 / matched 120 s trials')
fig.tight_layout()
fig.savefig(OUT / 'COMPARISON.png', dpi=160)
plt.close(fig)

# Equal XY scale in each panel. Every frame samples the same elapsed sim time.
width, height = 960, 680
scale = min(860 / (xmax - xmin), 490 / (ymax - ymin))
def xy(x, y):
    return round(45 + (x - xmin) * scale), round(645 - (y - ymin) * scale)
background = np.full((height, width, 3), 248, np.uint8)
local = WALLS[(WALLS[:, 0] >= xmin) & (WALLS[:, 0] <= xmax) & (WALLS[:, 1] >= ymin) & (WALLS[:, 1] <= ymax)]
coords = np.array([xy(x, y) for x, y, z in local])
background[coords[:, 1], coords[:, 0]] = (135, 135, 135)
filename = OUT / 'HT_TARE_seed42.mp4'
writer = cv2.VideoWriter(str(filename), cv2.VideoWriter_fourcc(*'mp4v'), 2, (1920, height))
assert writer.isOpened()
for elapsed in np.arange(0, 120.01, .5):
    panels = []
    for label, name, color in CASES:
        rows, values = DATA[label]
        index = max(0, np.searchsorted(values['elapsed_sim'], elapsed, side='right') - 1)
        path = np.array([xy(x, y) for x, y in zip(values['x'][:index+1], values['y'][:index+1])], dtype=np.int32)
        image = background.copy()
        bgr = tuple(int(color[i:i+2], 16) for i in (5, 3, 1))
        if len(path) > 1:
            cv2.polylines(image, [path], False, bgr, 2)
        cv2.circle(image, tuple(path[-1]), 5, bgr, -1)
        row = rows[index]
        lines = [f'{name} / CMU indoor + Scout / seed 42',
                 f'elapsed {elapsed:.1f}s / latest telemetry {values["elapsed_sim"][index]:.2f}s',
                 f'distance {values["distance_m"][index]:.2f}m / sampled free {values["observed_free_volume_m3"][index]:.2f}m3',
                 f'{row["execution"]} / {row["follower"]}',
                 'Recorded 2D trajectory over static preview points']
        for line_number, line in enumerate(lines):
            cv2.putText(image, line, (15, 25 + line_number*24), cv2.FONT_HERSHEY_SIMPLEX, .56, (20, 20, 20), 1, cv2.LINE_AA)
        panels.append(image)
    writer.write(np.concatenate(panels, axis=1))
writer.release()
cap = cv2.VideoCapture(str(filename))
count = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    assert frame.shape[:2] == (height, 1920)
    count += 1
cap.release()
assert count == 241
record = {'path': str(filename), 'frames': count, 'all_frames_decoded': True, 'fps': 2,
          'sha256': hashlib.sha256(filename.read_bytes()).hexdigest(), 'bytes': filename.stat().st_size,
          'left': 'p03_ht42', 'right': 'p02_tare42', 'alignment': 'Shared elapsed simulation time 0..120 at 0.5s increments, latest available sample; first sample held before it arrives.',
          'content': '2D saved ground-truth trajectory and telemetry over static CMU preview point cloud.'}
(OUT / 'PAIRED_VIDEO_VERIFICATION.json').write_text(json.dumps(record, indent=2)+'\n')
print(record)
