import gc
import os
from pathlib import Path
import signal
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from inference_context_io import GracefulStop, save_immutable_npz


class ContextIOTest(unittest.TestCase):
    def test_numeric_arrays_roundtrip_without_replacing_an_earlier_stamp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'stamp.npz'
            expected = dict(source_stamp=12.5, mask=np.eye(8, dtype=bool),
                            height=np.arange(80, dtype=np.float32).reshape(8, 10))
            save_immutable_npz(path, **expected)
            with np.load(path, allow_pickle=False) as data:
                for name, value in expected.items():
                    np.testing.assert_array_equal(data[name], value)
            previous = path.read_bytes()
            with self.assertRaises(FileExistsError):
                save_immutable_npz(path, height=np.zeros((8, 10)))
            self.assertEqual(previous, path.read_bytes())
            self.assertEqual(list(Path(directory).glob('*.partial')), [])

    def test_sigint_during_array_write_finishes_the_current_snapshot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'stamp.npz'
            stop = GracefulStop()
            previous = signal.signal(signal.SIGINT, stop.request)
            write_array = np.lib.format.write_array
            calls = 0

            def signal_during_write(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    os.kill(os.getpid(), signal.SIGINT)
                    self.assertTrue(stop.requested)
                return write_array(*args, **kwargs)

            try:
                with patch('numpy.lib.format.write_array', side_effect=signal_during_write):
                    save_immutable_npz(path, first=np.arange(10000), second=np.ones(10000))
            finally:
                signal.signal(signal.SIGINT, previous)
            with np.load(path) as data:
                self.assertEqual(len(data['first']), 10000)
                np.testing.assert_array_equal(data['second'], np.ones(10000))
            self.assertEqual(list(Path(directory).glob('*.partial')), [])

    def test_raised_interruption_never_advertises_an_incomplete_npz(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'stamp.npz'
            errors = []
            previous = sys.unraisablehook
            sys.unraisablehook = lambda error: errors.append(str(error.exc_value))
            try:
                with patch('numpy.lib.format.write_array', side_effect=KeyboardInterrupt):
                    with self.assertRaises(KeyboardInterrupt):
                        save_immutable_npz(path, height=np.arange(10000))
                gc.collect()
            finally:
                sys.unraisablehook = previous
            self.assertFalse(path.exists())
            self.assertEqual(len(list(Path(directory).glob('*.partial'))), 1)
            self.assertEqual(errors, [])

    def test_publish_failure_preserves_the_existing_final_and_partial_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'stamp.npz'

            def concurrent_final(source, target):
                Path(target).write_bytes(b'previous immutable data')
                raise FileExistsError(target)

            with patch('inference_context_io.os.link', side_effect=concurrent_final):
                with self.assertRaises(FileExistsError):
                    save_immutable_npz(path, height=np.arange(100))
            self.assertEqual(path.read_bytes(), b'previous immutable data')
            self.assertEqual(len(list(Path(directory).glob('*.partial'))), 1)


if __name__ == '__main__':
    unittest.main()
