"""Compiled updates for independent FP32 history cells, without fast math.

The vectorized NumPy implementation remains the reference/fallback. Explicit
FP32 intermediate rounding matches its ufunc sequence, including gain limits.
"""
from functools import lru_cache
import warnings
import numpy as np


def _update_cells(mean, variance, last, lx, ly, height, incoming_variance,
                  observed, rejected_time, association_gap):
    updates = 0
    layers = mean.shape[0]
    for i in range(len(lx)):
        x, y = lx[i], ly[i]
        newest = -np.inf
        for k in range(layers):
            seen = last[k, x, y]
            if np.isnan(seen):
                newest = np.nan
                break
            if seen > newest:
                newest = seen
        if rejected_time is not None:
            rejected = rejected_time[x, y]
            if np.isnan(rejected) or rejected > newest:
                newest = rejected
        if not observed[i] > newest + 1e-3:
            continue

        nearest, best, free, oldest = 0, np.float32(np.inf), -1, 0
        oldest_time = last[0, x, y]
        for k in range(layers):
            value = mean[k, x, y]
            if np.isfinite(value):
                distance = abs(np.float32(value - height[i]))
                if distance < best:
                    nearest, best = k, distance
            elif free < 0:
                free = k
            if last[k, x, y] < oldest_time:
                oldest, oldest_time = k, last[k, x, y]
        matched = best <= association_gap
        mode = nearest if matched else (free if free >= 0 else oldest)
        z, v = height[i], incoming_variance[i]
        if matched:
            old_z, old_v = mean[mode, x, y], variance[mode, x, y]
            denominator = np.float32(np.float32(old_v + v) + np.float32(1e-5))
            gain = np.float32(old_v / denominator)
            gain = min(max(gain, np.float32(.05)), np.float32(.5))
            z = np.float32(old_z + np.float32(gain * np.float32(z - old_z)))
            v = np.float32(np.float32(np.float32(1.) - gain) * old_v
                           + np.float32(gain * v))
            if not np.isnan(v):
                v = max(np.float32(.0001), v)
        mean[mode, x, y], variance[mode, x, y], last[mode, x, y] = z, v, observed[i]
        updates += 1
    return updates


@lru_cache(maxsize=3)
def warmup_history_fusion(backend='auto'):
    if backend not in ('auto', 'numpy', 'numba'):
        raise ValueError('Unknown history fusion backend')
    if backend == 'numpy':
        return 'numpy', None
    try:
        from numba import njit
        kernel = njit(cache=True, fastmath=False, error_model='numpy')(_update_cells)
        for rejection in (None, np.full((2, 2), -np.inf, np.float64)):
            z = np.full((4, 2, 2), np.nan, np.float32)
            v = np.full_like(z, np.inf)
            last = np.full(z.shape, -np.inf, np.float64)
            for _ in range(2):
                kernel(z, v, last, np.array([0], np.int64), np.array([0], np.int64),
                       np.zeros(1, np.float32), np.ones(1, np.float32),
                       np.ones(1, np.float64), rejection, np.float32(.6))
        return 'numba', kernel
    except Exception as error:
        if backend == 'numba':
            raise
        warnings.warn(f'Compiled history fusion unavailable; using NumPy: {error}', RuntimeWarning)
        return 'numpy', None
