#!/usr/bin/env python3
"""Correct report-only5s boundary splitting; never modify a published source."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    job=json.loads(a.state.read_text());suite=Path(job['suite']);base=Path(job['archive'])
    out=base.with_name(base.name+'_review')
    out.mkdir(exist_ok=True)
    font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    from matplotlib import font_manager
    font_manager.fontManager.addfont(font)
    plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name()
    plt.rcParams['axes.unicode_minus']=False
    fig,axes=plt.subplots(1,2,figsize=(14,5),layout='constrained')
    audits={}
    for name,label,color in [('original','原TARE（同运动上限）','#2878b5'),('ht','最新HT','#ed7d31')]:
        root=suite/name;origin=json.loads((root/'current/measurement_started.json').read_text())['wall_time']
        source=root/'resources.csv';rows=list(csv.DictReader(source.open()));groups=[]
        for row in rows:
            wall=float(row['wall_time'])
            if not origin<=wall<origin+600:
                continue
            if not groups or wall-groups[-1]['first_wall']>1:
                groups.append(dict(first_wall=wall,last_wall=wall,cpu=0.,rss=0.,rows=0))
            g=groups[-1];g['last_wall']=wall;g['rows']+=1;g['rss']+=float(row['rss_mb'])
            if row['cpu_percent']:
                g['cpu']+=float(row['cpu_percent'])
        output_rows=[dict(time_s=g['first_wall']-origin,cpu_percent=g['cpu'],rss_mib=g['rss'],
                          process_rows=g['rows'],batch_span_s=g['last_wall']-g['first_wall']) for g in groups]
        with (out/(name+'_resource_batches.csv')).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(output_rows[0]),lineterminator='\n');w.writeheader();w.writerows(output_rows)
        t=np.array([r['time_s'] for r in output_rows])/60
        axes[0].plot(t,[r['cpu_percent'] for r in output_rows],label=label,color=color,linewidth=.9)
        axes[1].plot(t,[r['rss_mib'] for r in output_rows],label=label,color=color,linewidth=.9)
        audits[name]=dict(source=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                          batches=len(groups),maximum_batch_span_s=max(r['batch_span_s'] for r in output_rows),
                          median_cpu_percent=float(np.median([r['cpu_percent'] for r in output_rows])),
                          median_rss_mib=float(np.median([r['rss_mib'] for r in output_rows])))
    for ax,title,ylabel in zip(axes,['全部试验进程组CPU','全部试验进程组RSS'],['%（100%=一核）','MiB（共享页可能重复）']):
        ax.set(title=title,xlabel='时间/min',ylabel=ylabel);ax.grid(alpha=.2);ax.legend()
    fig.suptitle('按实际采样批次聚合；避免把同一批进程拆到相邻5秒桶')
    fig.savefig(out/'resources_corrected.png',dpi=160);fig.savefig(out/'resources_corrected.pdf');plt.close(fig)
    (out/'resource_batch_audit.json').write_text(json.dumps(audits,indent=2)+'\n')
    report=(base/'REPORT.md').read_text()
    report=report.replace('](comparison.png)','](../'+base.name+'/comparison.png)')
    report=report.replace('](trajectories.png)','](../'+base.name+'/trajectories.png)')
    report=report.replace('](resources_comparison.png)','](resources_corrected.png)')
    for target in ['comparison.mp4','original/camera_h264.mp4','ht/camera_h264.mp4','original/late_camera.jpg','ht/late_camera.jpg']:
        report=report.replace(']('+target+')','](../'+base.name+'/'+target+')')
    note='''资源图复核说明：原封存报告按固定5秒边界求和，会把极少数跨界的同一采样批次拆开，形成CPU/RSS向下尖点。此复核按原始行的实际批次聚合（批内间隔小于1秒、批间约5秒），保留批次CSV和源SHA；没有平滑曲线、填补采样或修改运行数据。CPU/RSS数值是受记录进程组之和，共享页可能重复。下方资源图已换为修正图，其余比较数值/图/视频均引用原封存报告。

'''
    first,rest=report.split('\n',1)
    (out/'REPORT.md').write_text(first+'（资源图复核版）\n\n'+note+rest)
    (out/'source_review.json').write_text(json.dumps(dict(source_report=str(base/'REPORT.md'),
        source_report_sha256=hashlib.sha256((base/'REPORT.md').read_bytes()).hexdigest(),
        policy='Read-only source; published raw/results archives and their inventories unchanged.'),indent=2)+'\n')
    print(json.dumps(audits,indent=2))


if __name__=='__main__':
    main()
