#!/usr/bin/env python3
"""Compare measured indoor trials while requiring unchanged control inputs."""
import argparse
import csv
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def read(path):return json.loads(path.read_text())


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('before',type=Path)
    ap.add_argument('after',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=False)
    before,after=args.before.resolve(),args.after.resolve()
    old,new=[read(p/'manifest.json')['source_hashes'] for p in [before,after]]
    changed=[key for key in old.keys()|new.keys() if old.get(key)!=new.get(key)]
    if len(changed)!=2 or not all(key.endswith('/indoor.yaml') for key in changed):
        raise RuntimeError('Unexpected control/input differences: '+str(changed))
    audits=[read(p/'endurance_audit.json') for p in [before,after]]
    for p,audit in zip([before,after],audits):
        video=read(p/'video_validation.json')
        if audit['duration_s']!=600 or video['full_decode_returncode']!=0 or not video['duration_matches']:
            raise RuntimeError('Incomplete recording: '+str(p))
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,axes=plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    labels=['原0.6m视点（50×50）','细化0.3m视点（100×100）']
    intervals=[]
    for path,label in zip([before,after],labels):
        with (path/'timeseries.csv').open() as f:motion=list(csv.DictReader(f))
        with (path/'observation_volume.csv').open() as f:volume=list(csv.DictReader(f))
        axes[0].plot([float(r['t_s'])/60 for r in motion],[float(r['distance_m']) for r in motion],label=label)
        axes[1].plot([float(r['time_s'])/60 for r in volume],[float(r['observed_free_volume_m3']) for r in volume],label=label)
        mt=[float(r['t_s']) for r in motion];distance=[float(r['distance_m']) for r in motion]
        vt=[float(r['time_s']) for r in volume];observed=[float(r['observed_free_volume_m3']) for r in volume]
        intervals.append(dict(start_s=360,end_s=450,
            distance_m=float(np.interp(450,mt,distance)-np.interp(360,mt,distance)),
            observed_free_volume_gain_m3=float(np.interp(450,vt,observed)-np.interp(360,vt,observed))))
    axes[0].set(ylabel='累计里程 / m',xlabel='时间 / 分钟')
    axes[1].set(ylabel='近似观测自由体积 / m³',xlabel='时间 / 分钟')
    for axis in axes:axis.legend();axis.grid(alpha=.2);axis.set_xlim(0,10)
    fig.suptitle('室内视点采样补测：30×30m范围相同，HT与运动控制输入相同，各测一次600秒')
    fig.savefig(out/'comparison.png',dpi=160);plt.close(fig)
    rows=[]
    extractors=[('实际里程(m)',lambda a:f'{a["summary"]["distance_m"]:.2f}'),
                ('近似观测自由体积(m³)',lambda a:f'{a["external_metrics"]["observed_free_volume_m3"]:.3f}'),
                ('全零指令占比',lambda a:f'{a["external_metrics"]["fully_stopped_fraction"]:.1%}'),
                ('最长全零指令(s)',lambda a:f'{a["external_metrics"]["longest_zero_command_s"]:.2f}'),
                ('倒车指令占比',lambda a:f'{a["external_metrics"]["reverse_command_fraction"]:.1%}'),
                ('规划耗时P95(s)',lambda a:f'{a["summary"]["planner_runtime_p95_s"]:.3f}'),
                ('HT年龄P95/最大(s)',lambda a:f'{a["sampled_map_age_s"]["p95"]:.2f} / {a["sampled_map_age_s"]["max"]:.2f}'),
                ('最后任务状态',lambda a:a['mission_audit']['last_sampled_mission'])]
    for label,extract in extractors:rows.append(f'| {label} | {extract(audits[0])} | {extract(audits[1])} |')
    report=['# 室内视点采样修改前后：各10分钟','',
            '仅把室内视点从50×50、0.6m改为100×100、0.3m，物理范围均为30×30m。两轮冻结输入只有源码与独立安装目录的indoor.yaml哈希不同，其他共同输入一致。HT栅格分辨率、阈值0.5、足迹0.6m、3秒时效、运动学搜索、跟踪器和速度上限均保持原配置。','',
            '原轮次在约3m处持续停车：0.6m候选网格漏掉窄HT支撑带中的可用目标。补测单独重启，原失败视频与地图均保留。','',
            '| 指标 | 原0.6m视点 | 细化0.3m视点 |','|---|---:|---:|',*rows,'',
            '![同环境修改前后曲线](comparison.png)','',
            f'补测仍有低收益回访：第6至7.5分钟行驶{intervals[1]["distance_m"]:.2f}m，近似新增观测仅{intervals[1]["observed_free_volume_gain_m3"]:.3f}m³。最长停车约40秒，不是连续顺畅探索。原组大多没有目标可搜，补测有活跃搜索，因此耗时差不能全部归因于视点数。','',
            '[原参数完整视频](../ht_multiscene_10min_2026-10-17/indoor/camera_h264.mp4) · [补测完整视频](../ht_indoor_viewpoint_10min_2026-10-17/indoor/camera_h264.mp4) · [实际参数读取](../ht_indoor_viewpoint_10min_2026-10-17/indoor/effective_parameters.json)','',
            '每种配置仅一次，不能据此证明普遍性能提升或所有问题解决。视点数为原来的四倍，表中保留计算代价与后段任务状态；行驶距离不能当作覆盖率，观测自由体积是抽样射线体素并集近似。隧道返航未知支撑问题属于另一项失败，未由本修改解决。']
    (out/'REPORT.md').write_text('\n'.join(report)+'\n')
    (out/'low_gain_interval.json').write_text(json.dumps(dict(method='Linear interpolation of archived CSV at 360s and 450s',before=intervals[0],after=intervals[1]),indent=2)+'\n')
    (out/'source_difference.json').write_text(json.dumps(dict(before=str(before),after=str(after),changed_inputs={key:dict(before=old.get(key),after=new.get(key)) for key in changed},unchanged_input_count=len(old.keys()&new.keys())-len(changed)),ensure_ascii=False,indent=2)+'\n')
    print(out)


if __name__=='__main__':main()
