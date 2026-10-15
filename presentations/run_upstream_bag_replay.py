#!/usr/bin/env python3
"""Record ten minutes of original TARE, then replay through CuPy and HT."""
import argparse,datetime,json,os,shutil,subprocess,sys,time
from pathlib import Path
from run_scheduled_comparison import Trial,run_trial,source,q,BRIDGE,CMU,CUPY,UP,RESULTS

def record(folder,duration):
    trial=Trial('original',folder/'original',221)
    try:
        trial.start('bag_record',source('/opt/ros/jazzy/setup.bash',CMU/'install/setup.bash',UP/'install/setup.bash')+
                    f' exec ros2 bag record --all-topics --include-hidden-topics -s mcap --storage-preset-profile zstd_fast --max-cache-size 268435456 -b 2147483648 --disable-keyboard-controls -o {q(folder/"original_bag")}')
        summary=run_trial(trial,'original',duration)
    finally:trial.stop()
    (folder/'record_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print('RECORD COMPLETE',folder,flush=True)

def replay(folder,rate,playback_duration=None):
    import yaml
    config=folder/'configuration/mapper';config.mkdir(parents=True,exist_ok=True)
    if not (config/'offline_core.yaml').exists():
        core=yaml.safe_load((CUPY/'config/trial_core.yaml').read_text());core['base_frame']='sensor'
        setup=yaml.safe_load((CUPY/'config/trial_setup.yaml').read_text());setup['subscribers']['cmu_scan']['registered_cloud_sensor_frame']='sensor'
        (config/'offline_core.yaml').write_text(yaml.safe_dump(core));(config/'offline_setup.yaml').write_text(yaml.safe_dump(setup))
    trial=Trial('replay',folder/'replay_logs',int(os.environ.get('UPSTREAM_REPLAY_DOMAIN','222')))
    trial.env['HT_HISTORY_DUMP']=str(folder/'global_historical_elevation.npz')
    trial.env['HT_DIAGNOSTICS_DUMP']=str(folder/'ht_diagnostics.json')
    trial.env['CUPY_STATS_DUMP']=str(folder/'cupy_processing_stats.json')
    trial.env['CUPY_OFFLINE_TF_BAG']=str(folder/'original_bag')
    ready_file=folder/'cupy_ready.txt'
    if ready_file.exists():ready_file.unlink()
    trial.env['CUPY_READY_FILE']=str(ready_file)
    ros='/opt/ros/jazzy/setup.bash'
    code_snapshot=folder/'configuration/bridge';code_snapshot.mkdir(parents=True,exist_ok=True)
    for filename in ['cupy_to_ht.py','historical_elevation.py','elevation_quality.py',
                     'local_surface.py','model.py','student_best_epoch_weights.pth']:
        shutil.copy2(BRIDGE/filename,code_snapshot/filename)
    try:
        config=folder/'configuration/mapper'
        core=config/'offline_core.yaml';setup=config/'offline_setup.yaml'
        if not core.exists():core=CUPY/'config/trial_core.yaml'
        if not setup.exists():setup=CUPY/'config/trial_setup.yaml'
        trial.start('elevation',source(ros,CUPY/'install/setup.bash')+
                    f' exec ros2 run elevation_mapping_cupy elevation_mapping_node --ros-args -p use_sim_time:=true -p core_param_file:={q(core)} -p setup_file:={q(setup)}')
        trial.start('ht_bridge',source(ros,CMU/'install/setup.bash')+f' exec python3 {q(BRIDGE/"cupy_to_ht.py")} --ros-args -p use_sim_time:=true')
        trial.start('capture',source(ros,CMU/'install/setup.bash')+f' exec python3 {q(BRIDGE/"capture_replay_maps.py")} --output {q(folder/"snapshots")} --ros-args -p use_sim_time:=true')
        trial.start('map_record',source(ros,CMU/'install/setup.bash')+
                    f' exec ros2 bag record -s mcap --storage-preset-profile zstd_fast --disable-keyboard-controls -o {q(folder/"processed_bag")} --topics /clock /elevation_mapping/elevation_map_raw /elevation_mapping/historical_local /ht_traversability/global_local')
        deadline=time.monotonic()+180
        while not ready_file.exists() and time.monotonic()<deadline:
            trial.check();time.sleep(.5)
        if not ready_file.exists():raise RuntimeError('CuPy offline TF preload timed out')
        time.sleep(3);trial.check()
        limit=f' --playback-duration {playback_duration}' if playback_duration else ''
        player=trial.start('bag_play',source(ros,CMU/'install/setup.bash')+
                          f' exec ros2 bag play {q(folder/"original_bag")} --clock 50 --rate {rate} --delay 3 --read-ahead-queue-size 2000 --disable-keyboard-controls{limit} --topics /registered_scan /velodyne_points /state_estimation /tf /tf_static /camera/image_raw /camera/camera_info')
        player.wait(timeout=1800/rate)
        if player.returncode:raise RuntimeError('bag replay failed')
        time.sleep(3)
    finally:trial.stop()
    print('REPLAY COMPLETE',folder,flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--duration',type=int,default=600);ap.add_argument('--rate',type=float,default=1.0);ap.add_argument('--run-dir',type=Path);ap.add_argument('--replay-only',action='store_true');ap.add_argument('--replay-duration',type=float);args=ap.parse_args()
    folder=(args.run_dir or RESULTS/('original_10min_replay_'+datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))).resolve();folder.mkdir(parents=True,exist_ok=True)
    if not args.replay_only:
        (folder/'manifest.json').write_text(json.dumps({'scenario':'Garage','original_tare_workspace':str(UP),'duration_s':args.duration,'speed_cap_mps':.5,'record':'all published topics, MCAP zstd','pipeline':'original TARE drives; CuPy and HT only run afterward on recorded inputs','replay_rate':args.rate},indent=2)+'\n')
        record(folder,args.duration)
    replay(folder,args.rate,args.replay_duration)
    command=source('/opt/ros/jazzy/setup.bash')+f' exec python3 {q(Path(__file__).with_name("render_upstream_replay.py"))} {q(folder)}'
    with (folder/'render.log').open('w') as log:
        completed=subprocess.run(['bash','-lc',command],stdout=log,stderr=subprocess.STDOUT,timeout=600)
    if completed.returncode:raise RuntimeError(f'Visualization failed; see {folder/"render.log"}')
    print('COMPLETE',folder,flush=True)
if __name__=='__main__':main()
