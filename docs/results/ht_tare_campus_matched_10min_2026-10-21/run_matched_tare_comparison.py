#!/usr/bin/env python3
"""Sequential fresh600s measurements; analysis never runs during the other trial."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from run_scheduled_comparison import ROOT


def write(path, data):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
    tmp.replace(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--encoder', type=Path, required=True)
    ap.add_argument('--domain', type=int, default=226)
    ap.add_argument('--scenario', choices=['indoor', 'garage', 'campus'], default='indoor')
    a = ap.parse_args()
    folder = a.output.resolve()
    if folder.exists():
        raise RuntimeError('Refusing to overwrite '+str(folder))
    folder.mkdir(parents=True)
    candidate = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True).strip():
        raise RuntimeError('Freeze a clean candidate before recording')
    state = dict(git_head=candidate, duration_s=600, scene=a.scenario, state='RUNNING',
                 started_at=dt.datetime.now().astimezone().isoformat(),
                 runs=[dict(scenario=s, state='PENDING') for s in ['original', 'ht']])
    write(folder/'suite.json', state)
    programs = [
        [sys.executable, str(Path(__file__).with_name('run_matched_tare_original.py')),
         '--output', str(folder/'original'), '--duration', '600', '--scenario', a.scenario, '--domain', str(a.domain)],
        [sys.executable, str(Path(__file__).with_name('run_ht_endurance.py')),
         '--output', str(folder/'ht'), '--duration', '600', '--scenario', a.scenario, '--video-fps', '15', '--domain', str(a.domain+1)]]
    active = None
    observer = None
    handles = []
    def interrupted(signum, frame):
        raise SystemExit(128+signum)
    signal.signal(signal.SIGTERM, interrupted)
    try:
        for index, (row, program) in enumerate(zip(state['runs'], programs)):
            label = row['scenario']
            log = (folder/(label+'.runner.log')).open('w'); handles.append(log)
            active = subprocess.Popen(program, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            row.update(state='RECORDING', runner_pid=active.pid)
            print('STARTED', label, active.pid, flush=True)
            if label == 'ht':
                parameter_log = (folder/'ht.parameters.log').open('w'); handles.append(parameter_log)
                observer = subprocess.Popen([sys.executable, str(Path(__file__).with_name('capture_tare_multiscene_runtime.py')),
                    str(folder), '--domain', str(a.domain)], stdout=parameter_log, stderr=subprocess.STDOUT)
            deadline = time.monotonic()+1000
            while active.poll() is None:
                if time.monotonic()>deadline:
                    raise TimeoutError(label+' trial exceeded initialization+measurement deadline')
                try:
                    origin=json.loads((folder/label/'current/measurement_started.json').read_text())['wall_time']
                    row['elapsed_measurement_s']=min(600., time.time()-origin)
                except (OSError, ValueError, KeyError):
                    pass
                state['updated_at']=dt.datetime.now().astimezone().isoformat()
                write(folder/'suite.json', state)
                time.sleep(2)
            row['runner_returncode']=active.returncode
            row['state']='MEASURED' if active.returncode==0 and (folder/label/'COMPLETED.json').exists() else 'FAILED'
            write(folder/'suite.json', state)
            active=None
            if row['state']=='FAILED':
                raise RuntimeError(label+' measurement failed; retained original partial data')
            print('MEASURED', label, flush=True)
        state['state']='MEASUREMENTS_COMPLETE'
    except BaseException as error:
        state['state']='INTERRUPTED'
        state['error']=repr(error)
        raise
    finally:
        if active is not None and active.poll() is None:
            os.killpg(active.pid, signal.SIGINT)
            active.wait(timeout=50)
        state['finished_at']=dt.datetime.now().astimezone().isoformat()
        write(folder/'suite.json', state)
        write(folder/'FINISHED.json', state)
        if observer is not None:
            observer.wait(timeout=90)
        for handle in handles:
            handle.close()
    print('MEASUREMENTS_COMPLETE', folder, flush=True)


if __name__ == '__main__':
    main()
