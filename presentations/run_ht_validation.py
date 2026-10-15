#!/usr/bin/env python3
"""Start a fresh HT-driven Garage trial, save all evidence and render a video."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys

from run_scheduled_comparison import Trial, run_trial, source, q, CMU, CUPY, BRIDGE, ROOT


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--duration',type=int,default=180)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--domain',type=int,default=229)
    parser.add_argument('--skip-video',action='store_true')
    args=parser.parse_args()
    folder=(args.output or ROOT/'presentations/scheduled_results'/('ht_validation_'+dt.datetime.now().astimezone().strftime('%Y-%m-%d_%H-%M-%S'))).resolve()
    if (folder/'current').exists():raise RuntimeError(f'Refusing to overwrite {folder}')
    folder.mkdir(parents=True,exist_ok=True)
    trial=Trial('ht_validation',folder/'current',args.domain)
    trial.env['HT_DIAGNOSTICS_DUMP']=str(folder/'current/ht_diagnostics.json')
    trial.env['CUPY_STATS_DUMP']=str(folder/'current/cupy_processing_stats.json')
    ros='/opt/ros/jazzy/setup.bash'
    executable=CUPY/'install/elevation_mapping_cupy/lib/elevation_mapping_cupy/elevation_mapping_node'
    code=executable.read_text()
    for required in ['self.map_data.T','last_integrated_stamp','scan_callback_group']:
        if required not in code:raise RuntimeError('Mapper fixes are not installed: '+required)
    manifest={'driver':'CURRENT HT XYtheta controls vehicle','world':'Garage','duration_s':args.duration,
              'started_at':dt.datetime.now().astimezone().isoformat(),'domain':args.domain,
              'mapper_sha256':hashlib.sha256(executable.read_bytes()).hexdigest(),
              'bridge_source':str(BRIDGE),'speed_cap_mps':.5,
              'note':'HT channel-to-physical-angle mapping still requires vehicle calibration.'}
    manifest['git_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    follower=ROOT/'install_standalone/tare_planner/lib/tare_planner/xytheta_follower'
    manifest['follower_binary_sha256']=hashlib.sha256(follower.read_bytes()).hexdigest()
    (folder/'working_tree.patch').write_bytes(subprocess.check_output(['git','diff','HEAD'],cwd=ROOT))
    for pattern in ['src/tare_planner/include/ht_cost/*.h',
                    'src/tare_planner/src/ht_cost/*.cpp',
                    'src/tare_planner/src/local_coverage_planner/*.cpp',
                    'src/tare_planner/include/local_coverage_planner/*.h',
                    'presentations/run_ht_validation.py','presentations/run_scheduled_comparison.py']:
        for path in ROOT.glob(pattern):
            target=folder/'source_snapshot'/path.relative_to(ROOT)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
    (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    topics=['/registered_scan','/state_estimation','/tf','/tf_static','/camera/image_raw',
            '/cmd_vel','/way_point','/local_path','/ht_xytheta_path','/ht_execution_status',
            '/ht_navigation_allowed','/ht_follower_status','/ht_execution_rejected_edge','/mission_state','/runtime','/exploration_finish',
            '/elevation_mapping/elevation_map_raw','/elevation_mapping/historical_local',
            '/ht_traversability/global_local']
    try:
        trial.start('record',source(ros,CMU/'install/setup.bash')+
                    f' exec ros2 bag record -s mcap --storage-preset-profile zstd_fast --max-cache-size 268435456 --disable-keyboard-controls -o {q(folder/"original_bag")} --topics '+' '.join(q(t) for t in topics))
        capture=trial.start('snapshots',source(ros)+f' exec python3 {q(BRIDGE/"capture_replay_maps.py")} --output {q(folder/"snapshots")}')
        summary=run_trial(trial,'current',args.duration)
        if capture.poll() is None:
            os.killpg(capture.pid,signal.SIGINT)
            capture.wait(timeout=10)
        (folder/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
        (folder/'record_summary.json').write_text(json.dumps({'duration_s':args.duration,'driver':'CURRENT HT XYtheta'},indent=2)+'\n')
        (folder/'original').symlink_to(folder/'current')  # Shared renderer input schema.
    except Exception as exc:
        (folder/'FAILURE.json').write_text(json.dumps({'error':str(exc)},ensure_ascii=False,indent=2)+'\n')
        raise
    finally:trial.stop()
    if not args.skip_video:
        command=source(ros)+f' exec python3 {q(Path(__file__).with_name("render_upstream_replay.py"))} {q(folder)} --driver current'
        with (folder/'render.log').open('w') as log:
            subprocess.run(['bash','-lc',command],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
    audit=source(ros)+f' exec python3 {q(Path(__file__).with_name("summarize_ht_validation.py"))} {q(folder)}'
    with (folder/'audit.log').open('w') as log:
        subprocess.run(['bash','-lc',audit],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=180)
    print(folder,flush=True)


if __name__=='__main__':main()
