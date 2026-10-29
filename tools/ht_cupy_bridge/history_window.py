"""Compiled historical surface selection, with the NumPy path as fallback.

No fast math, parallel reductions, interpolation, or changes to association,
age, rejection and obstacle gates. Each cell retains first-index tie breaking.
"""
from functools import lru_cache
import warnings

import numpy as np


def _select_tile(z, variance, last, preferred, reference, rejection_time,
                 rejection_height, stamp, max_age, association_gap,
                 reference_tolerance, explicit_selection):
    layers, rows, columns = z.shape
    height = np.full((rows, columns), np.nan, np.float32)
    output_variance = np.full((rows, columns), np.inf, np.float32)
    incompatible = np.zeros((rows, columns), np.bool_)
    obstacle = np.full((rows, columns), np.nan, np.float32)
    for i in range(rows):
        for j in range(columns):
            p, r = preferred[i, j], reference[i, j]
            has_preferred, has_reference = np.isfinite(p), np.isfinite(r)
            has_target = has_preferred or has_reference
            target = p if has_preferred else r
            tolerance = association_gap if has_preferred else reference_tolerance
            mode, newest_mode = 0, 0
            best, newest_score, max_last = -np.inf, -np.inf, -np.inf
            found, any_height = False, False
            for k in range(layers):
                value, seen = z[k, i, j], last[k, i, j]
                # Match np.max's NaN propagation, though normal fused times
                # are finite or -inf by the observation-time contract.
                if seen > max_last or np.isnan(seen):
                    max_last = seen
                finite = np.isfinite(value)
                any_height = any_height or finite
                newest = seen if finite else -np.inf
                if newest > newest_score or (np.isnan(newest) and not np.isnan(newest_score)):
                    newest_mode, newest_score = k, newest
                distance = abs(value-target)
                usable = (finite and stamp-seen <= max_age and seen <= stamp+1e-3
                          and (not has_target or distance <= tolerance))
                if usable:
                    found = True
                    score = -distance if has_preferred else seen
                    if score > best:
                        mode, best = k, score
            chosen_time = last[mode, i, j]
            newest_z, newest_time = z[newest_mode, i, j], last[newest_mode, i, j]
            newer_incompatible = (not has_preferred and has_reference
                and newest_time > chosen_time+1e-3
                and abs(newest_z-r) > reference_tolerance)
            rejected_at = rejection_time[i, j]
            newer_rejection = (rejected_at > max_last+1e-3
                and rejected_at <= stamp+1e-3 and stamp-rejected_at <= max_age)
            found = (found and not newer_incompatible and not newer_rejection
                     and (not explicit_selection or has_target))
            incompatible[i, j] = (any_height and not found) or newer_rejection
            occupied = (not found and not newer_rejection and has_reference
                and np.isfinite(newest_z) and newest_time <= stamp+1e-3
                and stamp-newest_time <= max_age
                and abs(newest_z-r) > reference_tolerance)
            if occupied:
                obstacle[i, j] = newest_z
            if newer_rejection and np.isfinite(rejection_height[i, j]):
                obstacle[i, j] = rejection_height[i, j]
            if found:
                height[i, j], output_variance[i, j] = z[mode, i, j], variance[mode, i, j]
    return height, output_variance, incompatible, obstacle


@lru_cache(maxsize=3)
def warmup_history_window(backend='auto'):
    """Resolve/compile once before subscriptions, rather than on a live frame."""
    if backend not in ('auto', 'numpy', 'numba'):
        raise ValueError('ht_history_backend must be auto, numpy or numba')
    if backend == 'numpy':
        return 'numpy', None
    try:
        from numba import njit
        selector = njit(cache=True, fastmath=False)(_select_tile)
        plane = np.zeros((2, 2), np.float32)
        for strided in (False, True):
            # Advanced tile indexing produces (layers, rows, columns) with
            # layers innermost. Warm that signature as well as dense arrays.
            z = (np.zeros((2, 2, 4), np.float32).transpose(2, 0, 1) if strided
                 else np.zeros((4, 2, 2), np.float32))
            last = (np.zeros((2, 2, 4), np.float64).transpose(2, 0, 1) if strided
                    else np.zeros(z.shape, np.float64))
            selector(z, z.copy(order='K'), last, plane, plane.copy(),
                     np.full(plane.shape, -np.inf, np.float64),
                     np.full(plane.shape, np.nan, np.float32), 1., 600., .6, 1., True)
        return 'numba', selector
    except Exception as error:
        if backend == 'numba':
            raise
        warnings.warn(f'Compiled history selection unavailable; using NumPy: {error}', RuntimeWarning)
        return 'numpy', None
