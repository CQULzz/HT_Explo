#!/usr/bin/env python3
"""Summarize controlled static and moving elevation-chain captures."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE=Path(__file__).resolve().parent
BASE=HERE/'scheduled_results';OUT=BASE/'noise_source_analysis_2026-10-13';OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
names=['noise_static_2026-10-13','noise_static_unit_resolution_2026-10-13','noise_static_dense_2026-10-13']
labels=['原配置：360×64','resolution=1：360×64','加密采样：720×128']
ranges=[(0,1),(1,2),(2,3),(3,5)];results=[];frames=[]
for name,label in zip(names,labels):
    files=sorted((BASE/name/'noise').glob('*.npz'));d=np.load(files[-1]);p=d['raw_points'];r=np.hypot(p[:,0],p[:,1]);metrics=[]
    for lo,hi in ranges:
        # Restrict to the clear floor strip, excluding nearby column bases.
        a=p[(p[:,2]>-.9)&(p[:,2]<-.55)&(abs(p[:,0])<1)&(r>=lo)&(r<hi)]
        A=np.c_[a[:,:2],np.ones(len(a))];coef=np.linalg.lstsq(A,a[:,2],rcond=None)[0]
        metrics.append(float(np.percentile(abs(a[:,2]-A@coef),95)*1000))
    results.append({'label':label,'run':name,'point_count':len(p),'residual_p95_mm':metrics,
                    'last_frames_identical':bool(np.array_equal(np.load(files[-2])['raw_points'],p))})
    frames.append((p,d['odom']))
fig,ax=plt.subplots(figsize=(10,5),constrained_layout=True)
for result in results:ax.plot(['0–1 m','1–2 m','2–3 m','3–5 m'],result['residual_p95_mm'],'o-',label=result['label'],lw=2)
ax.set(xlabel='距雷达的水平距离',ylabel='平面残差绝对值的 95 分位（mm）',title='静止平地：噪声在 Gazebo 原始雷达点云中已出现')
ax.legend();ax.grid(alpha=.2);fig.savefig(OUT/'raw_lidar_error_vs_range.png',dpi=180);plt.close(fig)
fig,axes=plt.subplots(1,2,figsize=(13,5.5),constrained_layout=True)
for ax,idx in zip(axes,[0,2]):
    p,odom=frames[idx];r=np.hypot(p[:,0],p[:,1]);a=p[(p[:,2]>-.9)&(p[:,2]<-.55)&(abs(p[:,0])<1)&(r<5)]
    # Static pose has identity rotation. Ground's exact mesh surface is 0.12702461 m.
    err=(a[:,2]+odom[2]-.12702461)*1000
    im=ax.scatter(a[:,0],a[:,1],c=err,s=2,cmap='coolwarm',vmin=-50,vmax=50)
    ax.set(title=labels[idx],xlabel='雷达局部 X（m）',ylabel='雷达局部 Y（m）',xlim=(-5,5),ylim=(-5,5),aspect='equal')
fig.colorbar(im,ax=axes,label='相对真实平地高度的误差（mm）');fig.suptitle('平地高度误差带：固定误差不能靠重复帧平均消除')
fig.savefig(OUT/'raw_lidar_error_field.png',dpi=180);plt.close(fig)

moving=BASE/'noise_chain_2026-10-13_15-26-34/noise';series=[]
for f in sorted(moving.glob('*.npz')):
    d=np.load(f);entry={'file':f.name,'robot_xy':d['odom'][:2].tolist()}
    for kind in ['cupy','history']:
        z=d[kind];cx,cy,res=d[kind+'_geometry'];n,m=z.shape
        xx=cx+(n/2-np.arange(n)-.5)*res;yy=cy+(m/2-np.arange(m)-.5)*res
        crop=z[np.ix_(abs(xx-1)<1,abs(yy-11)<1)]
        diff=np.r_[abs(np.diff(crop,axis=0)).ravel(),abs(np.diff(crop,axis=1)).ravel()];diff=diff[np.isfinite(diff)]
        entry[kind+'_jump95_mm']=float(np.percentile(diff,95)*1000) if len(diff)>10 else None
    series.append(entry)
fig,ax=plt.subplots(figsize=(11,5),constrained_layout=True)
for kind,label in [('cupy','CuPy 发布高程'),('history','历史融合后的局部高程')]:
    ax.plot(np.arange(len(series))*2,[s[kind+'_jump95_mm'] or np.nan for s in series],label=label,lw=2)
ax.set(xlabel='采集序列时间（约 s；包括规划启动前等待）',ylabel='相邻格高度差的 95 分位（mm）',title='同一固定区域 (1,11) m：逐层比较，不同于点云平面残差')
ax.legend();ax.grid(alpha=.2);fig.savefig(OUT/'cupy_vs_history.png',dpi=180);plt.close(fig)
(OUT/'metrics.json').write_text(json.dumps({'static':results,'moving_series':series},ensure_ascii=False,indent=2)+'\n')
print(OUT)
