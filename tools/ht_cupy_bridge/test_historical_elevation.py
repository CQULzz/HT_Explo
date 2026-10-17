#!/usr/bin/env python3
"""Regression checks for multiple surfaces, alignment and actual observation age."""
import tempfile
import unittest
from pathlib import Path

import numpy as np

from historical_elevation import HistoricalElevation


class HistoricalElevationTest(unittest.TestCase):
    def test_rejected_finite_height_is_forbidden_context_and_expires(self):
        h=HistoricalElevation(.1,max_age_s=10)
        z,v=self.one_cell(0);h.fuse(z,v,0,0,1)
        bad,_=self.one_cell(1.4)
        h.record_rejections(np.isfinite(bad),0,0,2,np.full(z.shape,2.),elevation=bad)
        crop,*_=h.window(0,0,5,3,reference_height=0)
        self.assertTrue(np.isnan(crop[2,2]))
        self.assertAlmostEqual(h.last_window_obstacle_elevation[2,2],1.4,places=5)
        crop,*_=h.window(0,0,5,13,reference_height=0)
        self.assertTrue(np.isnan(crop[2,2]))
        self.assertFalse(np.isfinite(h.last_window_obstacle_elevation).any())
        self.assertTrue(h.last_window_incompatible_mask[2,2])
        h.fuse(z,v,0,0,14)
        crop,*_=h.window(0,0,5,14,reference_height=0)
        self.assertEqual(crop[2,2],0)
        self.assertFalse(np.isfinite(h.last_window_obstacle_elevation).any())

    def test_variance_aging_cannot_reject_an_accepted_observation(self):
        h=HistoricalElevation(.1,max_age_s=100)
        z,v=self.one_cell(.8);h.fuse(z,v,0,0,1,observation_time=1)
        mask=np.isfinite(z);times=np.full(z.shape,1.)
        self.assertEqual(h.record_rejections(mask,0,0,80,times),0)
        crop,*_=h.window(0,0,5,80,reference_height=0)
        self.assertAlmostEqual(crop[2,2],.8,places=5)
        self.assertFalse(h.last_window_incompatible_mask[2,2])

    def test_new_rejected_measurement_persists_until_new_accepted_return(self):
        h=HistoricalElevation(.1,max_age_s=100)
        z,v=self.one_cell(0);h.fuse(z,v,0,0,1,observation_time=1)
        mask=np.isfinite(z);times=np.full(z.shape,2.)
        self.assertEqual(h.record_rejections(mask,0,0,2,times),1)
        crop,*_=h.window(0,0,5,20,reference_height=0)
        self.assertTrue(np.isnan(crop[2,2]));self.assertTrue(h.last_window_incompatible_mask[2,2])
        self.assertFalse(np.isfinite(h.last_window_obstacle_elevation).any())
        self.assertEqual(h.fuse(z,v,0,0,20,observation_time=1),0)
        self.assertEqual(h.fuse(z,v,0,0,20,observation_time=2),0)
        self.assertEqual(h.fuse(z,v,0,0,21,observation_time=21),1)
        crop,*_=h.window(0,0,5,21,reference_height=0)
        self.assertEqual(crop[2,2],0);self.assertFalse(h.last_window_incompatible_mask[2,2])

    def one_cell(self, z, size=5):
        values = np.full((size, size), np.nan, np.float32)
        variance = np.full_like(values, np.inf)
        values[size//2, size//2] = z
        variance[size//2, size//2] = .1
        return values, variance

    def test_history_survives_rolling_and_unknown_is_not_filled(self):
        history = HistoricalElevation(.1, max_age_s=100)
        z, variance = self.one_cell(2.)
        self.assertEqual(history.fuse(z, variance, 0, 0, 1), 1)
        self.assertEqual(history.fuse(np.full_like(z, np.nan), variance, 2, 0, 2), 0)
        crop, _, x, y = history.window(0, 0, 5, 3, reference_height=2)
        self.assertEqual(crop[2, 2], 2.)
        self.assertEqual(np.isfinite(crop).sum(), 1)
        self.assertEqual((x, y), (0., 0.))
        old, _, _, _ = history.window(0, 0, 5, 102)
        self.assertFalse(np.isfinite(old).any())

    def test_circular_buffer_and_fusion_within_same_surface(self):
        history = HistoricalElevation(.1)
        z, variance = self.one_cell(2.)
        history.fuse(z, variance, 0, 0, 1)
        z[2, 2] = 2.2
        history.fuse(np.roll(z, (1, 2), (0, 1)),
                     np.roll(variance, (1, 2), (0, 1)), 0, 0, 2, 1, 2)
        crop, _, _, _ = history.window(0, 0, 5, 2)
        self.assertGreater(crop[2, 2], 2.)
        self.assertLess(crop[2, 2], 2.2)
        self.assertEqual(np.isfinite(crop).sum(), 1)

    def test_floor_switch_and_return_do_not_make_intermediate_height(self):
        history = HistoricalElevation(.1)
        for value, stamp in ((.127, 1), (3.60, 2), (.127, 3)):
            z, variance = self.one_cell(value)
            history.fuse(z, variance, 0, 0, stamp)
            crop, _, _, _ = history.window(0, 0, 5, stamp, reference_height=value)
            self.assertAlmostEqual(crop[2, 2], value, places=5)
        all_heights = np.concatenate([tile[0][np.isfinite(tile[0])]
                                      for tile in history.tiles.values()])
        np.testing.assert_allclose(np.sort(all_heights), [.127, 3.60], atol=1e-6)
        preferred, _ = self.one_cell(3.60)
        upper, _, _, _ = history.window(0, 0, 5, 3, reference_height=3.60,
                                         preferred_elevation=preferred)
        self.assertAlmostEqual(upper[2, 2], 3.60, places=5)

    def test_new_floor_unknown_does_not_fall_back_to_known_lower_floor(self):
        history = HistoricalElevation(.1)
        z, variance = self.one_cell(.127)
        history.fuse(z, variance, 0, 0, 1)
        crop, _, _, _ = history.window(0, 0, 5, 2, reference_height=3.60)
        self.assertFalse(np.isfinite(crop).any())
        preferred, _ = self.one_cell(3.60)
        crop, _, _, _ = history.window(0, 0, 5, 2, reference_height=.127,
                                       preferred_elevation=preferred)
        self.assertTrue(np.isnan(crop[2, 2]))

    def test_current_preferred_observation_selects_surface_and_obstacle_top(self):
        history = HistoricalElevation(.1)
        for height, stamp in ((.127, 1), (3.60, 2)):
            z, variance = self.one_cell(height)
            history.fuse(z, variance, 0, 0, stamp)
        # A directly measured tall obstacle must not be erased by ground-height
        # selection. Per-cell source preference takes priority over scalar ref.
        preferred, _ = self.one_cell(3.60)
        crop, _, _, _ = history.window(0, 0, 5, 2, reference_height=.127,
                                       preferred_elevation=preferred)
        self.assertAlmostEqual(crop[2, 2], 3.60, places=5)

    def test_observation_time_prevents_retained_cells_refreshing_age(self):
        history = HistoricalElevation(.1, max_age_s=10)
        z, variance = self.one_cell(0.)
        self.assertEqual(history.fuse(z, variance, 0, 0, 1, observation_time=1), 1)
        self.assertEqual(history.fuse(z, variance, 0, 0, 8, observation_time=1), 0)
        self.assertEqual(history.fuse(z, variance, 0, 0, 8,
                                       observation_time=1.00005), 0)
        z[2, 2] = 3.
        self.assertEqual(history.fuse(z, variance, 0, 0, 9, observation_time=1), 0)
        crop, _, _, _ = history.window(0, 0, 5, 12)
        self.assertFalse(np.isfinite(crop).any())
        self.assertEqual(sum(np.isfinite(t[0]).sum() for t in history.tiles.values()), 1)
        self.assertEqual(history.fuse(z, variance, 0, 0, 12, observation_time=12), 1)
        crop, _, _, _ = history.window(0, 0, 5, 12, reference_height=3.)
        self.assertEqual(crop[2, 2], 3.)

    def test_circular_observation_time_and_out_of_order_input(self):
        history = HistoricalElevation(.1, max_age_s=10)
        z, variance = self.one_cell(0.)
        obs = np.full(z.shape, np.nan, np.float64)
        obs[2, 2] = 5.
        history.fuse(np.roll(z, (1, 2), (0, 1)),
                     np.roll(variance, (1, 2), (0, 1)), 0, 0, 8, 1, 2,
                     observation_time=np.roll(obs, (1, 2), (0, 1)))
        z[2, 2] = .5
        self.assertEqual(history.fuse(z, variance, 0, 0, 9, observation_time=4), 0)
        crop, _, _, _ = history.window(0, 0, 5, 9)
        self.assertEqual(crop[2, 2], 0.)
        expired, _, _, _ = history.window(0, 0, 5, 16)
        self.assertFalse(np.isfinite(expired).any())

    def test_ramp_continuity_across_rolling_windows_without_z_buckets(self):
        history = HistoricalElevation(.1, tile_size=4)
        for center_x, stamp in ((0., 1), (.2, 2), (.4, 3)):
            x = center_x + (2-np.arange(5))*.1
            z = np.broadcast_to((2*x)[:, None], (5, 5)).astype(np.float32)
            history.fuse(z, np.full_like(z, .01), center_x, 0, stamp)
        reference = np.broadcast_to((.4+(2-np.arange(5))*.2)[:, None], (5, 5))
        crop, _, _, _ = history.window(.2, 0, 5, 3, reference_height=reference)
        np.testing.assert_allclose(crop, reference, atol=1e-6)
        # A single continuously sloped floor can span several metres without
        # being split into global altitude bins.
        self.assertEqual(sum(np.isfinite(t[0]).sum() for t in history.tiles.values()), 45)

    def test_all_291_grid_cells_have_unique_bins_at_actual_cupy_centers(self):
        res = .04093567251461988
        history = HistoricalElevation(res)
        for center in ((0., 0.), (161.99999939*res, 810.99849047*res),
                       (1246.99664089*res, 1662.00260598*res)):
            gx, gy = history._source_indices(*center, (291, 291))
            self.assertEqual(len(np.unique(gx)), 291)
            self.assertEqual(len(np.unique(gy)), 291)
            np.testing.assert_array_equal(np.diff(gx), -np.ones(290))
            np.testing.assert_array_equal(np.diff(gy), -np.ones(290))
        z = np.zeros((291, 291), np.float32)
        history.fuse(z, np.full_like(z, .01), 0, 0, 1)
        self.assertEqual(sum(np.isfinite(t[0]).sum() for t in history.tiles.values()), 291**2)

    def test_source_alignment_matches_history_without_smoothing_or_fill(self):
        history = HistoricalElevation(.1, tile_size=4)
        logical = np.arange(35, dtype=np.float32).reshape(7, 5)*.01
        logical[1, 1] = np.nan
        physical = np.roll(logical, (2, 3), (0, 1))
        v = np.where(np.isfinite(physical), .01, np.inf)
        history.fuse(physical, v, -.20000000001, .30000000001, 1, 2, 3)
        preferred = history.aligned_source_window(physical, -.20000000001,
                                                   .30000000001, 9, 2, 3)
        crop, _, cx, cy = history.window(-.20000000001, .30000000001, 9, 1,
                                         preferred_elevation=preferred)
        np.testing.assert_allclose(crop, preferred, equal_nan=True)
        self.assertAlmostEqual(cx, -.2)
        self.assertAlmostEqual(cy, .3)
        self.assertEqual(np.isfinite(crop).sum(), 34)

    def test_layer_capacity_evicts_oldest_without_merging(self):
        history = HistoricalElevation(.1, max_layers=2)
        for z, stamp in ((0., 1), (3., 2), (6., 3)):
            values, variance = self.one_cell(z)
            history.fuse(values, variance, 0, 0, stamp)
        heights = np.concatenate([t[0][np.isfinite(t[0])] for t in history.tiles.values()])
        np.testing.assert_array_equal(np.sort(heights), [3., 6.])
        crop, _, _, _ = history.window(0, 0, 5, 3, reference_height=0.)
        self.assertFalse(np.isfinite(crop).any())

    def test_save_all_modes_and_compatible_latest_view(self):
        history = HistoricalElevation(.1)
        for z, stamp in ((.127, 1), (3.60, 2)):
            values, variance = self.one_cell(z)
            history.fuse(values, variance, 0, 0, stamp)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'history.npz'
            history.save(target)
            with np.load(target) as saved:
                self.assertEqual(saved['schema_version'], 2)
                self.assertEqual(saved['frames'], 2)
                self.assertEqual(np.isfinite(saved['elevation_modes']).sum(), 2)
                self.assertEqual(np.isfinite(saved['elevation']).sum(), 1)
                np.testing.assert_allclose(saved['elevation'][np.isfinite(saved['elevation'])], [3.60])
                np.testing.assert_array_equal(saved['world_origin'], [0., 0.])

    def test_empty_history_can_be_saved(self):
        history = HistoricalElevation(.1)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'history.npz'
            history.save(target)
            with np.load(target) as saved:
                self.assertEqual(saved['elevation_modes'].shape, (0, 4, 64, 64))
                self.assertEqual(saved['elevation'].shape, (0, 64, 64))

    def test_incompatible_confident_post_is_flagged_for_network_guard(self):
        history = HistoricalElevation(.1)
        z, variance = self.one_cell(1.7)
        variance[2, 2] = .0009
        history.fuse(z, variance, 0, 0, 1)
        crop, _, _, _ = history.window(0, 0, 5, 3, reference_height=.127)
        self.assertTrue(np.isnan(crop[2, 2]))
        self.assertTrue(history.last_window_incompatible_mask[2, 2])
        self.assertFalse(history.last_window_incompatible_mask[1, 1])
        history.window(0, 0, 5, 1000, reference_height=.127)
        self.assertTrue(history.last_window_incompatible_mask[2, 2])

    def test_newer_post_blocks_resurrection_of_old_ground_until_observed_clear(self):
        history = HistoricalElevation(.1)
        for height, stamp in ((.127, 1), (1.7, 2)):
            z, variance = self.one_cell(height)
            variance[2, 2] = .0009
            history.fuse(z, variance, 0, 0, stamp)
        for now in (5, 1000):
            crop, _, _, _ = history.window(0, 0, 5, now, reference_height=.127)
            self.assertTrue(np.isnan(crop[2, 2]))
            self.assertTrue(history.last_window_incompatible_mask[2, 2])
        cleared, variance = self.one_cell(.127)
        history.fuse(cleared, variance, 0, 0, 1001)
        crop, _, _, _ = history.window(0, 0, 5, 1001, reference_height=.127,
                                       preferred_elevation=cleared)
        self.assertAlmostEqual(crop[2, 2], .127, places=5)
        self.assertFalse(history.last_window_incompatible_mask[2, 2])

    def test_recent_small_obstacle_is_kept_instead_of_closer_old_ground(self):
        history = HistoricalElevation(.1)
        for height, stamp in ((.127, 1), (.927, 2)):
            z, variance = self.one_cell(height)
            history.fuse(z, variance, 0, 0, stamp)
        crop, _, _, _ = history.window(0, 0, 5, 5, reference_height=.127)
        self.assertAlmostEqual(crop[2, 2], .927, places=5)
        self.assertFalse(history.last_window_incompatible_mask[2, 2])

    def test_other_floor_unknown_is_flagged_but_selected_floor_is_not(self):
        history = HistoricalElevation(.1)
        z, variance = self.one_cell(.127)
        history.fuse(z, variance, 0, 0, 1)
        history.window(0, 0, 5, 3, reference_height=3.627)
        self.assertTrue(history.last_window_incompatible_mask[2, 2])
        history.window(0, 0, 5, 3, reference_height=.127)
        self.assertFalse(history.last_window_incompatible_mask.any())

    def test_tile_limit_and_shape_errors_are_explicit(self):
        history = HistoricalElevation(.1, tile_size=4, max_tiles=1)
        z, variance = self.one_cell(0., 1)
        history.fuse(z, variance, 0, 0, 1)
        with self.assertRaises(MemoryError):
            history.fuse(z, variance, 2, 0, 2)
        with self.assertRaises(ValueError):
            history.fuse(z, variance, 0, 0, 3, observation_time=np.zeros((2, 2)))
        with self.assertRaises(ValueError):
            history.window(0, 0, 5, 3, preferred_elevation=np.zeros((1, 1)))


if __name__ == '__main__':
    unittest.main()
