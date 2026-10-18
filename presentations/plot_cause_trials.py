#!/usr/bin/env python3
"""Compare complete indoor diagnostic trials without claiming a paired effect."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--fixed-job',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();root=Path(__file__).resolve().parents[1]
    raw=root/'presentations/scheduled_results';audit=root/'docs/results/ht_completion_cause_audit_2026-10-18'
    cases=[('阶段19细视点','ht_indoor_dense_10min_2026-10-17_12-38-24',None),
        ('阶段20历史轮','ht_recovery_verified_10min_2026-10-17_14-55-26',None),
        ('同策略只读诊断','ht_completion_diagnostic_2026-10-18_01-06-52',None),
        ('退路候选（失败）','ht_reversible_motion_10min_2026-10-18_01-26-31','reversible_indoor'),
        ('联合候选（失败）','ht_combined_admission_10min_2026-10-18_01-52-52','combined_indoor'),
        ('仅修正停车消息','ht_zero_twist_verified_10min_2026-10-18_02-15-15',None),
        ('修正停车＋32航向',str(args.fixed_job.resolve()),None)]
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,axes=plt.subplots(1,3,figsize=(18,5),layout='constrained');records=[]
    palette=plt.get_cmap('tab10')
    mission_colors={'EXPLORING':'#4c9c69','BLOCKED':'#c9514b','RETURNING_HOME':'#e7b348','COMPLETED':'#397eb3'}
    for i,(name,job,corrected) in enumerate(cases):
        p=(raw/job if not Path(job).is_absolute() else Path(job))/'indoor'
        summary=json.loads((p/'summary.json').read_text());assert summary['duration_s']==600
        volume_path=audit/'corrected_metrics'/corrected/'observation_volume.csv' if corrected else p/'current/observation_volume.csv'
        v=rows(volume_path);m=rows(p/'current/timeseries.csv');color=palette(i)
        axes[0].plot([float(r['time_s'])/60 for r in v],[float(r['observed_free_volume_m3']) for r in v],label=name,color=color)
        axes[1].plot([float(r['t_s'])/60 for r in m],[float(r['distance_m']) for r in m],color=color)
        origin=json.loads((p/'current/measurement_started.json').read_text())['wall_time']
        health=[r for r in rows(p/'health.csv') if 0<=float(r['wall_time'])-origin<600]
        for r in health:
            axes[2].broken_barh([((float(r['wall_time'])-origin)/60,1/60)],(i-.35,.7),facecolors=mission_colors.get('RETURNING_HOME' if r['mission']=='RETURNING' else r['mission'],'#888'))
        records.append(dict(label=name,source=str(p),distance_m=summary['distance_m'],
            observed_free_volume_m3=float(v[-1]['observed_free_volume_m3']),volume_source=str(volume_path),
            final_mission=health[-1]['mission']))
    axes[0].set(title='近似观测自由体积',ylabel='m³');axes[1].set(title='实际运动距离',ylabel='m')
    axes[2].set(title='任务状态（1Hz记录）',yticks=range(len(cases)),yticklabels=[r[0] for r in cases])
    for ax in axes:ax.set_xlim(0,10);ax.set_xlabel('时间 / 分钟');ax.grid(alpha=.2)
    axes[0].legend(fontsize=8,loc='upper left')
    from matplotlib.patches import Patch
    axes[2].legend(handles=[Patch(color=c,label=n) for n,c in mission_colors.items()],fontsize=8,loc='upper left')
    fig.suptitle('同一室内环境，每轮600秒；不同轨迹、部分策略不同，每配置一次，不能视作配对因果效果\n候选轮体积按同一记录包更正重复分秒；状态完成不代表真实全覆盖',fontsize=12)
    args.output.mkdir(parents=True,exist_ok=True);fig.savefig(args.output/'indoor_trials.png',dpi=160);plt.close(fig)
    (args.output/'indoor_trials.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
