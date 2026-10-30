#!/usr/bin/env python3
"""Inspect one saved HT cell and its original 51x51 inference window, read-only."""
import argparse
import json
from pathlib import Path
import math
import numpy as np
from ht_reasons import REASON_FLAGS


def locate_cell(shape,center,resolution,x,y):
    if len(shape)!=2 or not all(math.isfinite(v) for v in (*center,resolution,x,y)) or resolution<=0:
        raise ValueError('Invalid axis-aligned map query')
    rx=shape[0]*.5-(x-center[0])/resolution
    cy=shape[1]*.5-(y-center[1])/resolution
    if not (0<=rx<shape[0] and 0<=cy<shape[1]):raise ValueError('Query outside saved map')
    return math.floor(rx),math.floor(cy)


def inspect_cell(frame,reason,context,x,y,direction):
    if not 0<=direction<8:raise ValueError('direction must be 0..7')
    stamp=int(frame['stamp_ns'])
    if stamp!=int(reason['stamp_ns']) or stamp!=int(context['stamp_ns']):
        raise ValueError('Refuse mixing different source stamps')
    if not np.array_equal(frame['center'],reason['center']) or float(frame['resolution'])!=float(reason['resolution']):
        raise ValueError('Reason/map geometry mismatch')
    shape=frame['ht_valid'].shape
    if reason['reason_flags'].shape!=shape or context['height'].shape!=(shape[0]+50,shape[1]+50):
        raise ValueError('Saved arrays do not match HT receptive field')
    row,col=locate_cell(shape,frame['center'],float(frame['resolution']),x,y)
    flags=int(reason['reason_flags'][row,col])
    def number(v):return float(v) if np.isfinite(v) else None
    explanation={'source_ns':stamp,'query_xy':[x,y],'row':row,'column':col,'direction_channel':direction,
        'effective_score':number(frame[f'ht_dir_{direction}'][row,col]),
        'raw_model_min_probability':number(reason['raw_model_min_probability'][row,col]),
        'reason_flags':flags,'reasons':[name for name,bit in REASON_FLAGS.items() if flags&bit],
        'context_valid':bool(frame['ht_valid'][row,col]>=.5),
        'physical_support_layer':bool(frame['ht_observation_valid'][row,col]>=.5),
        'occupied_layer':bool(frame['ht_obstacle'][row,col]>=.5),
        'scope':'Diagnostics only, channel index is not physical terrain calibration; support layer is existing proximity-based support, not direct-return ground truth'}
    return explanation,context['height'][row:row+51,col:col+51].copy()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ['frame','reason','context','output']:p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--x',type=float,required=True);p.add_argument('--y',type=float,required=True)
    p.add_argument('--direction',type=int,default=0);a=p.parse_args()
    with np.load(a.frame) as frame,np.load(a.reason) as reason,np.load(a.context) as context:
        explanation,window=inspect_cell(frame,reason,context,a.x,a.y,a.direction)
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'explanation.json').write_text(json.dumps(explanation,ensure_ascii=False,indent=2)+'\n')
    np.save(a.output/'input_window.npy',window)
    print(json.dumps(explanation,ensure_ascii=False))


if __name__=='__main__':main()
