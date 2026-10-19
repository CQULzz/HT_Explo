#!/usr/bin/env python3
"""Check saved inference inputs, masks and exact corresponding published HT maps."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import numpy as np
from scipy.ndimage import distance_transform_edt, uniform_filter, maximum_filter
import rosbag2_py
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trial',type=Path);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--verify-model',action='store_true')
    parser.add_argument('--record-damaged-contexts',action='store_true',
                        help='Retain and list unreadable NPZs; overall audit stays failed')
    args=parser.parse_args()
    origin=json.loads((args.trial/'current/measurement_started.json').read_text())['wall_time']
    duration=json.loads((args.trial/'summary.json').read_text())['duration_s'];wanted={};events=[];damaged=[]
    for file in sorted((args.trial/'current/inference_context').glob('*.npz')):
        try:
            with np.load(file) as header:
                header.files
        except zipfile.BadZipFile as error:
            if not args.record_damaged_contexts:raise
            damaged.append(dict(file=str(file),bytes=file.stat().st_size,
                sha256=hashlib.sha256(file.read_bytes()).hexdigest(),error=str(error)))
            continue
        with np.load(file) as d:
            stamp=float(d['source_stamp'])
            if not 0<=stamp-origin<duration:continue
            key=tuple(map(int,file.stem.split('_')));res=float(d['geometry'][2])
            occupied_full=np.isfinite(d['obstacle_context']);known=d['observed']|occupied_full
            uncertain=d['rejected']&~occupied_full;near=distance_transform_edt(~known)*res<=.25
            support=(uniform_filter(near.astype(np.float32),size=51,mode='constant')[25:-25,25:-25]>=.9)&~maximum_filter(uncertain,size=51,mode='constant')[25:-25,25:-25]
            occupied=occupied_full[25:-25,25:-25];support|=occupied
            physical=(near&~uncertain)[25:-25,25:-25]
            finite_reject=d['quality_rejected']&np.isfinite(d['raw_history'])
            checks=dict(support_exact=bool(np.array_equal(support,d['support'])),
                        physical_exact=bool(np.array_equal(physical,d['physical_support'])),
                        occupied_exact=bool(np.array_equal(occupied,d['occupied'])),
                        all_finite_rejects_occupied=bool(np.all(occupied_full[finite_reject])),
                        occupied_eight_probabilities_zero=bool(np.all(d['probabilities'][:,occupied]==0)))
            event=dict(file=str(file),source_stamp=stamp,finite_quality_rejections=int(finite_reject.sum()),checks=checks)
            events.append(event);wanted[key]=(file,event)
    reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(args.trial/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local']));paired=set()
    while reader.has_next():
        _,raw,_=reader.read_next();msg=deserialize_message(raw,GridMap);key=(msg.header.stamp.sec,msg.header.stamp.nanosec)
        if key not in wanted:continue
        file,event=wanted[key]
        with np.load(file) as d:
            def layer(name):
                a=np.asarray(msg.data[msg.layers.index(name)].data,np.float32).reshape((241,241),order='F')
                return np.roll(a,(-msg.outer_start_index,-msg.inner_start_index),(0,1))
            same=all(np.array_equal(layer(name),d[field].astype(np.float32)) for name,field in [('ht_valid','support'),('ht_observation_valid','physical_support'),('ht_obstacle','occupied')])
            same &= all(np.array_equal(layer(f'ht_dir_{k}'),np.where(d['support'],d['probabilities'][k],np.nan),equal_nan=True) for k in range(8))
            event['checks']['published_layers_exact']=bool(same);paired.add(key)
    for key,(_,event) in wanted.items():event['checks']['recorded_same_stamp_map']=key in paired
    models=[]
    if args.verify_model and events:
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools/ht_cupy_bridge'))
        import torch
        from model import load_student_model
        from cpu_threads import configure_cpu_threads
        limit,_=configure_cpu_threads(4)
        weights=Path(__file__).resolve().parents[1]/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'
        expected=json.loads((args.trial/'manifest.json').read_text())['source_hashes'][str(weights)]
        actual=hashlib.sha256(weights.read_bytes()).hexdigest()
        if actual!=expected:raise ValueError('Current model does not match tested frozen weights')
        model=load_student_model(str(weights),torch.device('cpu')).to(memory_format=torch.channels_last)
        for i in sorted({0,len(events)//2,len(events)-1}):
            with np.load(events[i]['file']) as d,torch.inference_mode():
                tensor=torch.from_numpy(d['height'][None,None]).contiguous(memory_format=torch.channels_last)
                result=torch.softmax(model(tensor),dim=2)[0,:,1].numpy();result[:,d['occupied']]=0
                error=float(np.max(np.abs(result-d['probabilities'])))
                models.append(dict(file=events[i]['file'],maximum_absolute_error=error,passed=error<=1e-6,weights_sha256=actual))
    valid_checks=bool(events) and all(all(e['checks'].values()) for e in events) and all(r['passed'] for r in models)
    result=dict(source=str(args.trial.resolve()),checked_contexts=len(events),paired_exact_source_maps=len(paired),
                all_checks_passed=valid_checks and not damaged,
                readable_context_checks_passed=valid_checks,damaged_contexts=damaged,
                model_replays=models,events=events,
                caveat='Only saved10s inference samples, not every map. Verifies recording/model/mask consistency, not physical truth or route safety.')
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='events'},indent=2))
    if not valid_checks or (damaged and not args.record_damaged_contexts):raise SystemExit(1)


if __name__=='__main__':main()
