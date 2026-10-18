#!/usr/bin/env python3
"""Show a recorded nearest-direction discontinuity and successor reserve."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('snapshot',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    a=np.load(args.snapshot);x,y,before=a['robot'];after=a['crossed_pose'][2]
    cx,cy,res=a['ht_geometry'];r=int(np.floor(120.5-(x-cx)/res));c=int(np.floor(120.5-(y-cy)/res))
    ii,jj=np.indices((241,241));body=np.hypot(ii-r,jj-c)*res<=.6+np.sqrt(2)*res
    valid=a['ht_ht_valid']>.5
    minima=np.array([np.nanmin(a[f'ht_ht_dir_{k}'][body&valid]) for k in range(8)])
    angle=np.linspace(0,45,4501);margin=np.rad2deg(.05)
    query=lambda theta:minima[(np.floor(theta/45+.5).astype(int))%8]
    raw=query(angle);reserve=np.minimum(query(angle-margin),query(angle+margin))
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,ax=plt.subplots(figsize=(11,5),layout='constrained')
    ax.plot(angle,raw,label='原始足迹最小HT概率：最近方向查询',linewidth=2)
    ax.plot(angle,reserve,'--',label='规划后继角度±0.05rad范围的最差值',linewidth=2)
    ax.axhline(.5,color='red',linestyle=':',label='原硬阈值0.5保持不变')
    ax.axvspan(22.5-margin,22.5,color='#edc766',alpha=.3,label='新增规划角度余量区')
    ax.scatter(np.rad2deg([before,after]),[query(np.rad2deg(before)),query(np.rad2deg(after))],c=['#278138','#bd2929'],s=55,zorder=5)
    ax.set(xlim=(0,45),ylim=(-.05,1.08),xlabel='查询车头角度 / 度',ylabel='足迹内最小HT概率',
        title='真实卡停记录：同一XY格子，约0.017°跨界导致硬判定跳变')
    ax.text(1,.35,f'记录：{np.rad2deg(before):.6f}° → {np.rad2deg(after):.6f}°\n'
        f'原最小概率：{query(np.rad2deg(before)):.6f} → {query(np.rad2deg(after)):.6f}\n'
        '这描述离散HT查询，不代表真实地形突然改变。',fontsize=10)
    ax.text(1,.07,'余量约2.86°，仅约束规划后继状态；真实起点仍须通过原硬门槛，可向安全角度转回。',fontsize=9)
    ax.grid(alpha=.2);ax.legend(loc='upper right',fontsize=9)
    fig.savefig(args.output/'heading_boundary.png',dpi=180);plt.close(fig)
    (args.output/'boundary_numbers.json').write_text(json.dumps(dict(before_deg=float(np.rad2deg(before)),after_deg=float(np.rad2deg(after)),
        delta_deg=float(np.rad2deg(after-before)),body_minimum_by_direction=minima.tolist(),
        margin_deg=float(margin),source_stamp=float(a['ht_stamp']),transition_time_s=float(a['transition_time_s'])),indent=2)+'\n')


if __name__=='__main__':main()
