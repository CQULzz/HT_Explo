#!/usr/bin/env python3
"""Compare complete, same-scene600s iterations without overwriting evidence."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def read(path):
    return json.loads(path.read_text())


def datafile(folder, name):
    return folder/name if (folder/name).exists() else folder/'current'/name


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def load(spec):
    label, separator, raw = spec.partition('=')
    if not separator or not label:
        raise ValueError('Expected LABEL=FOLDER')
    folder = Path(raw).resolve()
    summary = read(folder/'summary.json')
    manifest = read(folder/'manifest.json')
    validation = read(folder/'suite_validation.json')
    if summary['duration_s'] != 600 or manifest['planned_duration_s'] != 600:
        raise ValueError('Not a complete600s iteration: '+str(folder))
    if not (folder/'COMPLETED.json').exists() or not all(validation['checks'].values()):
        raise ValueError('Recording validation failed: '+str(folder))
    metric = read(folder/'metric_definition.json')
    mission = read(folder/'mission_audit.json')
    motion_path = datafile(folder, 'timeseries.csv')
    volume_path = datafile(folder, 'observation_volume.csv')
    motion, volume = rows(motion_path), rows(volume_path)
    if not motion or not volume or float(motion[-1]['t_s']) < 599:
        raise ValueError('Incomplete motion/volume series')
    counts = mission['sampled_mission_counts']
    total = sum(counts.values())
    result = dict(label=label, folder=str(folder), scenario=manifest['scenario'],
                  git_head=manifest['git_head'], duration_s=summary['duration_s'],
                  speed_cap_mps=manifest['speed_cap_mps'],
                  measurement_start_pose_xyyaw=summary['start_pose_xyyaw'],
                  distance_m=summary['distance_m'],
                  observed_free_volume_m3=float(volume[-1]['observed_free_volume_m3']),
                  final_mission=mission['last_sampled_mission'],
                  completed_at_s=mission['first_completed_sample_s'],
                  blocked_sample_fraction=counts.get('BLOCKED', 0)/total if total else None,
                  runtime_p95_s=summary['planner_runtime_p95_s'],
                  source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in (motion_path, volume_path, folder/'manifest.json',
                                           folder/'metric_definition.json',folder/'suite_validation.json')})
    return result, motion, volume, metric, summary['start_pose_xyyaw']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='append', required=True, help='LABEL=FOLDER')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if len(args.run)<2:
        raise ValueError('Need at least two versions')
    runs = [load(spec) for spec in args.run]
    first = runs[0]
    for row in runs[1:]:
        if row[0]['scenario'] != first[0]['scenario'] or row[0]['speed_cap_mps'] != first[0]['speed_cap_mps']:
            raise ValueError('Scenario or speed cap mismatch')
        if row[3] != first[3]:
            raise ValueError('Metric definitions differ; recompute before comparing')
        if math.hypot(row[4][0]-first[4][0],row[4][1]-first[4][1])>.05 or abs(
                math.remainder(row[4][2]-first[4][2],2*math.pi))>.02:
            raise ValueError('Initial poses differ')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig, axes = plt.subplots(2,2,figsize=(14,9),layout='constrained')
    for result, motion, volume, _, _ in runs:
        label = result['label']
        line, = axes[0,0].plot([float(r['time_s'])/60 for r in volume],
                              [float(r['observed_free_volume_m3']) for r in volume],label=label)
        color = line.get_color()
        t = [float(r['t_s'])/60 for r in motion]
        axes[0,1].plot(t,[float(r['distance_m']) for r in motion],color=color,label=label)
        axes[1,0].plot(t,[float(r['odom_speed_mps']) for r in motion],color=color,label=label,alpha=.8,lw=.8)
        axes[1,1].plot([float(r['x_m']) for r in motion],
                       [float(r['y_m']) for r in motion],color=color,label=label)
        axes[1,1].scatter(float(motion[-1]['x_m']),float(motion[-1]['y_m']),color=color,marker='x')
    titles = [('累计观测自由体积（近似）','时间 / 分钟','m³'),
              ('实际累计里程','时间 / 分钟','m'),
              ('里程计平移速度（原地转向时也为零）','时间 / 分钟','m/s'),
              ('实际XY轨迹，叉号为终点','X / m','Y / m')]
    for axis, (title,xlabel,ylabel) in zip(axes.flat,titles):
        axis.set(title=title,xlabel=xlabel,ylabel=ylabel)
        axis.grid(alpha=.2);axis.legend(fontsize=9)
    for axis in (axes[0,0],axes[0,1],axes[1,0]):
        axis.set_xlim(0,10)
    axes[1,1].set_aspect('equal',adjustable='datalim')
    fig.suptitle('同一室内场景，各完整600秒；不同闭环轨迹的单次记录，不代表统计优劣' if first[0]['scenario']=='indoor'
                 else f'{first[0]["scenario"]}：各完整600秒的历史版本对比')
    fig.savefig(out/'comparison.png',dpi=170)
    fig.savefig(out/'comparison.pdf');plt.close(fig)
    results = [row[0] for row in runs]
    (out/'comparison.json').write_text(json.dumps(dict(runs=results,metric_definition=first[3],
        measurement_start_pose_tolerance=dict(position_m=.05,yaw_rad=.02)),ensure_ascii=False,indent=2)+'\n')
    columns = ['label','git_head','distance_m','observed_free_volume_m3','final_mission',
               'completed_at_s','blocked_sample_fraction','runtime_p95_s','folder']
    with (out/'comparison.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,extrasaction='ignore');writer.writeheader();writer.writerows(results)
    lines=['# 同场景版本10分钟对比','',
           '各组600秒；同场景原生起点、相同速度上限和体积统计定义。计时起点允许5cm/0.02rad差异，实际位姿保存在JSON中。不同闭环轨迹的单次试验，不能独立归因或证明普遍优劣。',
           '体积是0.5m自由体素并集近似，不是真值覆盖率。平移速度为零也可能是在原地转向。','',
           '| 版本 | 代码 | 里程(m) | 观测自由体积(m³) | 最终状态 | BLOCKED抽样占比 | 规划P95(s) |',
           '|---|---|---:|---:|---|---:|---:|']
    for r in results:
        lines.append(f'| {r["label"]} | `{r["git_head"][:7]}` | {r["distance_m"]:.2f} | {r["observed_free_volume_m3"]:.3f} | {r["final_mission"]} | {r["blocked_sample_fraction"]:.1%} | {r["runtime_p95_s"]:.3f} |')
    lines += ['', '![体积、里程、速度和轨迹对比](comparison.png)','',
              '原始目录、输入CSV和记录校验文件的哈希保存在[comparison.json](comparison.json)。',
              '视频、原始MCAP与地图快照在各运行目录；历史结果中的精选归档可能只含视频、CSV和末段快照。']
    for r in results:
        lines.append(f'\n- {r["label"]}：`{r["folder"]}`')
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(out)


if __name__=='__main__':
    main()
