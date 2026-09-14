#!/usr/bin/env python3
"""Run one isolated CMU garage case; source both workspaces first."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--phases', default='valid:60')
    parser.add_argument('--disabled', action='store_true')
    parser.add_argument('--uncalibrated', action='store_true')
    parser.add_argument('--weight', type=float, default=1.0)
    parser.add_argument('--probabilities', default='0.9,0.9,0.9,0.9,0.9,0.9,0.9,0.9')
    parser.add_argument('--domain', type=int, default=71)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    config = {'/**': {'ros__parameters': {
        'ht_enabled': not args.disabled,
        'ht_directions_calibrated': not args.uncalibrated,
        'ht_weight': args.weight}}}
    # JSON is valid YAML and preserves parameter types.
    (out/'parameters.yaml').write_text(json.dumps(config, indent=2))
    env = dict(os.environ, ROS_DOMAIN_ID=str(args.domain),
               GZ_PARTITION=f'ht_validation_{os.getpid()}')
    processes = []
    logs = []

    def start(command, name):
        log = (out/f'{name}.log').open('w')
        logs.append(log)
        process = subprocess.Popen(command, env=env, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
        processes.append(process)
        return process

    try:
        sim = start(['ros2', 'launch', str(here/'cmu_sim.launch.py')], 'simulator')
        time.sleep(10)
        if sim.poll() is not None:
            raise RuntimeError('CMU simulator exited; see simulator.log')
        probe = start([sys.executable, str(here/'sim_probe.py'), '--phases', args.phases,
                       '--probabilities', args.probabilities,
                       '--output', str(out/'metrics.json')], 'probe')
        planner = start(['ros2', 'launch', 'tare_planner', 'explore_ht.launch.py',
                         'scenario:=garage', 'use_sim_time:=false',
                         f'ht_config:={out / "parameters.yaml"}'], 'planner')
        duration = sum(float(p.split(':')[1]) for p in args.phases.split(','))
        code = probe.wait(timeout=duration+30)
        if code or planner.poll() is not None:
            raise RuntimeError('Probe/planner failed; see logs')
        data = json.loads((out/'metrics.json').read_text())
        if not data['samples'] or data['samples'][-1]['scans'] < 10:
            raise RuntimeError('No usable CMU lidar stream; see simulator.log')
        print(json.dumps(data['samples'][-1], indent=2))
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                # ros2 launch forwards SIGINT to its children itself.
                process.send_signal(signal.SIGINT)
        for process in reversed(processes):
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
        # gz can outlive the launch shell. Reap the groups we created even
        # when their original process has already exited.
        for sig in (signal.SIGTERM, signal.SIGKILL):
            for process in reversed(processes):
                try:
                    os.killpg(process.pid, sig)
                except ProcessLookupError:
                    pass
            if sig == signal.SIGTERM:
                time.sleep(0.5)
        for log in logs:
            log.close()


if __name__ == '__main__':
    main()
