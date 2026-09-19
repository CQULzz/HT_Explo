"""Small independent fixtures for quantities used in the experiment report."""
import unittest

import numpy as np

from analyze_exploration import low_motion_intervals, summarize
from coverage_metrics import decode_keys, voxel_keys


class MetricsTest(unittest.TestCase):
    def test_world_voxels_and_reference_matching(self):
        points = [[-.01,0,0],[.01,0,0],[.49,0,0],[.5,0,0],
                  [float('nan'),0,0],[0,float('inf'),0]]
        keys=voxel_keys(points)
        self.assertEqual(set(map(tuple,decode_keys(keys))),
                         {(-.25,.25,.25),(.25,.25,.25),(.75,.25,.25)})
        self.assertEqual(len(set(keys)&set(voxel_keys([[.2,.1,.1],[20,0,0]]))),1)
        self.assertEqual(len(voxel_keys(np.empty((0,3)))),0)

    def test_low_motion_threshold_and_finish(self):
        rows=[]
        distance=0
        for t in range(31):
            if t and not (8<t<=14 or 20<t<=24):
                distance+=.5
            rows.append(dict(t=t,planar_distance_m=distance))
        self.assertEqual(low_motion_intervals(rows,30),
                         [dict(start_s=8.,end_s=14.,duration_s=6.)])
        self.assertEqual(low_motion_intervals(rows,30,finish_time=10),[])
        stationary=[dict(t=t,planar_distance_m=0) for t in range(21)]
        self.assertEqual(low_motion_intervals(stationary,20),
                         [dict(start_s=5.,end_s=20.,duration_s=15.)])

    def test_summary_uses_added_coverage_and_overall_runtime(self):
        rows=[]
        for t in (0,5,10):
            rows.append(dict(t=t,reference_hits=50+30*t,new_reference_hits=30*t,
                             reference_hit_pct=(50+30*t)/10,observed_voxels=60+40*t,
                             new_observed_voxels=40*t,cmu_hit_voxel_volume_m3=60+t,
                             planar_distance_m=t*.5,distance_m=t*.5,allowed=True,
                             position=[t*.5,0,.75],scans=t*5,scan_age_s=.1,sim_clock=t+10))
        data=dict(final=True,duration_requested_s=10,samples=rows,
                  finished=False,finish_time_s=None,
                  planning_cycles=[dict(overall_ms=x) for x in (100,200,300)])
        result=summarize(data,'ht',1)
        self.assertEqual(result['new_reference_hits'],300)
        self.assertEqual(result['reference_hit_pct'],35)
        self.assertEqual(result['new_reference_hits_per_planar_m'],60)
        self.assertEqual(result['mean_new_reference_hits_over_time'],150)
        self.assertEqual(result['scan_rate_hz'],5)
        self.assertEqual(result['sim_clock_rate'],1)
        self.assertEqual(result['runtime_median_ms'],200)
        self.assertEqual(result['runtime_p95_ms'],290)
        self.assertEqual(result['low_motion_total_s'],0)
        data['final']=False
        with self.assertRaises(ValueError):
            summarize(data,'ht',1)


if __name__=='__main__':
    unittest.main()
