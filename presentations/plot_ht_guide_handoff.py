#!/usr/bin/env python3
"""Plot measured same-scene curves and logged guide changes; no invented paths."""
import argparse,csv,hashlib,json,re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def rows(path):
    with path.open() as stream:return list(csv.DictReader(stream))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='append',required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,axes=plt.subplots(2,3,figsize=(19,11),layout='constrained');colors=['#718298','#dc842a','#158773']
    evidence=[]
    for index,spec in enumerate(args.run):
        label,folder=spec.split('=',1);folder=Path(folder);color=colors[index%len(colors)]
        def file(name):return folder/name if (folder/name).exists() else folder/'current'/name
        mp,vp=file('timeseries.csv'),file('observation_volume.csv');motion,volume=rows(mp),rows(vp)
        t=np.array([float(r['t_s']) for r in motion]);xy=np.array([[float(r['x_m']),float(r['y_m'])] for r in motion])
        vt=np.array([float(r['time_s']) for r in volume]);v=np.array([float(r['observed_free_volume_m3']) for r in volume])
        d=np.array([float(r['distance_m']) for r in motion]);entered=[]
        for p in np.floor(xy).astype(int):
            key=tuple(p)
            if not entered or key!=entered[-1]:entered.append(key)
        revisit=(len(entered)-len(set(entered)))/max(1,len(entered)-1)
        axes[0,0].plot(vt,v,label=label,color=color);axes[0,1].plot(t,d,label=label,color=color)
        minutes=np.arange(0,601,60);gain=np.diff(np.interp(minutes,vt,v))
        axes[0,2].bar(np.arange(10)+index*.24,gain,width=.23,label=label,color=color)
        axes[1,0].plot(xy[:,0],xy[:,1],label=label,color=color,alpha=.85)
        axes[1,0].plot(*xy[-1],marker='o',color=color)
        # Selected archives retain throttled, time-stamped plan rows as events.
        events=json.loads((folder/'target_selection_audit.json').read_text())['guide_events']
        changes=[]
        for r in events:
            match=re.search(r'HT guide selected: \(([^)]+)\)',r['log'])
            if match:changes.append((r['time_s'],float(match[1].split(',')[1])))
        if changes:
            ct,cy=zip(*changes);axes[1,1].step([*ct,600],[*cy,cy[-1]],where='post',label=label,color=color)
        audit=json.loads((folder/'endurance_audit.json').read_text());metrics=audit['external_metrics']
        vals=[revisit*100,metrics['stationary_turn_fraction']*100,metrics['fully_stopped_fraction']*100]
        axes[1,2].bar(np.arange(3)+index*.24,vals,width=.23,label=label,color=color)
        evidence.append(dict(label=label,source=str(folder.resolve()),volume_m3=float(v[-1]),
            cumulative_decreases=int(sum(np.diff(v)<0)),repeat_entry_fraction=revisit,
            last60_gain_m3=float(v[-1]-np.interp(540,vt,v)),per_minute_gain_m3=list(gain),
            guide_selected_events=len(changes),input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in [mp,vp,folder/'target_selection_audit.json',folder/'endurance_audit.json']}))
    for axis,title,xlabel,ylabel in [
        (axes[0,0],'累计观测自由体积：每轮均单调不减','测量时间 / s','近似自由体积 / m³'),
        (axes[0,1],'累计实际里程','测量时间 / s','里程 / m'),
        (axes[0,2],'每分钟新增观测：是否仍在获得新信息','分钟区间','新增 / m³'),
        (axes[1,0],'同尺度实际轨迹：圆点为终点','X / m','Y / m'),
        (axes[1,1],'日志中引导目标Y坐标（非车辆路径）','测量时间 / s','目标Y / m'),
        (axes[1,2],'回访、原地转向与完全停车','指标','占比 / %')]:
        axis.set(title=title,xlabel=xlabel,ylabel=ylabel);axis.grid(alpha=.2);axis.legend(fontsize=9)
    axes[0,2].set_xticks(np.arange(10)+.24,[f'{i}–{i+1}' for i in range(10)])
    axes[1,2].set_xticks(np.arange(3)+.24,['1m格重复进入','原地转向','完全停车'])
    axes[1,0].set_aspect('equal',adjustable='datalim')
    fig.suptitle('车库同条件600秒：阶段38修复任务交接；对照阶段36/37\n每版本一轮，含全部退步；体积是0.5m自由体素并集估计，回访受格边界抖动影响',fontsize=15)
    for suffix in ['png','pdf']:fig.savefig(args.output/('guide_handoff_comparison.'+suffix),dpi=160,bbox_inches='tight')
    plt.close(fig)
    (args.output/'plot_evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
