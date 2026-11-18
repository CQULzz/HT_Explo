"""Explain an interior HT window from recorded masks without changing evidence.

This reconstructs the strict NumPy context predicate for captures with
ht_qualify_evidence=false. It cannot recover the original variance/reject cause.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt


def explain(layers, metadata, x, y):
    if 'ht_uncertain_evidence' in layers:
        raise ValueError('Evidence-qualified captures require the original input context')
    resolution = metadata['resolution_m']
    rows, cols = layers['ht_valid'].shape
    cx, cy, _ = metadata['center_xyz']
    r = int(np.floor(rows / 2 - (x-cx) / resolution))
    c = int(np.floor(cols / 2 - (y-cy) / resolution))
    # The 51x51 field plus the nearest-known halo must fit in the published
    # crop; otherwise unrecorded outer input cells can change the predicate.
    margin = 25 + int(np.ceil(.25 / resolution))
    if not (margin <= r < rows-margin and margin <= c < cols-margin):
        raise ValueError('Query needs unrecorded outer context; reconstruction would be incomplete')
    known = (layers['ht_measured_valid'] >= .5) | (layers['ht_obstacle'] >= .5)
    near = distance_transform_edt(~known) * resolution <= .25
    uncertain = near & ~(layers['ht_observation_valid'] >= .5)
    window = (slice(r-25, r+26), slice(c-25, c+26))
    bad = np.argwhere(uncertain[window]) + [r-25, c-25]
    ratio = float(near[window].mean())
    return {
        'query_xy': [x, y], 'cell_rc': [r, c], 'window_size_cells': 51,
        'near_known_fraction': ratio, 'required_fraction': .9,
        'uncertain_cells': [
            {'cell_rc': [int(rr), int(cc)],
             'xy': [cx+(rows/2-rr-.5)*resolution, cy+(cols/2-cc-.5)*resolution]}
            for rr, cc in bad],
        'intrinsic_context_valid': bool(ratio >= .9 and not len(bad)),
        'reconstructed_context_valid': bool((ratio >= .9 and not len(bad)) or layers['ht_obstacle'][r, c] >= .5),
        'recorded_context_valid': bool(layers['ht_valid'][r, c] >= .5),
        'definition': 'Near-known support and uncertainty reconstructed from recorded measured/physical/occupied masks; qualify_evidence=false only. Occupied query cells are separately forced valid/zero-score by the publisher.',
        'limitations': 'Does not restore original height/variance/rejection timestamps, or unrecorded outer25 input cells. Does not apply persistent startup labels or establish safe route feasibility.',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map', type=Path, required=True)
    p.add_argument('--metadata', type=Path, required=True)
    p.add_argument('--x', type=float, required=True)
    p.add_argument('--y', type=float, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    metadata = json.loads(args.metadata.read_text())
    metadata = next(m for m in metadata['snapshots'] if m['file'] == args.map.name)
    with np.load(args.map) as layers:
        result = explain(layers, metadata, args.x, args.y)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False))
    print(json.dumps(result, allow_nan=False))


if __name__ == '__main__':
    main()
