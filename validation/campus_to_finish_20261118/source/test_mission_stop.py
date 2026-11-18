import unittest
from mission_stop import MissionStopRule


class StopRuleTest(unittest.TestCase):
    def test_finish_far_from_home_is_not_success(self):
        rule = MissionStopRule((0., 0.))
        for t in range(50):
            self.assertEqual(rule.update(t, (4., 0.), (0., 0.), True, True, 0.), 'RUNNING')

    def test_home_without_finish_is_not_success(self):
        rule = MissionStopRule((0., 0.))
        for t in range(50):
            self.assertEqual(rule.update(t, (0., 0.), (0., 0.), False, True, 0.), 'RUNNING')

    def test_finish_return_and_continuous_hold(self):
        rule = MissionStopRule((0., 0.))
        for t in range(20):
            self.assertEqual(rule.update(t, (.2, 0.), (0., 0.), True, True, 0.), 'RUNNING')
        self.assertEqual(rule.update(20, (.2, 0.), (0., 0.), True, True, 0.), 'RETURNED_AND_STOPPED')

    def test_motion_and_stale_inputs_reset_hold(self):
        for command, fresh in [((.1, 0.), True), ((0., 0.), False)]:
            rule = MissionStopRule((0., 0.))
            for t in range(19):
                rule.update(t, (.2, 0.), (0., 0.), True, True, 0.)
            rule.update(19, (.2, 0.), command, True, fresh, 0.)
            self.assertEqual(rule.update(20, (.2, 0.), (0., 0.), True, True, 0.), 'RUNNING')

    def test_displacement_resets_hold(self):
        rule = MissionStopRule((0., 0.))
        for t in range(20):
            rule.update(t, (.2, 0.), (0., 0.), True, True, 0.)
        self.assertEqual(rule.update(20, (.3, 0.), (0., 0.), True, True, 0.), 'RUNNING')

    def test_blocked_is_failure_and_no_duration_cap(self):
        rule = MissionStopRule((0., 0.))
        for t in range(301):
            outcome = rule.update(t, (4., 0.), (0., 0.), True, True, 0.)
        self.assertEqual(outcome, 'PERSISTENT_BLOCKED')
        rule = MissionStopRule((0., 0.))
        for t in range(7201):
            self.assertEqual(rule.update(t, (t*.2, 0.), (.2, 0.), False, True, t*10.), 'RUNNING')

    def test_new_observation_and_phase_prevent_false_block(self):
        rule = MissionStopRule((0., 0.))
        for t in range(301):
            outcome = rule.update(t, (4., 0.), (0., 0.), t >= 150, True, t)
        self.assertEqual(outcome, 'RUNNING')


if __name__ == '__main__':
    unittest.main()
