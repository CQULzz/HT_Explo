import unittest
from audit_matched_tare_cleanup import classify


class CleanupTiming(unittest.TestCase):
    def test_no_exception_is_clean(self):
        self.assertTrue(classify(['normal planning'],100.)['clean_shutdown'])

    def test_post_window_sigint_exception_is_preserved_as_unclean(self):
        r=classify(['user interrupted with ctrl-c (SIGINT)',
                    '[node] [INFO] [100.2] [rclcpp]: signal_handler(SIGINT/SIGTERM)',
                    'terminate called after throwing'],100.)
        self.assertFalse(r['clean_shutdown'])
        self.assertTrue(r['exceptions_confirmed_after_measurement_and_stop'])
        self.assertTrue(r['no_in_measurement_exception_detected'])

    def test_early_exception_cannot_be_excused_by_later_stop(self):
        r=classify(['terminate called after throwing','user interrupted with ctrl-c (SIGINT)',
                    '[node] [INFO] [100.2] [rclcpp]: signal_handler(SIGINT/SIGTERM)'],100.)
        self.assertFalse(r['no_in_measurement_exception_detected'])

    def test_stop_before_window_end_cannot_be_excused(self):
        r=classify(['user interrupted with ctrl-c (SIGINT)',
                    '[node] [INFO] [99.2] [rclcpp]: signal_handler(SIGINT/SIGTERM)',
                    'terminate called after throwing'],100.)
        self.assertFalse(r['no_in_measurement_exception_detected'])


if __name__=='__main__':
    unittest.main()
