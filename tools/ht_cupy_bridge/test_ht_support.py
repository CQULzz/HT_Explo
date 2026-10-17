import unittest
import numpy as np
from historical_elevation import HistoricalElevation
from ht_support import prepare_ht_context


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


if __name__=='__main__':unittest.main()
