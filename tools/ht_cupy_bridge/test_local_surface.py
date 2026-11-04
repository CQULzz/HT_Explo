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


def test_recorded_mixed_height_fit_does_not_quarantine_measured_floor():
    from pathlib import Path
    from height_evidence import qualify_height_evidence
    d=np.load(Path(__file__).with_name('test_fixtures')/'pcd_surface_260s.npz')
    z=d['source_height'].copy();flags=d['evidence_flags'].astype(int)
    z[(flags&2)!=0]=np.nan
    estimator=SurfaceReferenceEstimator(sensor_ground_offset_m=.23479)
    ref,meta=estimator.estimate(z,d['source_variance'],float(d['resolution']),
                              d['source_observation_age_s'],float(d['robot_z']))
    assert not meta['plane_fit'] and meta['fallback_reason']=='UNTRUSTED_LOCAL_PLANE'
    assert meta['fit_rms_m']>.025
    # Use the exact recorded diagnostic body-box subset, not an oracle fed to HT.
    n=z.shape[0];r=float(d['resolution']);cx,cy=d['map_xy'];px,py=d['robot_xy']
    xx,yy=np.meshgrid(cx+(n//2-np.arange(n))*r,cy+(n//2-np.arange(n))*r,indexing='ij')
    yaw=.6602011043625157;dx,dy=xx-px,yy-py
    bx=np.cos(yaw)*dx+np.sin(yaw)*dy;by=-np.sin(yaw)*dx+np.cos(yaw)*dy
    body=(abs(bx)<=.4825+r*.8)&(abs(by)<=.3695+r*.8)
    previously_unknown=body&((flags&32)!=0)
    assert previously_unknown.sum()==133
    when=260.-d['source_observation_age_s'].astype(np.float64)
    q=qualify_height_evidence(z,np.isfinite(z),np.zeros(z.shape,bool),
                             np.full_like(z,np.nan),when,when,ref,260.)
    assert q.observed[previously_unknown].all()
    assert not q.physical_unknown[previously_unknown].any()
    # Reference hints never fill actual holes or refresh their observation age.
    missing=~np.isfinite(z)
    assert not q.observed[missing].any()
    assert estimator.offset_m==.23479


def test_calibrated_mount_offset_does_not_drift_to_nearby_object_surface():
    z=np.full((81,81),-.58,np.float32);var=np.full_like(z,.001);age=np.zeros_like(z)
    estimator=SurfaceReferenceEstimator(sensor_ground_offset_m=.23479)
    for _ in range(30):
        ref,meta=estimator.estimate(z,var,.04,age,-.4)
    assert estimator.offset_m==.23479
    assert meta['plane_fit']


def test_untrusted_fit_without_ground_anchor_does_not_invent_reference():
    x,y=np.meshgrid((40-np.arange(81))*.04,(40-np.arange(81))*.04,indexing='ij')
    z=np.where((np.arange(81)[:,None]%2)==0,0.,.18)+np.zeros_like(x)
    ref,meta=SurfaceReferenceEstimator().estimate(z,np.full_like(z,.001),.04,np.zeros_like(z))
    assert not meta['plane_fit']
    assert np.isnan(ref).all()
