#!/usr/bin/env python3
"""Audit competing explanations for one indoor before/after pair; no causal ranking."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def read(path):return json.loads(path.read_text())


def rows(path):
    with path.open() as f:return list(csv.DictReader(f))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('before',type=Path,help='Raw trial folder')
    ap.add_argument('after',type=Path,help='Raw trial folder')
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    source_files=[];cases={}
    for label,p in [('before',args.before),('after',args.after)]:
        origin=read(p/'current/measurement_started.json')['wall_time']
        volume=rows(p/'current/observation_volume.csv')
        health=[r for r in rows(p/'health.csv') if origin<=float(r['wall_time'])<origin+600]
        audit=read(p/'endurance_audit.json')
        vt=np.array([float(r['time_s']) for r in volume]);v=np.array([float(r['observed_free_volume_m3']) for r in volume])
        peaks=max(health,key=lambda r:float(r['map_source_age_s']))
        source_files += [p/'current/measurement_started.json',p/'current/observation_volume.csv',p/'health.csv',p/'endurance_audit.json']
        cases[label]=dict(source=str(p.resolve()),volume_at_s={str(t):float(np.interp(t,vt,v)) for t in [60,120,180,215,328.43,600]},
            map_age_peak=dict(time_s=float(peaks['wall_time'])-origin,age_s=float(peaks['map_source_age_s']),mission=peaks['mission']),
            processed_volume_scans=audit['external_metrics']['processed_volume_scans'],
            skipped_volume_scans=audit['external_metrics']['skipped_volume_scans'],
            pose_time_offset_max_s=audit['external_metrics']['pose_time_offset_max_s'],
            raw_scan_count=audit['summary']['registered_scans'],
            first_exploration_finished_s=audit['mission_audit']['first_exploration_finished_sample_s'])
        cases[label]['plot']=(vt,v,np.array([float(r['wall_time'])-origin for r in health]),
                              np.array([float(r['map_source_age_s']) for r in health]))
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,axes=plt.subplots(1,2,figsize=(13,4.5),layout='constrained')
    for label,case in cases.items():
        vt,v,t,age=case.pop('plot')
        axes[0].plot(vt,v,label='原轮' if label=='before' else '修改后轮')
        axes[1].plot(t,age,label='原轮' if label=='before' else '修改后轮',alpha=.75,linewidth=.8)
    axes[0].axvline(215,color='#444',linestyle='--',label='修改后约215s触发返航')
    axes[1].axvline(215,color='#444',linestyle='--');axes[1].axhline(3,color='red',linestyle=':')
    peak=cases['after']['map_age_peak']
    axes[1].annotate('最大延迟发生于完成后',xy=(peak['time_s'],peak['age_s']),xytext=(270,5.5),
                     arrowprops=dict(arrowstyle='->'))
    axes[0].set(title='差距在返航前已经出现',xlabel='测量时间 / s',ylabel='近似自由体积 / m³')
    axes[1].set(title='地图年龄不能只看全程最大值',xlabel='测量时间 / s',ylabel='HT地图年龄 / s',ylim=(0,6))
    for ax in axes:ax.set_xlim(0,600);ax.grid(alpha=.2);ax.legend()
    fig.savefig(out/'competing_explanations.png',dpi=160);plt.close(fig)
    gap_total=cases['before']['volume_at_s']['600']-cases['after']['volume_at_s']['600']
    gap_at215=cases['before']['volume_at_s']['215']-cases['after']['volume_at_s']['215']
    result=dict(cases=cases,accounting=dict(final_gap_m3=gap_total,gap_already_at215_m3=gap_at215,
        change_in_gap_after215_m3=gap_total-gap_at215,
        caveat='Algebraic decomposition of observed runs, not the counterfactual gain of forcing longer exploration.'),
        source_sha256={str(p.resolve()):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        conclusion='One stochastic run per version, divergent trajectories, bundled modifications: no single cause of the 41.8% final difference can be identified from this pair. Inspect actual completion evidence before changing policy.')
    (out/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
