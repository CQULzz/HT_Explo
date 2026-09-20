#!/usr/bin/env python3
"""Fixed-protocol sequential CMU garage exploration comparison."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import numpy as np
from ament_index_python.packages import get_package_share_directory
from coverage_metrics import read_reference_ply, voxel_keys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent


def shutdown(processes):
    for process in reversed(processes):
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
    for process in reversed(processes):
        try:
            process.wait(timeout=12)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
            process.wait()
    for sig in (signal.SIGTERM,signal.SIGKILL):
        for process in reversed(processes):
            try:
                os.killpg(process.pid,sig)
            except ProcessLookupError:
                pass
        if sig==signal.SIGTERM:
            time.sleep(0.5)


def run_case(condition, repetition, duration, output, reference, map_file, domain):
    out=output/f'{condition}_{repetition}'
    out.mkdir(parents=True,exist_ok=False)
    config={'/**':{'ros__parameters':{
        'ht_enabled':condition=='ht', 'ht_directions_calibrated':True,
        'ht_weight':1.0, 'kAutoStart':False}}}
    (out/'planner_parameters.yaml').write_text(json.dumps(config,indent=2))
    scoring={'/**':{'ros__parameters':{
        'metricFile':str(out/'cmu_metrics'), 'trajFile':str(out/'cmu_trajectory'),
        'mapFile':str(map_file), 'overallMapVoxelSize':0.5,
        'exploredAreaVoxelSize':0.3, 'exploredVolumeVoxelSize':0.5,
        'transInterval':0.2, 'yawInterval':10.0,
        'overallMapDisplayInterval':10000, 'exploredAreaDisplayInterval':5}}}
    (out/'scorer_parameters.yaml').write_text(json.dumps(scoring,indent=2))
    env=dict(os.environ,ROS_DOMAIN_ID=str(domain),
             GZ_PARTITION=f'ht_experiment_{os.getpid()}_{condition}_{repetition}')
    processes=[]
    logs=[]

    def start(command,name):
        log=(out/f'{name}.log').open('w')
        logs.append(log)
        p=subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT,
                           start_new_session=True)
        processes.append(p)
        return p

    print(json.dumps(dict(event='start',condition=condition,repetition=repetition,
                          duration_s=duration,time=time.strftime('%Y-%m-%dT%H:%M:%S%z'))),flush=True)
    try:
        sim=start(['ros2','launch',str(ROOT/'validation/cmu_sim.launch.py')],'simulator')
        time.sleep(10)
        if sim.poll() is not None:
            raise RuntimeError('Simulator launch exited')
        scorer=start(['ros2','run','visualization_tools','visualizationTools',
                      '--ros-args','--params-file',str(out/'scorer_parameters.yaml')],'cmu_scorer')
        probe=start([sys.executable,str(HERE/'exploration_probe.py'),
                     '--output',str(out),'--reference',str(reference),
                     '--duration',str(duration),'--warmup','5'],'probe')
        planner=start(['ros2','launch','tare_planner','explore_ht.launch.py',
                       'scenario:=garage','use_sim_time:=false',
                       f'ht_config:={out/"planner_parameters.yaml"}'],'planner')
        deadline=time.monotonic()+duration+40
        while probe.poll() is None:
            if time.monotonic()>deadline:
                raise RuntimeError('Probe timed out')
            if planner.poll() is not None or scorer.poll() is not None or sim.poll() is not None:
                raise RuntimeError('A required experiment process exited')
            time.sleep(1)
        if probe.returncode:
            raise RuntimeError('Probe failed')
        data=json.loads((out/'metrics.json').read_text())
        last=data['samples'][-1]
        if not data['final'] or last['t']<duration-0.5 or last['scans']<duration*4:
            raise RuntimeError('Incomplete duration or insufficient lidar throughput')
        if not data['planning_cycles'] or last['cmu_hit_voxel_volume_m3']<=0:
            raise RuntimeError('Planner/scorer did not publish measurements')
        print(json.dumps(dict(event='complete',condition=condition,repetition=repetition,
                              last=last)),flush=True)
    finally:
        shutdown(processes)
        for log in logs:
            log.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    parser.add_argument('--duration',type=float,default=300)
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--pilot',action='store_true')
    mode.add_argument('--ht-only',action='store_true',help='Three HT trials for a separately recorded fix follow-up')
    parser.add_argument('--domain',type=int,default=75)
    args=parser.parse_args()
    output=Path(args.output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    map_file=Path(get_package_share_directory('vehicle_simulator'))/'mesh/garage/preview/pointcloud.ply'
    reference=output/'reference_voxels.npz'
    keys=voxel_keys(read_reference_ply(map_file))
    np.savez_compressed(reference,keys=keys)
    order=[('baseline',1),('ht',1)] if args.pilot else [
        ('baseline',1),('ht',1),('ht',2),('baseline',2),('baseline',3),('ht',3)]
    if args.ht_only:
        order=[('ht',1),('ht',2),('ht',3)]
    planner_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    source_diff=subprocess.check_output(['git','diff','HEAD','--','src'],cwd=ROOT,text=True)
    if source_diff:
        raise RuntimeError('Commit planner source changes before starting a recorded experiment')
    protocol=dict(planner_source_commit=planner_commit,
                  cmu_commit='8313dfed10533787582be8a6044483fe3299622f',
                  created=time.strftime('%Y-%m-%dT%H:%M:%S%z'),duration_s=args.duration,
                  order=order,cohort='ht_fix_followup' if args.ht_only else 'interleaved_comparison',
                  scenario='garage',speed_limit_m_s=0.5,
                  initial_sensor_position_m=[0,0,0.75],voxel_resolution_m=0.5,
                  reference_voxels=int(len(keys)),reference_ply_sha256=hashlib.sha256(map_file.read_bytes()).hexdigest(),
                  ht_map=dict(type='synthetic_uniform',probability=0.9,channels=8,
                              length_m=80,resolution_m=0.5,rate_hz=5),
                  random_seed='uncontrolled: upstream uses std::random_device',
                  clock='wall time; both navigation inputs and HT use use_sim_time=false',
                  script_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [Path(__file__),HERE/'exploration_probe.py',HERE/'coverage_metrics.py',
                                           ROOT/'validation/sim_probe.py',ROOT/'validation/cmu_sim.launch.py']})
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    for condition,repetition in order:
        run_case(condition,repetition,args.duration,output,reference,map_file,args.domain)


if __name__=='__main__':
    main()
