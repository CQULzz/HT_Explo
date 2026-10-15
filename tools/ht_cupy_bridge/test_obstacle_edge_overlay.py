import unittest
import numpy as np
from elevation_quality import retain_recent_obstacle_edges


class ObstacleEdgeOverlayTests(unittest.TestCase):
    def test_new_step_is_not_halved_toward_old_ground(self):
        old = np.full((9,9), .127, np.float32)
        current = old.copy(); current[3:6,3:6] += .15
        fused = (old+current)/2
        var = np.full_like(old, .01); age = np.zeros_like(old)
        edges = current > .2
        selected, _, changed = retain_recent_obstacle_edges(fused,var,current,var,age,edges)
        np.testing.assert_allclose(selected[edges], current[edges])
        self.assertEqual(changed.sum(), 9)

    def test_old_unknown_or_lower_returns_do_not_clear_obstacle(self):
        history = np.array([[1.7,1.7,np.nan,1.7]], np.float32)
        current = np.array([[.127,2.,2.,2.]], np.float32)
        var = np.full_like(history,.01); age=np.array([[0.,3.,0.,-.1]])
        z, _, changed=retain_recent_obstacle_edges(history,var,current,var,age,np.ones_like(history,bool))
        np.testing.assert_array_equal(z,history)
        self.assertFalse(changed.any())


if __name__ == '__main__':unittest.main()
