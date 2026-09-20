#!/usr/bin/env python3
"""Plot archived Scout height-bias results; not a new inference run."""
import csv
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path(__file__).parent/'evidence'
series={}
with (root/'historical_curves.csv').open() as f:
    for r in csv.DictReader(f):
        if '/sum_train_scout_infer_new1/' not in r['source']: continue
        model=r['source'].split('/')[2].split('_optimizer')[0]
        series.setdefault(model,[]).append((float(r['height_bias']),float(r['accuracy'])*100))
fig,ax=plt.subplots(figsize=(8,4.5))
for name,points in sorted(series.items()):
    label='Gradient HT' if 'grad_1' in name else ('Raw-height ViT' if 'vit' in name else 'Reference network')
    x,y=zip(*sorted(points)); ax.plot(x,y,label=label,linewidth=2)
ax.set(xlabel='Uniform height offset (m)',ylabel='Archived test accuracy (%)',title='Scout: robustness to uniform height offset',ylim=(45,95));ax.grid(alpha=.25);ax.legend()
fig.text(.5,.015,'Historical records; shared-terrain split; not a closed-loop driving test.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.04,1,1));fig.savefig(root/'height_bias.png',dpi=170);plt.close(fig)
