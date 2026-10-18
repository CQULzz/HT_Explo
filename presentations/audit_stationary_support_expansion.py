#!/usr/bin/env python3
"""Separate new neural support from changed predictions at a fixed world pose."""
import argparse
import json
from pathlib import Path

import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('folder',type=Path);args=ap.parse_args()
    with np.load(args.folder/'before.npz') as old,np.load(args.folder/'after.npz') as new:
        x,y,yaw=new['robot'];cx,cy,res=new['ht_geometry'];ocx,ocy,ores=old['ht_geometry']
        if abs(res-ores)>1e-9:raise ValueError('Different cell resolutions')
        shifts=np.array([cx-ocx,cy-ocy])/res
        if np.max(np.abs(shifts-np.round(shifts)))>1e-4:raise ValueError('Fields do not share the same world cell lattice')
        n,m=new['ht_ht_valid'].shape;k=int(np.floor(yaw/(np.pi/4)+.5))%8
        r=int(np.floor(n*.5-(x-cx)/res));c=int(np.floor(m*.5-(y-cy)/res))
        ii,jj=np.indices((n,m));body=np.hypot(ii-r,jj-c)*res<=.6+np.sqrt(2)*res
        bad=body&(new['ht_ht_valid']>=.5)&(new[f'ht_ht_dir_{k}']<.5);cells=[]
        for ri,ci in zip(*np.nonzero(bad)):
            wx=cx+(n*.5-ri-.5)*res;wy=cy+(m*.5-ci-.5)*res
            ro=int(np.floor(n*.5-(wx-ocx)/ores));co=int(np.floor(m*.5-(wy-ocy)/ores))
            if not(0<=ro<n and 0<=co<m):raise ValueError('Before field does not cover the queried footprint')
            p=float(old[f'ht_ht_dir_{k}'][ro,co])
            cells.append(dict(world_x=wx,world_y=wy,after_probability=float(new[f'ht_ht_dir_{k}'][ri,ci]),
                before_neural_valid=bool(old['ht_ht_valid'][ro,co]>=.5),
                before_physical_valid=bool(old['ht_ht_observation_valid'][ro,co]>=.5),
                before_probability=p if np.isfinite(p) else None))
        ro=int(np.floor(n*.5-(x-ocx)/ores));co=int(np.floor(m*.5-(y-ocy)/ores))
        result=dict(channel=k,robot=new['robot'].tolist(),
            center_probability_before=float(old[f'ht_ht_dir_{k}'][ro,co]),
            center_probability_after=float(new[f'ht_ht_dir_{k}'][r,c]),
            new_low_probability_body_cells=len(cells),previously_neural_unknown=sum(not a['before_neural_valid'] for a in cells),
            previously_physical_known=sum(a['before_physical_valid'] for a in cells),cells=cells,
            scope='Exact shared world lattice; same pose,0.6m footprint plus deployed raster margin,0.5 threshold. This audits the gate inputs, not true terrain safety or the correctness of double footprint inflation.')
    (args.folder/'new_support_cells.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='cells'},indent=2))


if __name__=='__main__':main()
