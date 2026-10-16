#!/usr/bin/env python3
"""Compare equal-duration prefixes of two completed endurance recordings."""
import argparse
import csv
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def table(folder, name):
    path = folder/'current'/name
    if not path.exists():
        path = folder/name
    with path.open() as file:
        return list(csv.DictReader(file))


def data(folder):
    motion = table(folder, 'timeseries.csv')
    volume = table(folder, 'observation_volume.csv')
    return dict(t=np.array([float(r['t_s']) for r in motion]),
                distance=np.array([float(r['distance_m']) for r in motion]),
                x=np.array([float(r['x_m']) for r in motion]),
                y=np.array([float(r['y_m']) for r in motion]),
                vt=np.array([float(r['time_s']) for r in volume]),
                volume=np.array([float(r['observed_free_volume_m3']) for r in volume]))


def measures(d, end):
    mask=d['t']<=end
    return dict(duration_s=float(end), distance_m=float(np.interp(end,d['t'],d['distance'])),
                observed_free_volume_m3=float(np.interp(end,d['vt'],d['volume'])),
                visited_1m_xy_cells=len({(math.floor(x),math.floor(y)) for x,y in zip(d['x'][mask],d['y'][mask])}),
                last10min_observed_gain_m3=float(np.interp(end,d['vt'],d['volume'])-
                                                np.interp(max(0,end-600),d['vt'],d['volume'])),
                last10min_distance_m=float(np.interp(end,d['t'],d['distance'])-
                                          np.interp(max(0,end-600),d['t'],d['distance'])))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--current',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    old,new=data(a.baseline),data(a.current)
    end=min(old['t'][-1],new['t'][-1],old['vt'][-1],new['vt'][-1])
    results={'baseline':measures(old,end),'current':measures(new,end),
             'baseline_source':str(a.baseline.resolve()),'current_source':str(a.current.resolve()),
             'limitations':'One trial per build; equal-duration prefixes, not a statistical benchmark. Volume is a sampled lidar-ray free-voxel union, not ground-truth coverage. All physical speed and HT safety gates remain unchanged.'}
    (a.output/'comparison.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
    plt.rcParams['font.family']='Noto Sans CJK JP'
    fig,axes=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    for d,label,color in [(old,'修改前（60分钟长测的同期部分）','#7d8997'),(new,'修改后','#148f8b')]:
        t=d['t']<=end;v=d['vt']<=end
        axes[0,0].plot(d['vt'][v]/60,d['volume'][v],label=label,color=color)
        axes[0,1].plot(d['t'][t]/60,d['distance'][t],label=label,color=color)
        axes[1,0].plot(d['x'][t],d['y'][t],label=label,color=color,linewidth=1)
        axes[1,0].scatter(d['x'][t][-1],d['y'][t][-1],color=color,s=25)
        cells=set();counts=[]
        for x,y in zip(d['x'][t],d['y'][t]):
            cells.add((math.floor(x),math.floor(y)));counts.append(len(cells))
        axes[1,1].plot(d['t'][t]/60,counts,label=label,color=color)
    axes[0,0].set(title='累计观测自由体积（近似值）',xlabel='运行时间 / 分钟',ylabel='m³')
    axes[0,1].set(title='累计实际里程',xlabel='运行时间 / 分钟',ylabel='m')
    axes[1,0].set(title='实际行驶轨迹',xlabel='世界 X / m',ylabel='世界 Y / m')
    axes[1,0].set_aspect('equal',adjustable='datalim')
    axes[1,1].set(title='到访的 1 m × 1 m 轨迹格',xlabel='运行时间 / 分钟',ylabel='格数')
    for ax in axes.flat:
        ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle(f'HT 绕圈修复验证：同一 Garage、前 {end/60:.1f} 分钟、速度上限 0.5 m/s',fontsize=15)
    fig.savefig(a.output/'comparison.png',dpi=170);plt.close(fig)
    lines=['# HT 绕圈修复：同场景等时长比较','',
           f'比较前 {end/60:.1f} 分钟；修改前截取上一轮60分钟长测的同期数据。两次独立启动Garage，前进速度上限均为0.5m/s。','',
           '| 指标 | 修改前 | 修改后 |','|---|---:|---:|']
    for label,key in [('累计实际里程(m)','distance_m'),('累计观测自由体积(m³，近似)','observed_free_volume_m3'),
                      ('到访1米轨迹格','visited_1m_xy_cells'),('最后10分钟新增观测(m³)','last10min_observed_gain_m3'),
                      ('最后10分钟里程(m)','last10min_distance_m')]:
        lines.append(f'| {label} | {results["baseline"][key]:.2f} | {results["current"][key]:.2f} |')
    lines+=['','![轨迹与观测比较](comparison.png)','',
            '这是单次仿真回归比较，不代表所有环境或60分钟稳定性验证完成。观测体积按同一0.5m体素、15m射线范围和每秒最多1帧计算，属于累计自由空间近似，并非官方覆盖率。',
            '算法收益日志、完整控制状态、数据新鲜度和失败事件需同时参照本轮endurance_audit.json。']
    (a.output/'COMPARISON.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
