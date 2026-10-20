#!/usr/bin/env python3
"""Reproduce the recorded 12-vertex cut without ROS, MCAP, models or simulation."""
from pathlib import Path
from collections import deque
import json
import numpy as np

root = Path(__file__).resolve().parent
with np.load(root / 'counterfactual_fixture.npz') as fixture:
    before, after = fixture['before'], fixture['after']
    colliding, history = fixture['current_colliding'], fixture['history']

# Actual TARE sample centres are .15 + .3*i. Quantising x*10 is incorrect
# because ties at half integers can alternate due to float32 roundoff.
def key(point):
    return tuple(np.round((point[:2] - .15) / .3).astype(int))

points = {key(v): v for v in np.vstack([before, after])}
terrain = {(int(i), int(j)): bool(value) for i, j, value in history}
ht_rejected = {k for k, v in points.items()
               if not terrain.get(tuple(np.floor(v[:2] / .2).astype(int)), True)}
physical_rejected = {key(v) for v in colliding}
start = min(points, key=lambda k: float(np.square(points[k][:2]).sum()))


def connected(remove):
    seen = {start}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                neighbor = (current[0] + dx, current[1] + dy)
                if (neighbor in points and neighbor not in remove and
                        neighbor not in seen and
                        abs(float(points[current][2]) - float(points[neighbor][2])) < .25):
                    seen.add(neighbor)
                    queue.append(neighbor)
    return seen

actual = {key(v) for v in after}
full = connected(set())
predicted = connected(ht_rejected)
result = dict(union_n=len(points), ht_rejected_union=len(ht_rejected),
              union_physically_colliding=len(physical_rejected & points.keys()),
              all_component=len(full), ht_mask_component=len(predicted),
              recorded_current_n=len(actual), missing=len(actual-predicted),
              extra=len(predicted-actual))
assert result == dict(union_n=516, ht_rejected_union=12,
                      union_physically_colliding=0, all_component=516,
                      ht_mask_component=283, recorded_current_n=283,
                      missing=0, extra=0), result
print(json.dumps(result, indent=2))
print('PASS: recorded candidate loss is exactly reproduced by the HT vertex cut.')
