"""Estimate the vehicle's current ground surface for historical-layer selection.

Fresh heights near the vehicle anchor a robust plane. Odometry Z and a learned
mounting offset prevent retained measurements from a different floor becoming
the reference after a floor transition. The plane is a selection hint, never
new observed terrain or a replacement for unknown cells.
"""
import numpy as np


class SurfaceReferenceEstimator:
    def __init__(self, fresh_age_s=2.0, radius_m=1.5, sensor_ground_offset_m=None):
        self.fresh_age_s = float(fresh_age_s)
        self.radius_m = float(radius_m)
        self.offset_m = sensor_ground_offset_m

    def estimate(self, elevation, variance, resolution, ages=None, robot_z=None):
        z = np.asarray(elevation, np.float32)
        v = np.asarray(variance, np.float32)
        if z.ndim != 2 or z.shape != v.shape:
            raise ValueError('surface input shape mismatch')
        n, m = z.shape
        x, y = np.meshgrid((n//2-np.arange(n))*resolution,
                           (m//2-np.arange(m))*resolution, indexing='ij')
        valid = np.isfinite(z) & np.isfinite(v) & (v >= 0) & (v < 1)
        valid &= x*x+y*y <= self.radius_m**2
        if ages is not None:
            ages = np.asarray(ages)
            if ages.shape != z.shape:
                raise ValueError('surface age shape mismatch')
            valid &= np.isfinite(ages) & (ages >= -.001) & (ages <= self.fresh_age_s)
        expected = None
        if robot_z is not None and self.offset_m is not None:
            expected = float(robot_z)-self.offset_m
            valid &= abs(z-expected) <= .6
        elif robot_z is not None:
            valid &= (z <= robot_z+.2) & (z >= robot_z-2.)
        count = int(valid.sum())
        if count < 20:
            reference = np.full(z.shape, expected if expected is not None else np.nan, np.float32)
            return reference, {'fresh_ground_cells': count, 'reference_center_m': expected,
                               'slope_xy': [0., 0.], 'offset_m': self.offset_m, 'plane_fit': False}
        xx, yy, zz = x[valid], y[valid], z[valid]
        # Local obstacles are not a new floor. Start at the dominant low/median
        # surface, then fit only its compatible near-ground measurements.
        seed = expected if expected is not None else float(np.median(zz))
        close = abs(zz-seed) < .35
        if close.sum() < 20:
            center = expected if expected is not None else seed
            reference = np.full(z.shape, center, np.float32)
            return reference, {'fresh_ground_cells': count, 'reference_center_m': center,
                               'slope_xy': [0., 0.], 'offset_m': self.offset_m, 'plane_fit': False}
        A = np.c_[xx[close], yy[close], np.ones(close.sum())]
        b = zz[close].astype(np.float64)
        weights = 1/np.maximum(v[valid][close], .001)
        weights /= weights.max()
        coef = np.array([0., 0., np.median(b)])
        for _ in range(5):
            residual = abs(b-A@coef)
            robust = np.minimum(1., .025/np.maximum(residual, 1e-9))
            root = np.sqrt(weights*robust)
            coef = np.linalg.lstsq(A*root[:, None], b*root, rcond=None)[0]
        if np.hypot(*coef[:2]) > .75:
            coef = np.array([0., 0., np.median(b)])
        if expected is not None and abs(coef[2]-expected) > .25:
            coef = np.array([0., 0., expected])
        rms = float(np.sqrt(np.mean(np.minimum((b-A@coef)**2, .1**2))))
        if robot_z is not None:
            candidate = float(robot_z)-float(coef[2])
            if self.offset_m is None:
                self.offset_m = candidate
            elif abs(candidate-self.offset_m) < .1 and rms < .025:
                self.offset_m += .02*(candidate-self.offset_m)
        reference = (coef[0]*x+coef[1]*y+coef[2]).astype(np.float32)
        return reference, {'fresh_ground_cells': count, 'reference_center_m': float(coef[2]),
                           'slope_xy': coef[:2].tolist(), 'offset_m': self.offset_m,
                           'plane_fit': True, 'fit_rms_m': rms}
