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
from diagnostic_history import DiagnosticHistory


class BridgeShutdownTest(unittest.TestCase):
    def test_main_exports_all_records_after_online_history_eviction(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'diagnostics.json'
            class CallbackNode(Node):
                def __init__(self):
                    super().__init__('bounded_diagnostic_shutdown')
                    self.history=None;self.n=0
                    self.diagnostics=DiagnosticHistory(2,path)
                    self.create_timer(.01,self.record)
                def record(self):
                    self.diagnostics.append({'source':self.n});self.n+=1
                    if self.n==6:os.kill(os.getpid(),signal.SIGINT)
            with patch.object(bridge,'CupyToHt',CallbackNode), \
                    patch.dict(os.environ,HT_DIAGNOSTICS_DUMP=str(path),HT_HISTORY_DUMP=''):
                bridge.main()
            self.assertEqual(json.loads(path.read_text()),[{'source':i} for i in range(6)])
            status=json.loads(Path(str(path)+'.status.json').read_text())
            self.assertEqual(status['retained'],2)
            self.assertEqual(status['archive_written'],6)
            self.assertFalse(bridge.rclpy.ok())

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
