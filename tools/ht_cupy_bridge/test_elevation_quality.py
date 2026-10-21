#!/usr/bin/env python3
"""Regression checks against unsafe terrain erasure and unknown filling."""
import unittest

import numpy as np

from elevation_quality import ElevationQualityConfig, preprocess_elevation


class ElevationQualityTest(unittest.TestCase):
    def process(self, z, std_m=.10, **kwargs):
        variance = np.full_like(z, std_m ** 2)
        return preprocess_elevation(z, variance, .04, ElevationQualityConfig(**kwargs))

    def test_centimeter_stripes_are_reduced_without_creating_observations(self):
        z = np.full((31, 31), .127, np.float32)
        z[:, ::2] += .009
        z[:, 1::2] -= .009
        z[:3, :3] = np.nan
        result = self.process(z)
        self.assertTrue(np.isnan(result.height_m[:3, :3]).all())
        original_rms = np.std(z[6:-6, 6:-6])
        filtered_rms = np.std(result.height_m[6:-6, 6:-6])
        self.assertLess(filtered_rms, original_rms * .60)
        np.testing.assert_array_equal(np.isfinite(result.height_m), np.isfinite(z))

    def test_uncertain_isolated_return_becomes_unknown_not_ground(self):
        z = np.zeros((15, 15), np.float32)
        z[7, 7] = .60
        result = self.process(z)
        self.assertTrue(result.rejected_mask[7, 7])
        self.assertFalse(result.observed_quality[7, 7])
        self.assertTrue(np.isnan(result.height_m[7, 7]))
        # Cells bordering the rejection are unchanged, not hole-filling output.
        np.testing.assert_array_equal(result.height_m[6:9, 6], z[6:9, 6])

    def test_confident_one_cell_post_is_preserved(self):
        z = np.zeros((15, 15), np.float32)
        z[7, 7] = .15  # 4 cm footprint: a median would erase this return.
        result = self.process(z, std_m=.003)
        self.assertTrue(result.observed_quality[7, 7])
        self.assertTrue(result.edge_mask[7, 7])
        self.assertEqual(result.height_m[7, 7], z[7, 7])
        self.assertEqual(result.stats["rejected_cells"], 0)

    def test_narrow_obstacle_with_multiple_returns_is_preserved(self):
        # A roughly 10 cm post yields two or three returns across its footprint.
        for side in (2, 3):
            z = np.zeros((21, 21), np.float32)
            z[9:9 + side, 9:9 + side] = .15
            result = self.process(z)
            np.testing.assert_array_equal(result.height_m[9:9 + side, 9:9 + side],
                                          z[9:9 + side, 9:9 + side])
            self.assertEqual(result.stats["rejected_cells"], 0)

    def test_vertical_obstacle_returns_are_not_rejected_as_flat_background(self):
        z = np.zeros((15, 15), np.float32)
        # A steep observed surface has several heights. Spatial isolation from
        # same-height returns is insufficient evidence to remove its center.
        z[6:9, 6:9] = [[.3, .5, .8], [.3, 1.2, .9], [.4, .6, .8]]
        result = self.process(z)
        self.assertFalse(result.rejected_mask[7, 7])
        self.assertEqual(result.height_m[7, 7], z[7, 7])

    def test_height_step_is_preserved_for_both_kernel_sizes(self):
        for radius in (1, 2):
            z = np.zeros((25, 25), np.float32)
            z[:, 12:] = .15
            result = self.process(z, radius_cells=radius)
            np.testing.assert_allclose(result.height_m, z, atol=1e-7)
            self.assertFalse(result.rejected_mask.any())

    def test_ramp_gradient_is_preserved(self):
        xx, yy = np.indices((31, 31), dtype=np.float32)
        z = .004 * xx + .007 * yy
        result = self.process(z)
        np.testing.assert_allclose(result.height_m[2:-2, 2:-2], z[2:-2, 2:-2], atol=1e-7)
        self.assertFalse(result.edge_mask.any())

    def test_nan_hole_and_one_sided_boundary_remain_unknown_or_unchanged(self):
        z = np.zeros((25, 25), np.float32)
        z[:, ::2] += .01
        z[10:15, 10:15] = np.nan
        result = self.process(z)
        self.assertTrue(np.isnan(result.height_m[10:15, 10:15]).all())
        np.testing.assert_array_equal(result.height_m[9, 11:14], z[9, 11:14])
        np.testing.assert_array_equal(result.height_m[15, 11:14], z[15, 11:14])
        np.testing.assert_array_equal(np.isfinite(result.height_m), np.isfinite(z))

    def test_sparse_ramp_has_no_one_sided_smoothing_bias(self):
        xx, yy = np.indices((41, 41), dtype=np.float32)
        z = .003*xx + .006*yy
        missing = np.random.default_rng(123).random(z.shape) < .25
        z[missing] = np.nan
        result = self.process(z)
        known = np.isfinite(z)
        np.testing.assert_allclose(result.height_m[known], z[known], atol=1e-7)
        self.assertTrue(np.isnan(result.height_m[missing]).all())
        self.assertGreater(result.stats['sparse_smoothable_cells'], 0)

    def test_sparse_texture_denoising_uses_real_opposite_pairs(self):
        z = np.zeros((61, 61), np.float32)
        z[:, ::2] = .009; z[:, 1::2] = -.009
        z[np.random.default_rng(41).random(z.shape) < .25] = np.nan
        sparse = self.process(z)
        full_only = self.process(z, sparse_symmetric=False)
        known = np.isfinite(z)
        self.assertGreater(sparse.stats['sparse_smoothable_cells'], 0)
        self.assertLess(np.std(sparse.height_m[known]), np.std(full_only.height_m[known])*.9)
        np.testing.assert_array_equal(sparse.observed_quality, full_only.observed_quality)
        np.testing.assert_array_equal(sparse.rejected_mask, full_only.rejected_mask)

    def test_small_steps_coherent_posts_and_confident_single_cells_are_preserved(self):
        for height in (.015, .03, .075):
            for side in (1, 2):
                z = np.zeros((25, 25), np.float32)
                z[12:12+side, 12:12+side] = height
                result = self.process(z, std_m=.003 if side == 1 else .1)
                np.testing.assert_array_equal(result.height_m, z)
                self.assertFalse(result.rejected_mask.any())
            z = np.zeros((25, 25), np.float32);z[:, 12:] = height
            result = self.process(z)
            np.testing.assert_allclose(result.height_m, z, atol=1e-7)

    def test_single_sided_sparse_support_does_not_extrapolate(self):
        z = np.full((9, 9), np.nan, np.float32)
        z[4, 4] = .01;z[3, 3:6] = 0.;z[4, 3] = 0.
        result = self.process(z)
        self.assertEqual(result.height_m[4, 4], z[4, 4])
        np.testing.assert_array_equal(np.isfinite(result.height_m), np.isfinite(z))

    def test_invalid_variance_is_rejected_and_inputs_are_not_modified(self):
        z = np.zeros((9, 9), np.float32)
        variance = np.full_like(z, .01)
        variance[2, 2] = -.1
        variance[4, 4] = np.inf
        original = z.copy()
        result = preprocess_elevation(z, variance, .04)
        self.assertTrue(result.rejected_mask[2, 2])
        self.assertTrue(result.rejected_mask[4, 4])
        self.assertTrue(np.isnan(result.height_m[2, 2]))
        np.testing.assert_array_equal(z, original)

    def test_low_variance_texture_is_kept_as_measured(self):
        z = np.zeros((15, 15), np.float32)
        z[:, ::2] += .01
        result = self.process(z, std_m=.003)
        np.testing.assert_array_equal(result.height_m, z)

    def test_no_grid_wraparound_or_unknown_border_fill(self):
        z = np.zeros((9, 9), np.float32)
        z[0, 0] = .5
        result = self.process(z)
        self.assertEqual(result.height_m[0, 0], z[0, 0])
        self.assertFalse(result.rejected_mask[0, 0])
        self.assertEqual(result.height_m[-1, -1], 0.)

    def test_all_unknown_map(self):
        z = np.full((5, 5), np.nan, np.float32)
        result = self.process(z)
        self.assertTrue(np.isnan(result.height_m).all())
        self.assertFalse(result.observed_quality.any())
        self.assertEqual(result.stats["observed_quality_cells"], 0)

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            ElevationQualityConfig(height_sigma_m=-.01)
        with self.assertRaises(ValueError):
            preprocess_elevation(np.zeros((2, 2)), np.zeros((2, 3)), .04)


if __name__ == '__main__':
    unittest.main()
