#!/usr/bin/env python3
"""Record a fresh upstream TARE/current HT pair, with identical offline metrics."""
import argparse
import datetime as dt
import hashlib
import json
import signal
import subprocess
from pathlib import Path

from run_scheduled_comparison import (
    Trial, run_trial, validate, source, q, ROOT, CMU, UP, BRIDGE, preflight)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--duration',type=int,default=180)
    ap.add_argument('--output',type=Path)
    args=ap.parse_args()
    folder=(args.output or ROOT/'presentations/scheduled_results'/
            ('tare_ht_pair_'+dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))).resolve()
    if folder.exists():raise RuntimeError(f'Refusing to overwrite {folder}')
    folder.mkdir(parents=True)
    manifest={'started_at':dt.datetime.now().astimezone().isoformat(),
              'duration_per_trial_s':args.duration,'scenario':'Garage','speed_cap_mps':.5,
              'order':['original','current'],'preflight':preflight(),
              'current_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              'upstream_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=UP,text=True).strip(),
              'runner_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'comparison':'End-to-end systems: original TARE + CMU local planner versus CuPy/HT + XYtheta + independent follower.'}
    (folder/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (folder/'working_tree.patch').write_bytes(subprocess.check_output(['git','diff','HEAD'],cwd=ROOT))
    topics=['/registered_scan','/state_estimation','/state_estimation_at_scan','/tf','/tf_static',
            '/camera/image_raw','/cmd_vel','/way_point','/path','/local_path','/global_path',
            '/runtime','/exploration_finish','/ht_xytheta_path','/ht_execution_status',
            '/ht_follower_status','/ht_execution_rejected_edge','/ht_navigation_allowed',
            '/elevation_mapping/elevation_map_raw','/elevation_mapping/historical_local',
            '/ht_traversability/global_local']
    pair={}
    try:
        for name,domain in [('original',227),('current',228)]:
            trial=Trial(name,folder/name,domain)
            try:
                ros=source('/opt/ros/jazzy/setup.bash',CMU/'install/setup.bash')
                trial.start('record',ros+' exec ros2 bag record -s mcap --storage-preset-profile zstd_fast '
                            '--max-cache-size 268435456 --disable-keyboard-controls -o '+
                            q(folder/(name+'_bag'))+' --topics '+' '.join(q(t) for t in topics))
                if name=='current':
                    trial.start('snapshots',ros+' exec python3 '+q(BRIDGE/'capture_replay_maps.py')+
                                ' --output '+q(folder/'current_snapshots'))
                pair[name]=run_trial(trial,name,args.duration)
            finally:trial.stop()
        validate(pair,args.duration)
        (folder/'pair_summary.json').write_text(json.dumps(pair,indent=2)+'\n')
        command=source('/opt/ros/jazzy/setup.bash')+' exec python3 '+q(Path(__file__).with_name('summarize_tare_ht_pair.py'))+' '+q(folder)
        with (folder/'postprocess.log').open('w') as log:
            subprocess.run(['bash','-lc',command],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=900)
        print('COMPLETE',folder,flush=True)
    except Exception as exc:
        (folder/'FAILURE.json').write_text(json.dumps({'error':str(exc)},indent=2)+'\n')
        raise


if __name__=='__main__':main()
