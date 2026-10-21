#!/usr/bin/env python3
"""Original TARE exploration with an explicit matched CMU motion envelope."""
import argparse
import datetime as dt
import hashlib
import json
import math
import subprocess
import threading
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from run_scheduled_comparison import Trial, run_trial, ROOT, CMU, UP, source, q, preflight
from run_ht_endurance import monitor


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def capture_parameters(trial, stopped):
    origin = trial.folder/'measurement_started.json'
    while not stopped.wait(.5):
        if not origin.exists():
            continue
        records = []
        for node in ['tare_planner_node', 'pathFollower', 'localPlanner', 'comparison_motion_limiter']:
            command = source('/opt/ros/jazzy/setup.bash', CMU/'install/setup.bash') + \
                f' exec ros2 param dump /{node} --no-daemon --spin-time 4'
            result = subprocess.run(['bash', '-lc', command], env=trial.env,
                                    capture_output=True, text=True, timeout=35)
            (trial.folder.parent/(node+'_parameters.yaml')).write_text(result.stdout)
            records.append(dict(node=node, returncode=result.returncode, stderr=result.stderr))
        dump(trial.folder.parent/'parameter_capture_attempts.json', records)
        return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--domain', type=int, required=True)
    ap.add_argument('--duration', type=int, default=600)
    ap.add_argument('--scenario', choices=['indoor', 'garage', 'campus'], default='indoor')
    a = ap.parse_args()
    folder = a.output.resolve()
    if folder.exists():
        raise RuntimeError('Refusing to overwrite '+str(folder))
    folder.mkdir(parents=True)
    preflight()
    original_xml = CMU/'src/local_planner/launch/local_planner.launch'
    tree = ET.parse(original_xml)
    follower = next(n for n in tree.getroot().findall('node') if n.get('exec') == 'pathFollower')
    for parameter in follower.findall('param'):
        if parameter.get('name') == 'maxYawRate':
            parameter.set('value', str(math.degrees(.8)))
        elif parameter.get('name') == 'maxAccel':
            parameter.set('value', '.5')
    ET.SubElement(follower, 'remap', {'from': '/cmd_vel', 'to': '/comparison/tare_raw_cmd_vel'})
    matched_xml = folder/'local_planner_matched.launch.xml'
    tree.write(matched_xml, encoding='unicode')
    (folder/'local_planner_original.launch.xml').write_bytes(original_xml.read_bytes())

    class MatchedTrial(Trial):
        def start(self, label, command):
            if label == 'local_planner':
                ros = source('/opt/ros/jazzy/setup.bash', CMU/'install/setup.bash')
                super().start('motion_limits', ros+' exec python3 '+q(Path(__file__).with_name('comparison_motion_limits.py')))
                command = ros+' exec ros2 launch '+q(matched_xml)+' autonomySpeed:=0.5'
            return super().start(label, command)

    trial = MatchedTrial('original_matched', folder/'current', a.domain)
    paths = [Path(__file__), Path(__file__).with_name('comparison_motion_limits.py'),
             Path(__file__).with_name('run_scheduled_comparison.py'),
             Path(__file__).with_name('endurance_probe.py'), Path(__file__).with_name('paired_probe.py'),
             original_xml, matched_xml, CMU/f'src/vehicle_simulator/world/{a.scenario}.world',
             UP/'install/tare_planner/lib/tare_planner/tare_planner_node']
    paths += [p for p in (UP/'src/tare_planner').rglob('*')
              if p.is_file() and p.suffix in ('.cpp', '.h', '.hpp', '.yaml', '.launch')
              and 'or-tools' not in p.parts and '.git' not in p.parts]
    paths += list((UP/'install/tare_planner/share/tare_planner').glob('*.yaml'))
    for package, executable in [('local_planner', 'localPlanner'), ('local_planner', 'pathFollower'),
                                ('vehicle_simulator', 'vehicleSimulator'), ('terrain_analysis', 'terrainAnalysis')]:
        paths += [CMU/f'install/{package}/lib/{package}/{executable}',
                  CMU/f'src/{package}/src/{executable}.cpp']
    hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    manifest = dict(git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    upstream_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=UP, text=True).strip(),
                    planned_duration_s=a.duration, scenario=a.scenario, domain=a.domain, video_fps=15,
                    source_hashes=hashes, started_at=dt.datetime.now().astimezone().isoformat(),
                    baseline='Original ROS2-adapted TARE; matched motion envelope; not stock CMU control parameters',
                    evidence_policy='All control/odom/status/routes; source-second lidar; camera15fps. Not lossless full-rate sensors.',
                    limits=dict(forward=.5, reverse=.25, yaw=.8, accel=.5, yaw_accel=1.2,
                                zero_or_stale_stop='Immediate; exempt from normal acceleration ramp'))
    dump(folder/'manifest.json', manifest)
    (folder/'upstream_tracked.patch').write_bytes(subprocess.check_output(['git', 'diff', 'HEAD'], cwd=UP))
    stopped, failures = threading.Event(), []
    worker = threading.Thread(target=monitor, args=(trial, folder, stopped, failures), daemon=True)
    observer = threading.Thread(target=capture_parameters, args=(trial, stopped), daemon=True)
    worker.start(); observer.start()
    try:
        ros = source('/opt/ros/jazzy/setup.bash', CMU/'install/setup.bash')
        topics = ['/endurance/registered_scan', '/state_estimation', '/state_estimation_at_scan',
                  '/tf', '/tf_static', '/cmd_vel', '/comparison/tare_raw_cmd_vel',
                  '/comparison/motion_limit_status', '/way_point', '/path', '/local_path', '/global_path',
                  '/runtime', '/runtime_breakdown', '/exploration_finish', '/terrain_map', '/terrain_map_ext']
        trial.start('record', ros+' exec ros2 bag record -s mcap --storage-preset-profile zstd_fast '
                    '--max-cache-size 134217728 --max-bag-duration 300 --disable-keyboard-controls -o '+
                    q(folder/'evidence_bag')+' --topics '+' '.join(q(t) for t in topics))
        trial.start('health', ros+' exec python3 '+q(Path(__file__).with_name('endurance_probe.py'))+
                    ' --output '+q(folder)+f' --video-fps 15 --scenario {a.scenario}')
        summary = run_trial(trial, 'original', a.duration, a.scenario)
        dump(folder/'summary.json', summary)
        dump(folder/'COMPLETED.json', dict(measurement_duration_s=a.duration,
              finished_at=dt.datetime.now().astimezone().isoformat(),
              note='Timer completion, not exploration success'))
    except BaseException as error:
        dump(folder/'FAILURE.json', dict(error=repr(error), wall_time=time.time()))
        raise
    finally:
        stopped.set(); worker.join(timeout=8); observer.join(timeout=40)
        trial.stop()
        dump(folder/'source_integrity.json', {p: Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
                                              for p, h in hashes.items()})


if __name__ == '__main__':
    main()
