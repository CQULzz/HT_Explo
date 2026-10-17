"""Integrated regression of quality rejection, height modes and surface selection.

These tests use the same processing order as CupyToHt.on_map without starting
ROS or the neural network, and check physical terrain outcomes rather than
only implementation-shaped array properties.
"""
import unittest

import numpy as np

from elevation_quality import preprocess_elevation
from historical_elevation import HistoricalElevation
from local_surface import SurfaceReferenceEstimator
from ht_support import prepare_ht_context


class SurfacePipelineTests(unittest.TestCase):
    def setUp(self):
        self.side = 81
        self.resolution = .04093567251461988
        self.history = HistoricalElevation(self.resolution)
        self.surface = SurfaceReferenceEstimator()
        self.variance = np.full((self.side, self.side), .01, np.float32)
        self.center = (0., 0.)

    def process(self, source_z, source_age, stamp_s, robot_z):
        source = preprocess_elevation(source_z, self.variance, self.resolution)
        measured = np.where(source.observed_quality, source_z, np.nan)
        self.history.record_rejections(source.rejected_mask,*self.center,stamp_s,
            stamp_s-source_age.astype(np.float64),elevation=source_z)
        count = self.history.fuse(measured, self.variance, *self.center, stamp_s,
                                   observation_time=stamp_s-source_age.astype(np.float64))
        align = lambda array, fill=np.nan: self.history.aligned_source_window(
            array, *self.center, self.side, fill_value=fill)
        current, variance, ages = (align(v) for v in (measured, self.variance, source_age))
        reference, stats = self.surface.estimate(current, variance, self.resolution,
                                                  ages, robot_z)
        preferred = np.where(np.isfinite(ages) & (ages <= 2.), current, np.nan)
        selected, selected_var, _, _ = self.history.window(
            *self.center, self.side, stamp_s, reference_height=reference,
            preferred_elevation=preferred)
        rejected = self.history.last_window_incompatible_mask.copy()
        selected[rejected] = np.nan
        quality = preprocess_elevation(selected, selected_var, self.resolution)
        rejected |= quality.rejected_mask
        return quality, rejected, stats, count

    def test_aging_source_variance_preserves_a_measured_wall_but_new_bad_data_blocks(self):
        z=np.full((self.side,self.side),.127,np.float32);z[35:41,35:41]+=.8
        self.process(z,np.zeros_like(z),1.,.877)
        self.variance[35:41,35:41]=1.
        age=np.zeros_like(z);age[35:41,35:41]=79.
        result,rejected,*_=self.process(z,age,80.,.877)
        self.assertAlmostEqual(result.height_m[37,37],.927,places=5)
        self.assertFalse(rejected[37,37])
        result,rejected,*_=self.process(z,np.zeros_like(z),81.,.877)
        self.assertTrue(rejected[37,37]);self.assertTrue(np.isnan(result.height_m[37,37]))
        self.variance[35:41,35:41]=.01;age[35:41,35:41]=4.
        result,rejected,*_=self.process(z,age,85.,.877)
        self.assertTrue(rejected[37,37])
        result,rejected,*_=self.process(z,np.zeros_like(z),86.,.877)
        self.assertFalse(rejected[37,37]);self.assertAlmostEqual(result.height_m[37,37],.927,places=5)

    def initialize_lower_floor(self):
        z = np.full((self.side, self.side), .127, np.float32)
        self.process(z, np.zeros_like(z), 1., .877)
        return z

    def upper_floor_source(self, lower):
        # The old rolling CuPy source still retains the first floor away from
        # fresh upper-floor points, and also contains an unseen hole upstairs.
        z = lower.copy()
        age = np.full(z.shape, 99., np.float32)
        z[20:61, 20:61] = 3.627
        age[20:61, 20:61] = 0.
        z[40, 40] = np.nan
        return z, age

    def test_floor_transition_hole_unknown_and_return_without_fake_heights(self):
        lower = self.initialize_lower_floor()
        upper_source, age = self.upper_floor_source(lower)
        result, _, stats, _ = self.process(upper_source, age, 100., 4.377)
        self.assertAlmostEqual(stats['reference_center_m'], 3.627, places=4)
        self.assertAlmostEqual(result.height_m[30, 30], 3.627, places=4)
        self.assertTrue(np.isnan(result.height_m[40, 40]))
        # History has plenty of known low-floor cells here, but upper-floor
        # planning must not fill the currently unseen surface with them.
        self.assertTrue(np.isnan(result.height_m[5, 5]))
        finite = result.height_m[np.isfinite(result.height_m)]
        np.testing.assert_allclose(finite, 3.627, atol=1e-5)
        returned, _, stats, _ = self.process(lower, np.zeros_like(lower), 200., .877)
        np.testing.assert_allclose(returned.height_m, .127, atol=1e-5)
        self.assertAlmostEqual(stats['reference_center_m'], .127, places=4)
        all_values = np.concatenate([t[0][np.isfinite(t[0])] for t in self.history.tiles.values()])
        self.assertTrue(np.all((abs(all_values-.127) < 1e-5) |
                               (abs(all_values-3.627) < 1e-5)))

    def test_stale_upper_cells_do_not_force_wrong_floor_when_returning(self):
        lower = self.initialize_lower_floor()
        upper, upper_age = self.upper_floor_source(lower)
        self.process(upper, upper_age, 100., 4.377)
        returned_source = lower.copy()
        ages = np.zeros_like(lower)
        returned_source[10:15, 10:15] = 3.627
        ages[10:15, 10:15] = 100.
        returned, _, stats, _ = self.process(returned_source, ages, 200., .877)
        mask = np.ones_like(lower, dtype=bool)
        mask[10:15, 10:15] = False
        np.testing.assert_allclose(returned.height_m[mask], .127, atol=1e-5)
        self.assertTrue(np.isnan(returned.height_m[10:15, 10:15]).all())
        self.assertTrue(self.history.last_window_incompatible_mask[10:15, 10:15].all())
        self.assertAlmostEqual(stats['reference_center_m'], .127, places=4)

    def test_real_obstacle_top_and_edges_are_preserved_on_current_floor(self):
        lower = self.initialize_lower_floor()
        upper = np.full_like(lower, 3.627)
        # Current observations of a 0.8m block and a tall 2.4m obstacle both
        # belong in the map despite being outside the reference-height gate.
        upper[20:25, 20:25] += .8
        upper[55:60, 55:60] += 2.4
        result, rejected, stats, _ = self.process(upper, np.zeros_like(lower), 100., 4.377)
        self.assertAlmostEqual(stats['reference_center_m'], 3.627, places=4)
        np.testing.assert_allclose(result.height_m[20:25, 20:25], 4.427, atol=1e-5)
        np.testing.assert_allclose(result.height_m[55:60, 55:60], 6.027, atol=1e-5)
        self.assertFalse(rejected[20:25, 20:25].any())
        self.assertFalse(rejected[55:60, 55:60].any())
        self.assertAlmostEqual(result.height_m[19, 20], 3.627, places=4)

    def test_quality_rejected_spike_cannot_reappear_from_history_or_padding(self):
        lower = self.initialize_lower_floor()
        outlier = lower.copy()
        outlier[40, 40] += .6
        result, rejected, _, _ = self.process(outlier, np.zeros_like(lower), 2., .877)
        self.assertTrue(rejected[40, 40])
        self.assertTrue(np.isnan(result.height_m[40, 40]))
        # A rejected finite return is occupied, never free ground. Its actual
        # height supplies context without invalidating every nearby network
        # query. Production forces all eight probabilities at occupied to 0;
        # the consumer dilates those forbidden cells by the vehicle footprint.
        height,support,occupied,physical=prepare_ht_context(result.height_m,
            result.observed_quality,rejected,self.history.last_window_obstacle_elevation,
            self.resolution)
        self.assertAlmostEqual(height[40,40],.727,places=5)
        self.assertTrue(occupied[15,15]);self.assertTrue(support[15,15])
        self.assertTrue(physical[15,15])
        self.assertTrue(support[15,0])
        # An actually unobserved hole remains unsupported; it has no occupied
        # measurement to justify treating it as known terrain.
        unknown=result.height_m.copy();unknown[25:56,25:56]=np.nan
        _,unknown_support,_,unknown_physical=prepare_ht_context(unknown,
            np.isfinite(unknown),rejected,np.full_like(unknown,np.nan),self.resolution)
        self.assertFalse(unknown_support[15,15]);self.assertFalse(unknown_physical[15,15])

    def test_retained_post_dropped_by_floor_selection_stays_occupied(self):
        # An initially measured confident tall post becomes old. Surface
        # selection hides its height after preferred-source expiry, but must
        # retain its occupied evidence instead of reverting to free ground.
        ground = np.full((self.side, self.side), .127, np.float32)
        ground[40, 40] = 1.7
        self.variance[40, 40] = .0009
        self.process(ground, np.zeros_like(ground), 1., .877)
        ages = np.full_like(ground, 3.)
        result, rejected, _, _ = self.process(ground, ages, 4., .877)
        self.assertTrue(np.isnan(result.height_m[40, 40]))
        self.assertTrue(rejected[40, 40])
        self.assertTrue(self.history.last_window_incompatible_mask[40, 40])
        _,support,occupied,_=prepare_ht_context(result.height_m,result.observed_quality,
            rejected,self.history.last_window_obstacle_elevation,self.resolution)
        self.assertTrue(occupied[15,15]);self.assertTrue(support[15,15])

    def test_ramp_reference_reuses_only_previously_observed_ramp_surface(self):
        x, y = np.meshgrid((40-np.arange(81))*self.resolution,
                           (40-np.arange(81))*self.resolution, indexing='ij')
        ramp = (.127+.15*x-.05*y).astype(np.float32)
        # An unknown location never gets an observation from the fitted plane.
        ramp[5, 5] = np.nan
        self.process(ramp, np.zeros_like(ramp), 1., .877)
        retained = ramp.copy()
        ages = np.full(ramp.shape, 99., np.float32)
        ages[20:61, 20:61] = 0.
        result, _, stats, _ = self.process(retained, ages, 100., .877)
        self.assertAlmostEqual(stats['reference_center_m'], .127, places=4)
        np.testing.assert_allclose(stats['slope_xy'], [.15, -.05], atol=.001)
        self.assertTrue(np.isnan(result.height_m[5, 5]))
        known = np.isfinite(ramp)
        # At most the metric bounded small-texture smoothing is allowed. The
        # reference plane must not flatten the ramp or synthesize its hole.
        np.testing.assert_allclose(result.height_m[known], ramp[known], atol=.0001)


if __name__ == '__main__':
    unittest.main()
