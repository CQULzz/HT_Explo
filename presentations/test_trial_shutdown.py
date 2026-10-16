"""Integration regression: only a launch parent forwards the initial SIGINT."""
import json
from pathlib import Path
import shlex
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from run_scheduled_comparison import Trial


class ShutdownTest(unittest.TestCase):
    def test_forwarding_launcher_and_nonforwarding_run_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            child = root / 'child.py'
            child.write_text("""import signal, sys, time
from pathlib import Path
out=Path(sys.argv[1]); count=0; stopped=False
def stop(signum, frame):
 global count,stopped
 count+=1; out.write_text(str(count)); stopped=True
signal.signal(signal.SIGINT,stop)
out.with_suffix('.ready').touch()
while not stopped: time.sleep(.01)
time.sleep(.25)
""")
            parent = root / 'parent.py'
            parent.write_text("""import signal, subprocess, sys
child=subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2]])
def stop(signum,frame):
 if sys.argv[3]=='forward': child.send_signal(signum)
signal.signal(signal.SIGINT,stop)
sys.exit(child.wait())
""")
            trial = Trial('shutdown-test', root / 'logs', 225)
            try:
                for mode in ('forward', 'no-forward'):
                    output = root / mode
                    command = 'exec ' + ' '.join(shlex.quote(str(x)) for x in
                        [sys.executable, parent, child, output, mode])
                    proc = trial.start(mode, command)
                    proc.ht_forwards_sigint = mode == 'forward'
                    deadline = time.monotonic() + 5
                    while not output.with_suffix('.ready').exists() and time.monotonic() < deadline:
                        time.sleep(.01)
                    self.assertTrue(output.with_suffix('.ready').exists())
                trial.stop()
                for mode in ('forward','no-forward'):
                    self.assertEqual((root / mode).read_text(), '1')
                audit = json.loads((root/'logs/shutdown.json').read_text())
                self.assertEqual([x['returncode'] for x in audit if 'returncode' in x], [0,0])
                self.assertFalse(any(x.get('signal') in ('SIGTERM','SIGKILL') for x in audit))
            finally:
                if trial.processes: trial.stop()

    def test_orphan_is_detected_after_launcher_exits_zero(self):
        import psutil
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            parent=root/'leaky_parent.py'
            marker=root/'child.pid'
            parent.write_text("""import signal, subprocess, sys, time
from pathlib import Path
child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'])
Path(sys.argv[1]).write_text(str(child.pid))
signal.signal(signal.SIGINT,lambda *_:sys.exit(0))
while True: time.sleep(.01)
""")
            trial=Trial('orphan-test',root/'logs',225)
            proc=trial.start('leaky_launcher','exec '+shlex.quote(sys.executable)+' '+
                             shlex.quote(str(parent))+' '+shlex.quote(str(marker)))
            proc.ht_forwards_sigint=True
            try:
                deadline=time.monotonic()+5
                while not marker.exists() and time.monotonic()<deadline:time.sleep(.01)
                self.assertTrue(marker.exists())
                child=psutil.Process(int(marker.read_text()))
                trial.stop()
                audit=json.loads((root/'logs/shutdown.json').read_text())
                self.assertTrue(any(x.get('scope')=='remaining_descendant' for x in audit))
                self.assertEqual(audit[-1]['remaining_live_descendants'],[])
            finally:
                if trial.processes:trial.stop()
                if marker.exists():
                    try:
                        child=psutil.Process(int(marker.read_text()))
                        if child.status()!=psutil.STATUS_ZOMBIE:child.kill()
                    except psutil.Error:pass


if __name__ == '__main__':
    unittest.main()
