"""Exact parity of compiled multi-surface selection and the original gates."""
from copy import deepcopy

import numpy as np
import pytest

from historical_elevation import HistoricalElevation
from history_window import warmup_history_window


@pytest.mark.parametrize('selection', ['newest', 'reference', 'preferred', 'both'])
@pytest.mark.parametrize('stamp', [9., 12., 700.])
def test_compiled_selection_matches_numpy_with_rejections_expiry_and_rolling(selection, stamp):
    pytest.importorskip('numba')
    rng = np.random.default_rng(843)
    original = HistoricalElevation(.04, tile_size=8, window_backend='numpy')
    for tick in range(1, 10):
        z = rng.choice(np.array([0., .2, 1.3, 3.5, np.nan], np.float32), (31, 31))
        v = rng.uniform(.0001, .1, z.shape).astype(np.float32)
        x, y = .04*(tick % 3), -.04*(tick % 2)
        original.fuse(z, v, x, y, float(tick))
        rejected = rng.random(z.shape) < .04
        original.record_rejections(rejected, x, y, tick+.5,
                                   np.full(z.shape, tick+.5), elevation=z)
    compiled = deepcopy(original)
    compiled.window_backend, compiled._window_selector = warmup_history_window('numba')
    reference = rng.choice(np.array([0., 1.3, 3.5, np.nan], np.float32), (31, 31))
    preferred = rng.choice(np.array([0., .2, 1.3, 3.5, np.nan], np.float32), (31, 31))
    kwargs = {}
    if selection in ('reference', 'both'):
        kwargs['reference_height'] = reference
    if selection in ('preferred', 'both'):
        kwargs['preferred_elevation'] = preferred
    a = original.window(-.02, .06, 31, stamp, **kwargs)
    b = compiled.window(-.02, .06, 31, stamp, **kwargs)
    for before, after in zip(a, b):
        np.testing.assert_array_equal(before, after)
    np.testing.assert_array_equal(original.last_window_incompatible_mask, compiled.last_window_incompatible_mask)
    np.testing.assert_array_equal(original.last_window_obstacle_elevation, compiled.last_window_obstacle_elevation)
    for key in original.tiles:
        for before, after in zip(original.tiles[key], compiled.tiles[key]):
            np.testing.assert_array_equal(before, after)


def test_unrecognized_backend_is_rejected():
    with pytest.raises(ValueError):
        warmup_history_window('unknown')
