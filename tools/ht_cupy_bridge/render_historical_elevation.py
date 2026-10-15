#!/usr/bin/env python3
"""Render the full sparse historical map without changing the planner map."""
import argparse
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--reference-height', type=float,
                        help='Select a retained height mode near this elevation; no interpolation')
    parser.add_argument('--tolerance', type=float, default=1.0)
    args = parser.parse_args()
    with np.load(args.input) as saved:
        keys = saved['keys']
        tile_size = int(saved['tile_size'])
        resolution = float(saved['resolution'])
        layers = saved['elevation']
        if args.reference_height is not None:
            if 'elevation_modes' not in saved:
                raise ValueError('surface selection requires schema-2 multi-surface history')
            modes = saved['elevation_modes']
            distance = abs(modes-args.reference_height)
            usable = np.isfinite(modes) & (distance <= args.tolerance)
            choice = np.argmin(np.where(usable, distance, np.inf), axis=1, keepdims=True)
            layers = np.take_along_axis(modes, choice, axis=1)[:, 0]
            layers = np.where(np.any(usable, axis=1), layers, np.nan)
    if not len(keys):
        raise ValueError('historical map has no tiles')
    lo = keys.min(axis=0)
    hi = keys.max(axis=0)
    shape = (hi - lo + 1) * tile_size
    grid = np.full(tuple(shape), np.nan, np.float32)
    for key, tile in zip(keys, layers):
        start = (key - lo) * tile_size
        grid[start[0]:start[0]+tile_size, start[1]:start[1]+tile_size] = tile
    # Array rows/columns increase with world X/Y, so transpose for imshow.
    extent = [lo[0]*tile_size*resolution, (hi[0]+1)*tile_size*resolution,
              lo[1]*tile_size*resolution, (hi[1]+1)*tile_size*resolution]
    fig, ax = plt.subplots(figsize=(9, 7), constrained_layout=True)
    im = ax.imshow(grid.T, origin='lower', extent=extent, cmap='terrain',
                   interpolation='none', aspect='equal')
    selection = ('latest observed surface per XY' if args.reference_height is None else
                 f'surface near {args.reference_height:.3f} m (within {args.tolerance:.2f} m)')
    ax.set(xlabel='Map X (m)', ylabel='Map Y (m)',
           title=f'Global historical elevation | {selection}\n{np.isfinite(grid).sum():,} observed cells')
    fig.colorbar(im, ax=ax, label='Elevation (m)')
    fig.savefig(args.output, dpi=180)
    print(args.output)


if __name__ == '__main__':
    main()
