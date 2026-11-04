#!/usr/bin/env python3
"""Derive the confirmed URDF rear-deck material; never fill its gaps."""
import argparse
import hashlib
from pathlib import Path
import numpy as np

parser=argparse.ArgumentParser()
parser.add_argument('--stl',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args()
raw=args.stl.read_bytes();digest=hashlib.sha256(raw).hexdigest()
if digest!='828a686c1a0ec7d66e727fc7772600a98f24bb709b566be82d2d5ca43f1e7754':
    raise ValueError('Rack STL differs from the audited URDF source')
count=int.from_bytes(raw[80:84],'little')
if len(raw)!=84+count*50:raise ValueError('Invalid binary STL length')
dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
triangles=np.frombuffer(raw,dtype=dtype,offset=84,count=count)['vertices'].astype(np.float64)
# Select the entire physical rear top surface, independently of recorded hits.
selected=np.all(np.abs(triangles[:,:,2]-.189)<1e-7,axis=1)&(triangles[:,:,0].max(axis=1)<-.1)
triangles=triangles[selected]+np.array([.1725,0.,.1162])
if triangles.shape!=(536,3,3):raise ValueError('Rear-deck topology changed')
if args.output.exists():raise FileExistsError(args.output)
np.savez_compressed(args.output,triangles=triangles,source_triangle_ids=np.flatnonzero(selected),
                    source_stl_sha256=np.array(digest))
