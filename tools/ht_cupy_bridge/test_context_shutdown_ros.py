"""Exercise the actual bridge main-loop shutdown with SIGINT inside a write."""
import json
import os
from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from rclpy.node import Node

import cupy_to_ht as bridge
from inference_context_io import save_immutable_npz


class BridgeShutdownTest(unittest.TestCase):
    def test_actual_main_finishes_callback_and_history_before_context_shutdown(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            write_array = np.lib.format.write_array
            calls = 0
            before = signal.getsignal(signal.SIGINT)

            def interrupt_first_write(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    os.kill(os.getpid(), signal.SIGINT)
                return write_array(*args, **kwargs)

            class History:
                def save(self, path):
                    save_immutable_npz(path, elevation=np.ones((3, 3)))

            class CallbackNode(Node):
                def __init__(self):
                    super().__init__('context_shutdown_regression')
                    self.history = History()
                    self.diagnostics = []
                    self.create_timer(.01, self.write)

                def write(self):
                    save_immutable_npz(output / 'context.npz', first=np.arange(10000),
                                       probabilities=np.ones((8, 10, 10)))
                    self.diagnostics.append({'callback_completed': True})

            with patch.object(bridge, 'CupyToHt', CallbackNode), \
                    patch.dict(os.environ, HT_HISTORY_DUMP=str(output / 'history.npz'),
                               HT_DIAGNOSTICS_DUMP=str(output / 'diagnostics.json')), \
                    patch('numpy.lib.format.write_array', side_effect=interrupt_first_write):
                bridge.main()
            self.assertEqual(signal.getsignal(signal.SIGINT), before)
            self.assertFalse(bridge.rclpy.ok())
            with np.load(output / 'context.npz') as data:
                self.assertEqual(data['probabilities'].shape, (8, 10, 10))
            with np.load(output / 'history.npz') as data:
                self.assertEqual(data['elevation'].shape, (3, 3))
            self.assertEqual(json.loads((output / 'diagnostics.json').read_text()),
                             [{'callback_completed': True}])
            self.assertEqual(list(output.glob('*.partial')), [])


if __name__ == '__main__':
    unittest.main()
