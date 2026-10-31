"""Compare full stored surfaces/times against the retained NumPy update path."""
import numpy as np
import pytest
from historical_elevation import HistoricalElevation


def equal_history(a, b):
    assert a.frames == b.frames and set(a.tiles) == set(b.tiles)
    for key in a.tiles:
        for x, y in zip(a.tiles[key], b.tiles[key]):
            np.testing.assert_array_equal(x, y)


def test_compiled_fusion_preserves_all_modes_variances_and_observation_barriers():
    a = HistoricalElevation(.04, tile_size=8, window_backend='numpy')
    b = HistoricalElevation(.04, tile_size=8, window_backend='numba')
    rng = np.random.default_rng(1101)
    previous = None
    for i in range(60):
        z = (rng.integers(-3, 4, (19, 23)) * .8 + rng.normal(0, .02, (19, 23))).astype(np.float32)
        v = rng.uniform(0, .3, z.shape).astype(np.float32)
        z[rng.random(z.shape) < .12] = np.nan
        stamp = 100 + i * .1
        times = np.full(z.shape, stamp, np.float64)
        if i % 3 == 0 and previous is not None:
            times[:, :10] = previous[:, :10]  # retained source cells
        if i % 7 == 0:
            times[:5] = stamp + .02  # invalid future returns
        cx, cy = (-.12 if i % 2 else .04), -.20
        if i % 5 == 0:
            rejected = rng.random(z.shape) < .1
            for history in (a, b):
                history.record_rejections(rejected, cx, cy, stamp, times, elevation=z)
        assert a.fuse(z, v, cx, cy, stamp, observation_time=times) == b.fuse(
            z, v, cx, cy, stamp, observation_time=times)
        equal_history(a, b)
        for history in (a, b):
            history.window(cx, cy, 25, stamp, reference_height=np.float32(0))
        np.testing.assert_array_equal(a.last_window_incompatible_mask, b.last_window_incompatible_mask)
        np.testing.assert_array_equal(a.last_window_obstacle_elevation, b.last_window_obstacle_elevation)
        previous = times


@pytest.mark.parametrize('difference', [np.nextafter(np.float32(.6), np.float32(0)),
                                      np.float32(.6), np.nextafter(np.float32(.6), np.float32(1))])
def test_float32_association_boundary_and_first_mode_ties(difference):
    a = HistoricalElevation(.04, window_backend='numpy')
    b = HistoricalElevation(.04, window_backend='numba')
    for i, value in enumerate([0, 1.2, float(difference), float(-difference), .01]):
        for history in (a, b):
            history.fuse(np.full((5, 5), value, np.float32),
                         np.full((5, 5), .0001 if i % 2 else .2, np.float32), 0, 0, 10 + i)
        equal_history(a, b)
