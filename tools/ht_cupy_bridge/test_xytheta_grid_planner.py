import unittest

import numpy as np

from xytheta_grid_planner import plan


class GridPlannerTest(unittest.TestCase):
    def setUp(self):
        self.x = np.arange(7, dtype=float)
        self.y = np.arange(7, dtype=float)
        self.p = np.ones((8, 7, 7), dtype=np.float32)
        self.safe = np.ones((7, 7), dtype=bool)
        self.kw = dict(p_min=.2, risk_weight=1, turn_cost=.22, reverse_factor=1.2)

    def run_plan(self, start, goal):
        return plan(self.x, self.y, self.p, self.safe, start, goal, **self.kw)

    def test_reverse_keeps_body_yaw_and_uses_opposite_ht_channel(self):
        states, actions, _, _ = self.run_plan((3, 3, 0), (2, 3, 0))
        self.assertEqual(actions, ["reverse"])
        self.assertEqual(states, [(3, 3, 0), (2, 3, 0)])
        self.p[4, 3, 3] = .01  # Westward travel is now forbidden.
        _, actions, _, _ = self.run_plan((3, 3, 0), (2, 3, 0))
        self.assertNotEqual(actions, ["reverse"])

    def test_rotation_is_an_explicit_state_transition(self):
        states, actions, _, _ = self.run_plan((3, 3, 0), (3, 3, 2))
        self.assertEqual(len(actions), 2)
        self.assertTrue(all(name.startswith("rotate") for name in actions))
        self.assertEqual(states[-1], (3, 3, 2))

    def test_no_diagonal_corner_cut(self):
        self.safe[:] = False
        self.safe[3, 3] = True
        self.safe[4, 4] = True
        with self.assertRaises(RuntimeError):
            self.run_plan((3, 3, 1), (4, 4, 1))


if __name__ == "__main__":
    unittest.main()
