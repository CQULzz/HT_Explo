#!/usr/bin/env python3
"""Eight raw HT layers and the corresponding 0.6 m footprint hard gates."""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch, Circle
import numpy as np
from scipy.ndimage import binary_dilation


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    args = parser.parse_args()
    with np.load(args.input) as data:
        p = data['probabilities']
        valid = data['valid'].astype(bool)
        center = data['center']
        robot = data['robot']
        res = float(data['resolution'])
    metadata = json.loads(args.input.with_suffix('.json').read_text())
    n, m = valid.shape
    extent = [center[0]-n*res/2, center[0]+n*res/2,
              center[1]-m*res/2, center[1]+m*res/2]
    radius = int(np.ceil(.6/res)+1)
    dx, dy = np.mgrid[-radius:radius+1, -radius:radius+1]
    kernel = np.hypot(dx*res, dy*res) <= .6+np.sqrt(2)*res
    unknown = binary_dilation(~valid, structure=kernel, border_value=1)
    blocked = np.stack([binary_dilation(valid & (plane < .5), structure=kernel)
                        for plane in p])
    gates = np.where(blocked, 0, np.where(unknown, 1, 2))
    row = int(np.floor(n/2-(robot[0]-center[0])/res))
    col = int(np.floor(m/2-(robot[1]-center[1])/res))
    yaw_deg = float(np.degrees(robot[2]) % 360)
    metadata['robot_probability_8'] = p[:,row,col].tolist()
    metadata['robot_gate_8'] = gates[:,row,col].tolist()
    metadata['gate_codes'] = {'0':'blocked', '1':'unknown', '2':'allowed'}
    for kind in ('probabilities', 'hard_gate'):
        fig, axes = plt.subplots(2, 4, figsize=(16, 8.5), constrained_layout=True)
        cmap = plt.get_cmap('RdYlGn').copy()
        cmap.set_bad('#c5c5c5')
        for k, ax in enumerate(axes.flat):
            plane = np.where(valid,p[k],np.nan) if kind=='probabilities' else gates[k]
            im = ax.imshow(plane[::-1,::-1].T, origin='lower', extent=extent,
                           cmap=cmap if kind=='probabilities' else ListedColormap(['#c9453f','#bfc3c6','#4b985a']),
                           vmin=0, vmax=1 if kind=='probabilities' else 2,
                           interpolation='nearest')
            ax.add_patch(Circle(robot[:2], .6, fill=False, color='#1457c4', lw=1.5))
            ax.plot(*robot[:2], 'o', color='#1457c4', ms=4)
            ax.arrow(robot[0],robot[1],.7*np.cos(robot[2]),.7*np.sin(robot[2]),
                     head_width=.17, color='#1457c4', length_includes_head=True)
            ax.set(title=f'{k*45}° | robot P={p[k,row,col]:.2f}', xlabel='Map X (m)', ylabel='Map Y (m)')
            ax.set_aspect('equal')
            ax.grid(alpha=.15)
        if kind=='probabilities':
            fig.colorbar(im, ax=axes, shrink=.75, label='HT predicted traversability probability')
        else:
            fig.get_layout_engine().set(rect=(0, .065, 1, 1))
            fig.legend(handles=[Patch(color='#c9453f',label='Blocked: P < 0.5 within footprint'),
                                Patch(color='#bfc3c6',label='Unknown footprint'),
                                Patch(color='#4b985a',label='Allowed')], loc='lower center', ncol=3)
        fig.suptitle(f'Stopped robot HT {kind.replace("_"," ")} | {metadata["status"]}\n'
                     f'Robot ({robot[0]:.2f}, {robot[1]:.2f}) m, yaw {yaw_deg:.1f}° | blue circle: 0.6 m support radius', fontsize=15)
        output = args.input.with_name(f'stopped_ht_{kind}.png')
        fig.savefig(output,dpi=170)
        plt.close(fig)
        print(output)
    args.input.with_name('stopped_ht_analysis.json').write_text(json.dumps(metadata,indent=2)+'\n')


if __name__ == '__main__':
    main()
