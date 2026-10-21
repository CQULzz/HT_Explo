#!/usr/bin/env python3
"""Compare old/new filtering on one exact saved input; no ROS or navigation writes."""
import argparse,hashlib,json,subprocess,sys,types
from pathlib import Path
import numpy as np
import torch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/ht_cupy_bridge'))
from elevation_quality import preprocess_elevation
from ht_support import prepare_ht_context
from model import load_student_model


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--context',type=Path,required=True)
    ap.add_argument('--snapshot',type=Path);ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--baseline-ref',default='f381a73')
    ap.add_argument('--points',default='[[2.25,5.25],[2.55,5.25],[2.85,5.25],[3.15,5.25],[2.25,5.55],[2.55,5.55],[2.85,5.55],[3.15,5.55],[3.45,5.55],[3.75,5.55],[3.45,5.85],[3.75,5.85]]')
    a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    with np.load(a.context) as file:d={k:file[k] for k in file.files}
    if 'history_variance' in d:variance=d['history_variance']
    elif a.snapshot:
        with np.load(a.snapshot) as s:
            if abs(float(s['ht_stamp'])-float(d['source_stamp']))>1e-6 or not np.array_equal(s['history_elevation_raw'],d['raw_history'],equal_nan=True):
                raise ValueError('Snapshot is not the exact context source stamp/history')
            variance=s['history_variance'].copy()
    else:raise ValueError('Old context needs its exact-stamp variance snapshot')
    original_source=subprocess.check_output(['git','show',a.baseline_ref+':tools/ht_cupy_bridge/elevation_quality.py'],cwd=ROOT,text=True)
    module=types.ModuleType('_saved_baseline_elevation_quality');sys.modules[module.__name__]=module
    exec(compile(original_source,'baseline/elevation_quality.py','exec'),module.__dict__)
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    weights=ROOT/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'
    model=load_student_model(str(weights),torch.device('cpu'))
    cx,cy,res=d['geometry'];points=json.loads(a.points);rows=[]
    for xy in points:
        i,j=int(np.floor(120.5-(xy[0]-cx)/res)),int(np.floor(120.5-(xy[1]-cy)/res))
        if not (0<=i<241 and 0<=j<241):raise ValueError('Requested point outside scored context')
        rows.append(dict(xy=xy,index=[i,j],recorded=d['probabilities'][:,i,j].tolist(),
                         supported=bool(d['support'][i,j]),occupied=bool(d['occupied'][i,j])))
    results={}
    for name,filter_function in [('baseline',module.preprocess_elevation),('candidate',preprocess_elevation)]:
        q=filter_function(d['raw_history'],variance,float(res))
        h,support,occupied,physical=prepare_ht_context(q.height_m,q.observed_quality,d['rejected'],d['obstacle_context'],float(res))
        patches=np.asarray([h[row['index'][0]:row['index'][0]+51,row['index'][1]:row['index'][1]+51] for row in rows],np.float32)
        with torch.inference_mode():p=torch.softmax(model(torch.from_numpy(patches[:,None])),dim=2)[:,:,1,0,0].numpy()
        for row,probabilities in zip(rows,p):
            if row['occupied']:probabilities[:]=0
            row[name]=probabilities.tolist();row[name+'_max']=float(probabilities.max())
        results[name]=dict(stats=q.stats,observed_unchanged=bool(np.array_equal(q.observed_quality,d['observed'])),
            physical_unchanged=bool(np.array_equal(physical,d['physical_support'])),
            obstacle_unchanged=bool(np.array_equal(occupied,d['occupied'])),
            context_support_unchanged=bool(np.array_equal(support|occupied,d['support'])),
            max_height_change_m=float(np.nanmax(np.abs(q.height_m-d['raw_history']))),
            replay_height_error_m=float(np.max(np.abs(h-d['height']))))
    replay=max(abs(x-y) for row in rows for x,y in zip(row['recorded'],row['baseline']))
    assert replay<1e-5, 'Baseline network output did not reproduce saved context'
    assert all(results['candidate'][k] for k in ['observed_unchanged','physical_unchanged','obstacle_unchanged','context_support_unchanged'])
    record=dict(source_stamp=float(d['source_stamp']),context=str(a.context),baseline_ref=a.baseline_ref,
        context_sha256=hashlib.sha256(a.context.read_bytes()).hexdigest(),weights_sha256=hashlib.sha256(weights.read_bytes()).hexdigest(),
        baseline_output_error=replay,results=results,points=rows,
        scope='Exact saved later-frame input, not the unsaved13.512s completion-trigger input. Offline filtering is not proof of a feasible vehicle path.')
    (a.output/'summary.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    for row in rows:print(row['xy'],round(row['baseline_max'],3),'->',round(row['candidate_max'],3))
    print('Masks unchanged; baseline output replay error',replay)


if __name__=='__main__':main()
