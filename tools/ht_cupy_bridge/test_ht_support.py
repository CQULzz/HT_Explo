import unittest
import numpy as np
from historical_elevation import HistoricalElevation
from ht_support import prepare_ht_context, preserve_rejected_obstacles
from pathlib import Path


class ObstacleContextTest(unittest.TestCase):
    def test_observed_wall_is_blocked_without_unknown_halo(self):
        z=np.zeros((91,91),np.float32);observed=np.ones_like(z,bool)
        rejected=np.zeros_like(z,bool);obstacle=np.full_like(z,np.nan)
        z[45,45]=np.nan;observed[45,45]=False;rejected[45,45]=True;obstacle[45,45]=1.7
        height,support,occupied,physical=prepare_ht_context(z,observed,rejected,obstacle,.041)
        self.assertEqual(height[45,45],np.float32(1.7))
        self.assertTrue(support[20,20]);self.assertTrue(occupied[20,20])
        self.assertTrue(support[20,10]);self.assertFalse(occupied[20,10])
        # An uncertain spike, without reliable obstacle history, still masks
        # the full receptive field rather than becoming apparent free ground.
        obstacle[:]=np.nan
        _,support,occupied,physical=prepare_ht_context(z,observed,rejected,obstacle,.041)
        self.assertFalse(support[20,10]);self.assertFalse(occupied.any())

    def test_missing_area_is_not_reconstructed_as_supported_ground(self):
        z=np.zeros((91,91),np.float32);known=np.ones_like(z,bool);known[25:65,25:65]=False;z[~known]=np.nan
        _,support,_,_=prepare_ht_context(z,known,np.zeros_like(known),np.full_like(z,np.nan),.041)
        self.assertFalse(support[20,20])

    def test_incompatible_surface_never_becomes_selected_ground(self):
        h=HistoricalElevation(.1,max_age_s=10);z=np.full((5,5),np.nan,np.float32);v=np.full_like(z,.001)
        z[2,2]=0;h.fuse(z,v,0,0,1)
        z[2,2]=1.7;h.fuse(z,v,0,0,2)
        crop,*_=h.window(0,0,5,4,reference_height=0)
        self.assertTrue(np.isnan(crop[2,2]))
        self.assertAlmostEqual(h.last_window_obstacle_elevation[2,2],1.7,places=5)
        # Expiry and missing floor reference do not create occupied/observed
        # context, and a genuinely new ground observation can clear a wall.
        h.window(0,0,5,13,reference_height=0)
        self.assertFalse(np.isfinite(h.last_window_obstacle_elevation).any())
        h.window(0,0,5,4,reference_height=np.nan)
        self.assertFalse(np.isfinite(h.last_window_obstacle_elevation).any())
        z[2,2]=0;h.fuse(z,v,0,0,5);crop,*_=h.window(0,0,5,5,reference_height=0)
        self.assertEqual(crop[2,2],0)
        self.assertFalse(np.isfinite(h.last_window_obstacle_elevation).any())

    def test_finite_fused_reject_is_occupied_context_never_free_ground(self):
        raw=np.zeros((91,91),np.float32);raw[45,64]=.46
        rejected=np.zeros_like(raw,bool);rejected[45,64]=True
        observed=~rejected;filtered=np.where(observed,raw,np.nan)
        before=np.full_like(raw,np.nan)
        obstacle=preserve_rejected_obstacles(before,raw,rejected)
        height,support,occupied,physical=prepare_ht_context(filtered,observed,rejected,obstacle,.041)
        self.assertTrue(support[20,20])  # Clear vehicle reference need not inherit a1m halo.
        self.assertTrue(occupied[20,39])  # Rejected cell is unsafe, not a filled free hole.
        self.assertTrue(physical[20,39])
        self.assertAlmostEqual(float(height[45,64]),.46,places=6)
        self.assertTrue(np.isnan(before).all())  # Do not mutate retained history.

    def test_unmeasured_reject_stays_unknown_and_keeps_context_veto(self):
        raw=np.zeros((91,91),np.float32);raw[45,64]=np.nan
        rejected=np.zeros_like(raw,bool);rejected[45,64]=True
        observed=~rejected;obstacle=preserve_rejected_obstacles(np.full_like(raw,np.nan),raw,rejected)
        _,support,occupied,physical=prepare_ht_context(raw,observed,rejected,obstacle,.041)
        self.assertFalse(support[20,20]);self.assertFalse(occupied.any())
        self.assertFalse(physical[20,39])

    def test_existing_obstacle_height_is_not_overwritten_by_a_quality_reject(self):
        obstacle=np.full((91,91),np.nan,np.float32);obstacle[45,45]=1.7
        raw=np.zeros_like(obstacle);rejected=np.zeros_like(raw,bool);rejected[45,45]=True
        retained=preserve_rejected_obstacles(obstacle,raw,rejected)
        self.assertAlmostEqual(float(retained[45,45]),1.7,places=6)
        with self.assertRaises(ValueError):preserve_rejected_obstacles(obstacle,raw[:2],rejected)

    def test_real_stopped_snapshot_retains_one_rejected_height_as_unsafe(self):
        snapshot=Path(__file__).resolve().parents[2]/'docs/results/ht_continuous_geometry_10min_2026-10-18/geometry_capture/stopped_snapshot.npz'
        with np.load(snapshot) as data:
            observed=data['history_input_valid']>=.5;rejected=data['history_rejected']>=.5
            # Old captures omit outer25 input cells' obstacle heights. Finite
            # placeholders reconstruct MASKS only, never substitute model input.
            old_obstacle=np.pad(np.where(data['ht_ht_obstacle']>=.5,1.7,np.nan),25,constant_values=np.nan)
            _,old_support,old_occupied,old_physical=prepare_ht_context(data['history_elevation'],observed,rejected,old_obstacle,data['ht_geometry'][2])
            np.testing.assert_array_equal((old_support|old_occupied)[40:-40,40:-40],(data['ht_ht_valid']>=.5)[40:-40,40:-40])
            self.assertFalse(old_support[120,120]);self.assertTrue(old_physical[120,120])
            obstacle=preserve_rejected_obstacles(old_obstacle,data['history_elevation_raw'],rejected)
            height,support,occupied,physical=prepare_ht_context(data['history_elevation'],observed,rejected,obstacle,data['ht_geometry'][2])
            self.assertEqual(int((np.isfinite(obstacle)&~np.isfinite(old_obstacle)).sum()),1)
            self.assertTrue(support[120,120]);self.assertTrue(occupied[105,140])
            self.assertTrue(physical[120,120])
            self.assertAlmostEqual(float(height[130,165]),.4596158,places=6)


if __name__=='__main__':unittest.main()
