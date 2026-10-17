#!/usr/bin/env python3
"""Plot a recorded HT directional restriction, without claiming terrain truth."""
import argparse
import json
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('snapshot',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    a=np.load(args.snapshot,allow_pickle=False);x,y,yaw=a['robot'];cx,cy,res=a['ht_geometry']
    p=np.stack([a[f'ht_ht_dir_{k}'] for k in range(8)]);valid=a['ht_ht_valid']>.5
    physical=a['ht_ht_observation_valid']>.5
    radius=int(np.ceil(.6/res)+1);ii,jj=np.mgrid[-radius:radius+1,-radius:radius+1]
    kernel=(np.hypot(ii,jj)*res<=.6+np.sqrt(2)*res).astype('uint8')
    unknown=cv2.dilate((~physical).astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=1)>0
    blocked=np.stack([cv2.dilate((valid&(pk<.5)).astype('uint8'),kernel)>0 for pk in p])
    status=np.where(blocked,2,np.where(unknown|~valid,0,1))
    r=int(np.floor(120.5-(x-cx)/res));c=int(np.floor(120.5-(y-cy)/res))
    ii,jj=np.indices(valid.shape);body=np.hypot(ii-r,jj-c)*res<=.6+np.sqrt(2)*res
    metadata=dict(robot=a['robot'].tolist(),geometry=a['ht_geometry'].tolist(),source_stamp=float(a['ht_stamp']),
        low_probability_body_cells=[int((valid&body&(pk<.5)).sum()) for pk in p],
        minimum_body_probability=[float(np.nanmin(pk[body&valid])) for pk in p],
        unknown_body_cells=int((~physical&body).sum()),
        forced_zero_body_cells=int(((p==0).all(axis=0)&body).sum()),
        limit='Predicted HT constraints, not physical terrain ground truth or a continuous reachability proof.')
    (out/'footprint_evidence.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    cv2.imwrite(str(out/'camera.jpg'),a['camera'])
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    extent=(cx-241*res/2,cx+241*res/2,cy-241*res/2,cy+241*res/2)
    cmap=ListedColormap(['#bfc3c6','#50a66b','#c84b45']);norm=BoundaryNorm([-.5,.5,1.5,2.5],3)
    def draw(ax,field,title):
        ax.imshow(field[::-1,::-1].T,origin='lower',extent=extent,cmap=cmap,norm=norm,interpolation='nearest')
        ax.plot(x,y,'b+',ms=9);ax.arrow(x,y,.35*np.cos(yaw),.35*np.sin(yaw),color='blue',width=.012)
        ax.set(xlim=(x-2,x+2),ylim=(y-2,y+2),title=title,xlabel='X / m',ylabel='Y / m')
    fig,axes=plt.subplots(2,4,figsize=(14,8),layout='constrained')
    for k,ax in enumerate(axes.flat):draw(ax,status[k],f'查询方向 {45*k}°：车位状态 {int(status[k,r,c])}')
    fig.suptitle('同一停滞快照的八方向HT足迹检查：绿=该方向允许，红=含低概率格，灰=支撑不足\n蓝箭头为实际车头；这是模型约束，不是真实地形通行结论')
    fig.savefig(out/'directional_footprints.png',dpi=170);plt.close(fig)
    paired=np.where((status[0]==2)|(status[4]==2),2,np.where((status[0]==0)|(status[4]==0),0,1))
    fig,axes=plt.subplots(1,3,figsize=(13,4.5),layout='constrained')
    draw(axes[0],status[0],'沿0°方向检查')
    draw(axes[1],status[4],'原车头倒退：检查180°行驶方向')
    draw(axes[2],paired,'候选规则：正反行驶均通过才接纳')
    fig.suptitle('单向可走不等于能沿原轨迹退回；新规则是保守的局部退路检查，不保证未来地图或全局返航')
    fig.savefig(out/'retrace_gate.png',dpi=170);plt.close(fig)


if __name__=='__main__':main()
