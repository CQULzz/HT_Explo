#!/usr/bin/env python3
"""Reconstruct a stopped snapshot using saved history, not a closed-loop replay."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/ht_cupy_bridge'))
from historical_elevation import HistoricalElevation
from elevation_quality import preprocess_elevation,retain_recent_obstacle_edges
from local_surface import SurfaceReferenceEstimator
from ht_support import prepare_ht_context
from cpu_threads import configure_cpu_threads
from model import load_student_model


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('snapshot',type=Path)
    ap.add_argument('history',type=Path)
    ap.add_argument('--robot-z',type=float,required=True,help='Sensor-frame odometry Z at this flat-floor stop')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    a=np.load(args.snapshot,allow_pickle=False);saved=np.load(args.history,allow_pickle=False)
    res=float(saved['resolution']);h=HistoricalElevation(res)
    h.tiles={tuple(k):(saved['elevation_modes'][i].copy(),saved['variance_modes'][i].copy(),
                       saved['last_seen_modes'][i].copy()) for i,k in enumerate(saved['keys'])}
    if 'rejected_observation_time' in saved:
        h.rejections={tuple(k):saved['rejected_observation_time'][i].copy() for i,k in enumerate(saved['keys'])}
    if 'rejected_height' in saved:
        h.rejected_heights={tuple(k):saved['rejected_height'][i].copy() for i,k in enumerate(saved['keys'])}
    stamp=max(float(a['cupy_stamp']),max(float(t[2].max()) for t in h.tiles.values()))
    z,v,age=(a[k] for k in ['cupy_elevation','cupy_variance','cupy_observation_age'])
    cx,cy,_=a['cupy_geometry'];sq=preprocess_elevation(z,v,res)
    current=np.where(sq.observed_quality,z,np.nan)
    count=h.record_rejections(sq.rejected_mask,cx,cy,stamp,
        float(a['cupy_stamp'])-age.astype(np.float64),elevation=z)
    align=lambda x,fill=np.nan:h.aligned_source_window(x,cx,cy,291,fill_value=fill)
    reference,reference_stats=SurfaceReferenceEstimator().estimate(
        align(current),align(v),res,align(age),args.robot_z)
    selected,var,cx,cy=h.window(cx,cy,291,stamp,reference_height=reference,
        preferred_elevation=np.where(align(age)<=2,align(current),np.nan))
    selected,var,_=retain_recent_obstacle_edges(selected,var,align(current),align(v),align(age),
        align(sq.edge_mask.astype(np.float32),0)>=.5)
    rejected=h.last_window_incompatible_mask.copy();selected[rejected]=np.nan
    quality=preprocess_elevation(selected,var,res);rejected|=quality.rejected_mask
    height,support,occupied,physical=prepare_ht_context(quality.height_m,quality.observed_quality,
        rejected,h.last_window_obstacle_elevation,res)
    limit,_=configure_cpu_threads(4)
    model=load_student_model(str(ROOT/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'),
                            torch.device('cpu')).to(memory_format=torch.channels_last)
    with torch.inference_mode():
        p=torch.softmax(model(torch.from_numpy(height[None,None]).contiguous(
            memory_format=torch.channels_last)),dim=2)[0,:,1].numpy()
    p[:,occupied]=0;support|=occupied
    x,y,yaw=a['robot'];r=int(np.floor(120.5-(x-cx)/res));c=int(np.floor(120.5-(y-cy)/res))
    ii,jj=np.indices(physical.shape);body=np.hypot(ii-r,jj-c)*res<=.6+np.sqrt(2)*res
    result=dict(method='Post-hoc reconstruction from a stopped snapshot and saved historical modes; not a full stream or closed-loop replay',
        snapshot=str(args.snapshot.resolve()),history=str(args.history.resolve()),
        source_sha256={str(path.resolve()):hashlib.sha256(path.read_bytes()).hexdigest()
                       for path in [args.snapshot,args.history]},
        evaluation_stamp=stamp,source_stamp=float(a['cupy_stamp']),robot_z_hint=args.robot_z,
        old_center_context=float(a['ht_ht_valid'][r,c]),new_center_context=bool(support[r,c]),
        center_occupied=bool(occupied[r,c]),center_physical=bool(physical[r,c]),
        center_probabilities=p[:,r,c].tolist(),new_rejections=count,
        unknown_body_cells=int((~physical&body).sum()),
        blocked_body_cells_per_heading=[int(((p[k]<.5)&support&body).sum()) for k in range(8)],
        rejected_context_cells=int(rejected[r:r+51,c:c+51].sum()),surface=reference_stats)
    (out/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    np.savez_compressed(out/'reconstructed_map.npz',height=height,support=support,physical=physical,
        occupied=occupied,p=p,robot=a['robot'],geometry=[cx,cy,res],old_support=a['ht_ht_valid'])
    with (out/'cpp_fixture.txt').open('w') as f:
        f.write(f'241 241 {res:.17g} {cx:.17g} {cy:.17g} {x:.17g} {y:.17g} {yaw:.17g}\n')
        np.savetxt(f,np.stack([*p,support,physical],axis=-1).reshape(-1,10),fmt='%.9g')
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    extent=(cx-241*res/2,cx+241*res/2,cy-241*res/2,cy+241*res/2)
    fig,axes=plt.subplots(1,3,figsize=(14,4.5),layout='constrained')
    fields=[a['ht_ht_valid'],support,occupied]
    titles=['原神经网络上下文有效性','修正后上下文有效性','实测禁行格：八方向概率强制为0']
    for ax,field,title in zip(axes,fields,titles):
        ax.imshow(field[::-1,::-1].T,origin='lower',extent=extent,interpolation='nearest',vmin=0,vmax=1,cmap='Greys')
        ax.plot(x,y,'r+',ms=10);ax.add_patch(plt.Circle((x,y),.6,fill=False,color='#e69f00'))
        ax.set(title=title,xlabel='X / m',ylabel='Y / m')
    fig.suptitle('同一停滞快照重建：红十字为车，橙圈为0.6m足迹；有效上下文不等于允许通行')
    fig.savefig(out/'context_recovery.png',dpi=180);plt.close(fig)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
