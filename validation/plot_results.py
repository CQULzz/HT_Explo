#!/usr/bin/env python3
"""Plot recorded CMU trajectory progress and HT fault responses."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

root = Path(__file__).resolve().parent/'results'
fig, (progress, faults) = plt.subplots(2, 1, figsize=(10, 7), constrained_layout=True)
for case, label, color in [('baseline', 'HT disabled', '#666666'),
                           ('ht_initial', 'HT before waypoint fix', '#be3f3f'),
                           ('ht_fixed', 'HT after waypoint fix', '#146d9b')]:
    data = json.loads((root/case/'metrics.json').read_text())
    rows = [r for r in data['samples'] if r['t'] <= 45]
    progress.plot([r['t'] for r in rows], [r['distance'] for r in rows],
                  label=label, color=color, linewidth=2)
progress.set(xlabel='Wall time (s)', ylabel='Travel distance (m)',
             title='CMU garage: motion smoke tests, first 45 seconds')
progress.legend()
progress.grid(alpha=0.2)
data = json.loads((root/'ht_fixed'/'metrics.json').read_text())
rows = data['samples']
faults.plot([r['t'] for r in rows], [r['speed'] for r in rows], color='#146d9b', label='Commanded speed')
start = 0
for name, duration in data['phases']:
    if name != 'valid':
        faults.axvspan(start, start+duration, color='#be3f3f', alpha=0.14)
        faults.text(start+duration/2, 0.56, name.replace('_', '\n'),
                    ha='center', va='bottom', fontsize=8)
    start += duration
faults.set(xlabel='Wall time (s)', ylabel='Commanded linear speed (m/s)', ylim=(-0.05, 0.72),
           title='HT fault injection and recovery (synthetic HT maps)')
faults.grid(alpha=0.2)
fig.savefig(root/'motion_and_faults.png', dpi=180)
fig.savefig(root/'motion_and_faults.pdf')
