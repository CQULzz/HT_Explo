#!/usr/bin/env python3
"""One unchanged HT control stack, one uninterrupted wall-time endurance trial."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import threading
import time

import psutil

from run_scheduled_comparison import Trial, run_trial, source, q, CMU, CUPY, BRIDGE, ROOT, preflight


def monitor(trial, folder, stopped, failures):
    previous = {}
    last_gpu = {}
    fields = ['wall_time', 'pid', 'label', 'name', 'rss_mb', 'cpu_percent',
              'read_mb', 'write_mb', 'system_available_mb', 'disk_free_gb',
              'gpu_used_mb', 'gpu_util_percent', 'gpu_temp_c']
    with (folder/'resources.csv').open('w', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        while not stopped.is_set():
            now = time.monotonic()
            free_gb = shutil.disk_usage(folder).free / 1024**3
            available = psutil.virtual_memory().available / 1024**2
            try:
                gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.used,utilization.gpu,temperature.gpu',
                                               '--format=csv,noheader,nounits'], text=True, timeout=3)
                vals = gpu.strip().split(',')
                last_gpu = dict(zip(['gpu_used_mb', 'gpu_util_percent', 'gpu_temp_c'], map(float, vals)))
            except Exception:
                last_gpu = {}
            for label, proc, _ in list(trial.processes):
                if proc.poll() is not None:
                    if label == 'probe' and proc.returncode == 0:
                        continue
                    item = {'label': label, 'returncode': proc.returncode,
                            'wall_time': time.time(), 'event': 'unexpected_process_exit'}
                    if not any(x.get('label') == label for x in failures):
                        failures.append(item)
                        (folder/'runtime_failures.json').write_text(json.dumps(failures, indent=2))
                    # The measurement probe exits normally at its planned end.
                    if label != 'probe':
                        stopped.set()
                try:
                    parent = psutil.Process(proc.pid)
                    tree = [parent] + parent.children(recursive=True)
                except psutil.Error:
                    continue
                for child in tree:
                    try:
                        cpu = sum(child.cpu_times()[:2])
                        before = previous.get(child.pid)
                        percent = 100*(cpu-before[1])/(now-before[0]) if before else ''
                        previous[child.pid] = (now, cpu)
                        io = child.io_counters()
                        writer.writerow(dict(wall_time=time.time(), pid=child.pid, label=label,
                                             name=child.name(), rss_mb=child.memory_info().rss/1024**2,
                                             cpu_percent=percent, read_mb=io.read_bytes/1024**2,
                                             write_mb=io.write_bytes/1024**2, system_available_mb=available,
                                             disk_free_gb=free_gb, **last_gpu))
                    except psutil.Error:
                        pass
            out.flush()
            if free_gb < 6 or available < 800:
                failures.append({'event': 'resource_guard', 'disk_free_gb': free_gb,
                                 'available_mb': available, 'wall_time': time.time()})
                (folder/'runtime_failures.json').write_text(json.dumps(failures, indent=2))
                stopped.set()
            stopped.wait(5)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--duration', type=int, default=3600)
    parser.add_argument('--domain', type=int, default=231)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--scenario',choices=['garage','campus','indoor','forest','tunnel'],default='garage')
    parser.add_argument('--video-fps',type=int,choices=[2,10,15],default=2)
    args = parser.parse_args()
    folder = (args.output or ROOT/'presentations/scheduled_results'/
              ('ht_endurance_'+dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))).resolve()
    if folder.exists():
        raise RuntimeError(f'Refusing to overwrite {folder}')
    folder.mkdir(parents=True)
    trial = Trial('endurance', folder/'current', args.domain)
    trial.env.update(HT_DIAGNOSTICS_DUMP=str(folder/'current/ht_diagnostics.json'),
                     CUPY_STATS_DUMP=str(folder/'current/cupy_processing_stats.json'))
    paths = [BRIDGE/'ht_trial.yaml', BRIDGE/'cupy_to_ht.py', BRIDGE/'historical_elevation.py',
             CUPY/'config/trial_core.yaml', CUPY/'config/trial_setup.yaml',
             CUPY/'install/elevation_mapping_cupy/lib/elevation_mapping_cupy/elevation_mapping_node',
             ROOT/'install_standalone/tare_planner/lib/tare_planner/xytheta_follower',
             ROOT/'install_standalone/tare_planner/lib/tare_planner/tare_planner_node',
             ROOT/'src/tare_planner/config/ht.yaml',
             ROOT/'src/tare_planner/src/ht_cost/ht_cost_map.cpp',
             ROOT/'src/tare_planner/include/ht_cost/ht_cost_map.h',
             ROOT/'src/tare_planner/include/local_coverage_planner/local_coverage_planner.h',
             ROOT/'src/tare_planner/include/ht_cost/heading_reserve.h',
             ROOT/'src/tare_planner/include/ht_cost/xytheta_planner.h',
             ROOT/'src/tare_planner/include/ht_cost/ht_cost_core.h',
             ROOT/'src/tare_planner/src/grid_world/grid_world.cpp',
             ROOT/'src/tare_planner/include/grid_world/grid_world.h',
             ROOT/'src/tare_planner/include/ht_cost/exploration_progress.h',
             ROOT/'src/tare_planner/include/ht_cost/execution_policy.h',
             ROOT/'src/tare_planner/src/local_coverage_planner/ht_route.cpp',
             ROOT/'src/tare_planner/src/local_coverage_planner/local_coverage_planner.cpp',
             ROOT/'src/tare_planner/src/sensor_coverage_planner/sensor_coverage_planner_ground.cpp']
    paths += [Path(__file__), Path(__file__).with_name('run_scheduled_comparison.py'),
              Path(__file__).with_name('summarize_ht_endurance.py'),
              Path(__file__).with_name('summarize_tare_ht_pair.py'),
              ROOT/'src/tare_planner/include/ht_cost/target_commitment.h',
              ROOT/'src/tare_planner/src/ht_cost/xytheta_follower.cpp',
              CUPY/'src/elevation_mapping_cupy_2204/elevation_mapping_cupy/script/elevation_mapping_cupy/elevation_mapping_ros.py']
    paths += [BRIDGE/name for name in ('cmu_xytheta.launch.py','cmu_vehicle_downward.launch.py','gz_sim_direct.launch.py')]
    paths += [BRIDGE/name for name in ('cpu_threads.py','model.py','local_surface.py','elevation_quality.py','ht_support.py','capture_replay_maps.py','profile_cupy_runtime.py',
                                     'assets/camera_sensor_mask.sdf','assets/lidar_downward.sdf',
                                     'assets/robot_sensor_mask.sdf','student_best_epoch_weights.pth')]
    paths += [CMU/f'src/vehicle_simulator/world/{args.scenario}.world',
              ROOT/f'src/tare_planner/config/{args.scenario}.yaml',
              ROOT/f'install_standalone/tare_planner/share/tare_planner/{args.scenario}.yaml',
              Path(__file__).with_name('stage_garage_pose.py'),Path(__file__).with_name('endurance_probe.py')]
    paths += [CMU/'src/vehicle_simulator/launch/vehicle_simulator.launch', CUPY/'config/trial_plugins.yaml']
    paths += [CUPY/'src/elevation_mapping_cupy_2204/elevation_mapping_cupy/script/elevation_mapping_cupy'/name
              for name in ('elevation_mapping.py','traversability_filter.py')]
    for package, executable in [('vehicle_simulator','vehicleSimulator'),
                                ('terrain_analysis','terrainAnalysis'),
                                ('terrain_analysis_ext','terrainAnalysisExt'),
                                ('sensor_scan_generation','sensorScanGeneration')]:
        paths += [CMU/f'src/{package}/src/{executable}.cpp',
                  CMU/f'install/{package}/lib/{package}/{executable}']
    manifest = dict(started_at=dt.datetime.now().astimezone().isoformat(),
                    planned_duration_s=args.duration, scenario=args.scenario, domain=args.domain,
                    video_fps=args.video_fps, cupy_timing_profile=os.environ.get('HT_PROFILE_CUPY')=='1',
                    speed_cap_mps=.5, preflight=preflight(),
                    ht_score_semantics=json.loads((BRIDGE/'ht_trial.yaml').read_text())['/**']['ros__parameters'].get('ht_score_semantics','point'),
                    git_head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                    evidence_policy=f'All control/status and odometry, full-rate published HT maps; original-stamped scans1Hz; exact-stamp map triplets every10s; camera{args.video_fps}fps. Raw CuPy and scans are not fully bagged.',
                    source_hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths})
    (folder/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (folder/'working_tree.patch').write_bytes(subprocess.check_output(['git', 'diff', 'HEAD'], cwd=ROOT))
    for p in [Path(__file__), Path(__file__).with_name('endurance_probe.py')]:
        shutil.copy2(p, folder/p.name)
    topics = ['/endurance/registered_scan', '/state_estimation', '/state_estimation_at_scan',
              '/tf', '/tf_static', '/cmd_vel', '/way_point', '/ht_xytheta_path',
              '/ht_execution_status', '/ht_follower_status', '/ht_execution_rejected_edge',
              '/ht_navigation_allowed', '/mission_state', '/mission_completed', '/runtime', '/runtime_breakdown', '/exploration_finish',
              '/ht_traversability/global_local']
    stopped = threading.Event()
    failures = []
    thread = threading.Thread(target=monitor, args=(trial, folder, stopped, failures), daemon=True)
    thread.start()
    # The guard terminates only this trial's owned process groups, never other workspaces.
    def guard():
        stopped.wait()
        if failures:
            for label, proc, _ in list(trial.processes):
                if label == 'probe' and proc.poll() is None:
                    proc.terminate()
    watcher = threading.Thread(target=guard, daemon=True)
    watcher.start()
    try:
        ros = source('/opt/ros/jazzy/setup.bash', CMU/'install/setup.bash')
        trial.start('record', ros+' exec ros2 bag record -s mcap --storage-preset-profile zstd_fast '
                    '--max-cache-size 134217728 --max-bag-duration 300 --disable-keyboard-controls -o '+
                    q(folder/'evidence_bag')+' --topics '+' '.join(q(t) for t in topics))
        trial.start('health', ros+' exec python3 '+q(Path(__file__).with_name('endurance_probe.py'))+
                    ' --output '+q(folder)+f' --video-fps {args.video_fps} --scenario {args.scenario}')
        summary = run_trial(trial, 'current', args.duration,args.scenario)
        (folder/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2))
        (folder/'COMPLETED.json').write_text(json.dumps({
            'finished_at': dt.datetime.now().astimezone().isoformat(),
            'measurement_duration_s': args.duration, 'node_restarts': 0,
            'note': 'Timer completion is not exploration success; see motion and health analysis.'}, indent=2))
    except BaseException as exc:
        (folder/'FAILURE.json').write_text(json.dumps({'error': str(exc),
                                                     'wall_time': time.time()}, ensure_ascii=False, indent=2))
        raise
    finally:
        stopped.set()
        thread.join(timeout=8)
        trial.stop()
        print('RESULTS', folder, flush=True)


if __name__ == '__main__':
    main()
