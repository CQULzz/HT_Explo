import unittest
import numpy as np
from local_surface import SurfaceReferenceEstimator


class SurfaceReferenceTests(unittest.TestCase):
    def setUp(self):
        self.res = .041
        self.x, self.y = np.meshgrid((40-np.arange(81))*self.res,
                                    (40-np.arange(81))*self.res, indexing='ij')
        self.v = np.full((81,81), .01, np.float32)
        self.age = np.zeros((81,81), np.float32)

    def test_ramp_is_reference_only_and_not_flattened(self):
        z = (.13+.15*self.x-.05*self.y).astype(np.float32)
        z[5:9,5:9] += .8
        estimator = SurfaceReferenceEstimator()
        reference, meta = estimator.estimate(z, self.v, self.res, self.age, robot_z=.88)
        self.assertAlmostEqual(reference[40,40], .13, places=4)
        np.testing.assert_allclose(meta['slope_xy'], [.15,-.05], atol=.003)
        self.assertAlmostEqual(estimator.offset_m, .75, places=4)
        self.assertAlmostEqual(z[6,6]-(.13+.15*self.x[6,6]-.05*self.y[6,6]), .8, places=5)

    def test_floor_transition_does_not_choose_retained_lower_floor(self):
        estimator = SurfaceReferenceEstimator()
        low = np.full((81,81), .127, np.float32)
        estimator.estimate(low, self.v, self.res, self.age, robot_z=.877)
        ref, meta = estimator.estimate(low, self.v, self.res, self.age+100, robot_z=4.377)
        self.assertAlmostEqual(ref[40,40], 3.627, places=4)
        self.assertEqual(meta['fresh_ground_cells'], 0)
        high = low.copy(); high[20:60,20:60] += 3.5
        ages = self.age+100; ages[20:60,20:60] = 0
        ref, _ = estimator.estimate(high, self.v, self.res, ages, robot_z=4.377)
        self.assertAlmostEqual(ref[40,40], 3.627, places=4)
        self.assertAlmostEqual(estimator.offset_m, .75, places=4)

    def test_unknown_reference_stays_unknown_without_odometry(self):
        estimator = SurfaceReferenceEstimator()
        reference, _ = estimator.estimate(np.full((81,81), np.nan), self.v, self.res, self.age)
        self.assertTrue(np.isnan(reference).all())


if __name__ == '__main__':
    unittest.main()
