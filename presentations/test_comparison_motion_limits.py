import unittest
from comparison_motion_limits import limited_step


class MotionEnvelope(unittest.TestCase):
    def test_forward_reverse_and_yaw_caps_after_sustained_requests(self):
        for wanted, expected in [((4., 4.), (.5, .8)), ((-4., -4.), (-.25, -.8))]:
            state = (0., 0.)
            for _ in range(100):
                previous = state
                state, status = limited_step(state, wanted, .05)
                self.assertLessEqual(abs(state[0]-previous[0]), .025000001)
                self.assertLessEqual(abs(state[1]-previous[1]), .060000001)
            self.assertEqual(state, expected)

    def test_sign_change_obeys_acceleration(self):
        self.assertEqual(limited_step((.5, .8), (-.25, -.8), .05)[0], (.475, .74))

    def test_explicit_zero_stale_and_invalid_are_immediate_stops(self):
        for request, stale in [((0., 0.), False), ((.5, .8), True), ((float('nan'), .1), False)]:
            self.assertEqual(limited_step((.5, .8), request, .05, stale)[0], (0., 0.))

    def test_delayed_tick_does_not_release_large_step(self):
        state, _ = limited_step((0., 0.), (.5, .8), 10.)
        self.assertEqual(state, (.05, .12))


if __name__ == '__main__':
    unittest.main()
