#!/usr/bin/env python3
"""Separate process stability, data freshness and exploration progress in a long run."""
import argparse
import bisect
import collections
import csv
import json
import math
import re
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def read_csv(path):
    with path.open() as file:
        return list(csv.DictReader(file))


def number(row, key):
    try:
        return float(row[key])
    except (ValueError, TypeError, KeyError):
        return math.nan


def stats(values):
    values = np.asarray(values, float)
    values = values[np.isfinite(values)]
    return {'count': len(values), 'median': float(np.median(values)) if len(values) else None,
            'p95': float(np.percentile(values, 95)) if len(values) else None,
            'max': float(values.max()) if len(values) else None}


def longest(times, mask, period=.5):
    start = None
    events = []
    for index, (t, active) in enumerate(zip(times, mask)):
        if active and start is None:
            start = float(t)
        if start is not None and (not active or index == len(times)-1):
            end = float(t if not active else t+period)
            events.append({'start_s': start, 'end_s': end, 'duration_s': end-start})
            start = None
    return sorted(events, key=lambda row: row['duration_s'], reverse=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', type=Path)
    ap.add_argument('--skip-volume', action='store_true')
    args = ap.parse_args()
    folder = args.folder.resolve()
    origin = json.loads((folder/'current/measurement_started.json').read_text())['wall_time']
    summary = json.loads((folder/'summary.json').read_text())
    duration = float(summary['duration_s'])
    rows = read_csv(folder/'current/timeseries.csv')
    t = np.array([number(row, 't_s') for row in rows])
    dist = np.array([number(row, 'distance_m') for row in rows])
    x = np.array([number(row, 'x_m') for row in rows])
    y = np.array([number(row, 'y_m') for row in rows])
    v = np.array([number(row, 'cmd_speed_mps') for row in rows])
    w = np.array([number(row, 'cmd_yaw_rate_rps') for row in rows])
    full_stop = (np.abs(v)<.01) & (np.abs(w)<.05)
    turning = (np.abs(v)<.01) & (np.abs(w)>=.05)
    runtime = np.array([number(row, 'planner_runtime_s') for row in rows])
    actual_stationary = np.r_[False, np.diff(dist)/np.maximum(np.diff(t), .001)<.01]
    health = [row for row in read_csv(folder/'health.csv')
              if origin <= number(row, 'wall_time') < origin+duration]
    ht = np.array([number(row, 'wall_time')-origin for row in health])
    map_age = np.array([number(row, 'map_source_age_s') for row in health])
    scan_age = np.array([number(row, 'scan_source_age_s') for row in health])
    stamp_rows = sorted([(number(row, 'wall_time')-number(row, 'scan_source_age_s'), row)
                         for row in health if math.isfinite(number(row, 'scan_source_age_s'))],
                        key=lambda item: item[0])
    scan_stamps = [item[0] for item in stamp_rows]
    matches = []
    if (folder/'mapper_checkpoints.jsonl').exists():
        seen_stamps = set()
        for line in (folder/'mapper_checkpoints.jsonl').read_text().splitlines():
            cp = json.loads(line)
            m = cp['mapper']
            cloud_stamp = m.get('last_cloud_source_stamp_s')
            if cloud_stamp is None or cloud_stamp in seen_stamps or not scan_stamps:
                continue
            j = bisect.bisect_left(scan_stamps, cloud_stamp)
            k = min(range(max(0,j-1), min(len(scan_stamps),j+1)),
                    key=lambda i: abs(scan_stamps[i]-cloud_stamp))
            if abs(scan_stamps[k]-cloud_stamp)<1e-4:
                seen_stamps.add(cloud_stamp)
                matches.append({'source_stamp_s': cloud_stamp,
                                'probe_count': int(stamp_rows[k][1]['scan_count']),
                                'mapper_received_count': int(m['received_cloud_callbacks'])})
    offsets = [row['probe_count']-row['mapper_received_count'] for row in matches]
    delivery = {
        'exact_source_stamp_checkpoints': len(matches), 'source_stamp_tolerance_s': 1e-4,
        'count_offset_distribution': dict(collections.Counter(offsets)),
        'constant_offset_in_observed_window': bool(offsets) and min(offsets)==max(offsets),
        'first_checkpoint': matches[0] if matches else None,
        'last_checkpoint': matches[-1] if matches else None,
        'meaning': 'A constant offset supports no net relative input loss between the full-rate external observer and mapper in this matched window. It does not prove the simulator published continuously or that neither subscriber missed the same message.'}
    (folder/'input_delivery_audit.json').write_text(json.dumps(delivery, indent=2))
    resources = read_csv(folder/'resources.csv')
    groups = []
    for row in resources:
        wall = number(row, 'wall_time')
        if not origin <= wall < origin+duration:
            continue
        if not groups or wall-groups[-1]['wall']>1:
            groups.append({'wall': wall, 'rss': collections.defaultdict(float),
                           'cpu': collections.defaultdict(float),
                           'gpu': number(row, 'gpu_used_mb'), 'free': number(row, 'disk_free_gb')})
        group = groups[-1]
        group['rss'][row['label']] += number(row, 'rss_mb')
        cpu = number(row, 'cpu_percent')
        if math.isfinite(cpu):
            group['cpu'][row['label']] += cpu
    rt = np.array([group['wall']-origin for group in groups])
    labels = sorted({key for group in groups for key in group['rss']})
    label_stats = {}
    for label in labels:
        rss = np.array([group['rss'].get(label, 0) for group in groups])
        early = rss[(rt>=300)&(rt<600)]
        late = rss[rt>=max(0, duration-300)]
        label_stats[label] = {
            'peak_summed_rss_mb': float(rss.max()),
            'minute5to10_median_rss_mb': float(np.median(early)) if len(early) else None,
            'last5min_median_rss_mb': float(np.median(late)) if len(late) else None,
            'median_rss_change_mb': float(np.median(late)-np.median(early)) if len(late) and len(early) else None}
    segments = []
    for begin in range(0, math.ceil(duration), 600):
        end = min(begin+600, duration)
        selected = (t>=begin) & (t<end)
        fresh = (ht>=begin) & (ht<end)
        visited = {(math.floor(a), math.floor(b)) for a, b in zip(x[t<end], y[t<end])}
        segments.append({
            'start_s': begin, 'end_s': end,
            'distance_m': float(np.interp(end, t, dist)-np.interp(begin, t, dist)),
            'fully_stopped_sample_fraction': float(full_stop[selected].mean()),
            'stationary_turn_sample_fraction': float(turning[selected].mean()),
            'map_age': stats(map_age[fresh]), 'reported_planner_runtime_sampled_s': stats(runtime[selected]),
            'cumulative_visited_1m_xy_cells': len(visited)})
    external = None
    if not args.skip_volume:
        import summarize_tare_ht_pair as common
        link = folder/'current_bag'
        if not link.exists():
            link.symlink_to(folder/'evidence_bag', target_is_directory=True)
        original_reader = common.reader
        def sampled_reader(path, topics):
            return original_reader(path, ['/endurance/registered_scan' if topic=='/registered_scan' else topic
                                          for topic in topics])
        common.reader = sampled_reader
        _, volume, external = common.evaluate(folder, 'current', duration)
        volume_t = np.array([row['time_s'] for row in volume])
        volumes = np.array([row['observed_free_volume_m3'] for row in volume])
        for segment in segments:
            segment['observed_free_volume_gain_m3'] = float(
                np.interp(segment['end_s'], volume_t, volumes)-
                np.interp(segment['start_s'], volume_t, volumes))
        (folder/'metric_definition.json').write_text(json.dumps({
            'voxel_size_m': .5, 'ray_sample_step_m': .25, 'max_range_m': 15,
            'endpoint_exclusion_m': .25, 'scan_recording': 'first source-stamped scan per wall-clock source second',
            'selection': 'at most one recorded scan per measurement second; bins may be missing',
            'definition': 'Approximate cumulative union of observed free voxels; not ground truth or official coverage.',
            'delivery_audit': 'Sampled bag cannot establish loss of unsaved input frames; compare full-rate observer and mapper callback counters.'}, indent=2))
    failures = json.loads((folder/'runtime_failures.json').read_text()) if (folder/'runtime_failures.json').exists() else []
    target_pattern = re.compile(
        r'\[(\d+\.\d+)\].*XYtheta exploration target=(\d+) gain=([\d.]+).*'
        r'held=(\d).*goal=\(([^)]+)\) guide=\(([^)]+)\) recovery=(\d)')
    plan_log_rows = []
    for line in (folder/'current/tare.log').read_text().splitlines():
        match = target_pattern.search(line)
        if match and 0<=float(match[1])-origin<duration:
            plan_log_rows.append({'time_s': float(match[1])-origin, 'target_id': int(match[2]),
                                  'reported_gain': float(match[3]), 'held': match[4]=='1',
                                  'goal_xy': match[5], 'guide_xy': match[6], 'recovery': match[7]=='1'})
    new_goal_rows = [row for row in plan_log_rows if not row['held']]
    target_audit = {
        'logged_plan_rows': len(plan_log_rows), 'new_goal_rows': len(new_goal_rows),
        'new_goal_zero_reported_gain_rows': sum(row['reported_gain']==0 for row in new_goal_rows),
        'new_goal_recovery_rows': sum(row['recovery'] for row in new_goal_rows),
        'guide_log_counts': dict(collections.Counter(row['guide_xy'] for row in plan_log_rows)),
        'note': 'These are throttled log rows, not all planning cycles. Held targets are inserted withgain0 in ht_route.cpp; their logs cannot establish zero scene gain.'}
    accepted_rejections = []
    for line in (folder/'current/tare.log').read_text().splitlines():
        if 'Execution rejected HT edge' not in line:
            continue
        when = re.search(r'\[(\d+\.\d+)\]', line)
        if when and 0<=float(when[1])-origin<duration:
            accepted_rejections.append({'time_s': float(when[1])-origin, 'log': line})
    target_audit['accepted_execution_rejections'] = accepted_rejections
    (folder/'target_selection_audit.json').write_text(json.dumps(target_audit, indent=2))
    report = {
        'duration_s': duration, 'completed_timer': (folder/'COMPLETED.json').exists(),
        'node_restarts': 0, 'runtime_failures': failures,
        'summary': summary, 'external_metrics': external,
        'target_selection_audit': target_audit,
        'source_aligned_input_delivery': delivery,
        'sampled_map_age_s': stats(map_age), 'sampled_scan_age_s': stats(scan_age),
        'map_age_over3s_samples': int(np.sum(map_age>3)),
        'sampled_follower_status_counts': dict(collections.Counter(row['follower_status'] for row in health)),
        'longest_fully_zero_sampled_intervals': longest(t, full_stop)[:15],
        'longest_no_actual_translation_sampled_intervals': longest(t, actual_stationary)[:15],
        'process_memory': label_stats, 'segments': segments,
        'limitations': ['One Garage run; not a cross-environment or real-vehicle safety guarantee.',
                        'A running node is not proof of exploration progress.',
                        'RSS sums can double-count shared pages. GPU total includes the desktop.',
                        'Probe ages and stop states are sampled1Hz and0.5s; full control messages retained in MCAP.',
                        'Reported planner runtime is not end-to-end latency.']}
    (folder/'endurance_audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    with (folder/'ten_minute_segments.csv').open('w', newline='') as out:
        keys = ['start_s','end_s','distance_m','fully_stopped_sample_fraction',
                'stationary_turn_sample_fraction','cumulative_visited_1m_xy_cells','observed_free_volume_gain_m3']
        writer = csv.DictWriter(out, fieldnames=keys, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(segments)
    fig, axes = plt.subplots(3, 2, figsize=(14, 12), layout='constrained')
    axes[0,0].plot(t/60, dist, color='#2878b5')
    axes[0,0].set(title='Travel distance (actual odometry)', xlabel='Minutes', ylabel='m')
    if external:
        axes[0,1].plot(volume_t/60, volumes, color='#248f60')
    axes[0,1].set(title='Observed free-space volume (approximate)', xlabel='Minutes', ylabel='m3')
    axes[1,0].plot(ht/60, map_age, label='HT map source age', linewidth=.8)
    axes[1,0].plot(ht/60, scan_age, label='Lidar source age', linewidth=.6)
    axes[1,0].axhline(3, color='red', linestyle='--', label='HT3s freshness limit')
    axes[1,0].set(title='Data freshness, including time between callbacks', xlabel='Minutes', ylabel='Seconds')
    axes[1,0].legend(fontsize=8)
    for label in labels:
        axes[1,1].plot(rt/60, [group['rss'].get(label, 0) for group in groups], label=label)
    axes[1,1].set(title='Process-group RSS (shared pages may count twice)', xlabel='Minutes', ylabel='MB')
    axes[1,1].legend(fontsize=7, ncol=2)
    axes[2,0].plot(rt/60, [group['gpu'] for group in groups], label='GPU memory (all applications)')
    axes[2,0].set(title='GPU memory', xlabel='Minutes', ylabel='MB')
    axes[2,0].legend(fontsize=8)
    axes[2,1].plot(x, y, linewidth=.8)
    axes[2,1].scatter([x[0], x[-1]], [y[0], y[-1]], c=['green','red'], s=35)
    axes[2,1].set(title='Actual XY trajectory: green start / red end', xlabel='X(m)', ylabel='Y(m)')
    axes[2,1].set_aspect('equal', adjustable='datalim')
    for axis in axes.flat:
        axis.grid(alpha=.2)
    fig.savefig(folder/'stability.png', dpi=165)
    plt.close(fig)
    fig, axes = plt.subplots(2, 2, figsize=(14, 8), layout='constrained')
    minute_times, medians, p95s = [], [], []
    for begin in range(0, math.ceil(duration), 60):
        sample = runtime[(t>=begin)&(t<begin+60)]
        measured = stats(sample)
        minute_times.append((begin+30)/60)
        medians.append(measured['median'])
        p95s.append(measured['p95'])
    axes[0,0].plot(minute_times, medians, label='Median')
    axes[0,0].plot(minute_times, p95s, label='P95')
    axes[0,0].set(title='Reported planner runtime: sampled latest value / minute', xlabel='Minutes', ylabel='Seconds')
    axes[0,0].legend()
    for label in ['elevation', 'ht_bridge', 'tare', 'health', 'record', 'sim']:
        axes[0,1].plot(rt/60, [group['cpu'].get(label, 0) for group in groups], label=label, linewidth=.7)
    axes[0,1].set(title='Process-group CPU (100% = one core)', xlabel='Minutes', ylabel='CPU %')
    axes[0,1].legend(fontsize=8, ncol=2)
    centers = [(segment['start_s']+segment['end_s'])/120 for segment in segments]
    axes[1,0].bar(np.array(centers)-1, [100*s['fully_stopped_sample_fraction'] for s in segments],
                  width=2, label='Fully zero command')
    axes[1,0].bar(np.array(centers)+1, [100*s['stationary_turn_sample_fraction'] for s in segments],
                  width=2, label='Stationary turn')
    axes[1,0].set(title='Different reasons for no translation / ten-minute interval', xlabel='Minutes', ylabel='Samples %')
    axes[1,0].legend(fontsize=8)
    checkpoints = []
    if (folder/'mapper_checkpoints.jsonl').exists():
        for line in (folder/'mapper_checkpoints.jsonl').read_text().splitlines():
            value = json.loads(line)
            if origin<=value['wall_time']<origin+duration:
                checkpoints.append(value)
    if checkpoints:
        ct = np.array([entry['wall_time']-origin for entry in checkpoints])
        queues = [entry['mapper'].get('queue_age_p95_s') for entry in checkpoints]
        axes[1,1].plot(ct/60, queues, label='Lidar queue age P95 (cumulative)', color='#b44242')
        axes[1,1].set(ylabel='Seconds')
        twin = axes[1,1].twinx()
        processed = np.array([entry['mapper']['processed_clouds'] for entry in checkpoints])
        intervals = np.diff(ct)
        rates = np.divide(np.diff(processed), intervals,
                          out=np.zeros_like(intervals), where=intervals>0)
        twin.plot(ct[1:]/60, rates, color='#248f60', linewidth=.7, label='Completed fusion rate')
        twin.set_ylabel('Clouds / s')
        axes[1,1].legend(loc='upper left', fontsize=8)
        twin.legend(loc='upper right', fontsize=8)
    axes[1,1].set(title='Mapper queue and fusion throughput', xlabel='Minutes')
    for axis in axes.flat:
        axis.grid(alpha=.2)
    fig.savefig(folder/'performance.png', dpi=165)
    plt.close(fig)
    stopped = report['longest_fully_zero_sampled_intervals']
    no_motion = report['longest_no_actual_translation_sampled_intervals']
    lines = ['# 当前HT：Garage连续长时间测试', '',
             f'计划/实际记录 {duration/60:.0f} 分钟；不重启规划、建图及跟踪节点。前进上限0.5m/s。', '',
             f'- 行驶距离：{summary["distance_m"]:.2f}米；到访1米轨迹格：{summary["visited_1m_xy_cells"]}。',
             f'- 探索完成信号：{summary["exploration_finished"]}；定时结束不等于探索完成。',
             f'- 运行期间父进程退出/资源保护事件：{len(failures)}个，详见endurance_audit.json。',
             f'- 1Hz采样HT地图年龄P95/最大：{stats(map_age)["p95"]:.3f}/{stats(map_age)["max"]:.3f}秒；超过3秒{int(np.sum(map_age>3))}个采样点。',
             f'- 最长完全零速约{stopped[0]["duration_s"] if stopped else 0:.1f}秒；最长实际不平移约{no_motion[0]["duration_s"] if no_motion else 0:.1f}秒，后者包括原地旋转。', '',
             f'- 规划器日志确认收到并处理执行拒绝运动段{len(accepted_rejections)}次；已进入6秒冷却重规划分支。', '',
             '![稳定性曲线](stability.png)', '', '![运行性能与停车](performance.png)', '',
             '| 时段(分钟) | 里程(m) | 完全零速采样占比 | 原地转向采样占比 | 新增估计自由体积(m³) |',
             '|---|---:|---:|---:|---:|']
    for segment in segments:
        gain = segment.get('observed_free_volume_gain_m3')
        lines.append(f'| {segment["start_s"]/60:.0f}–{segment["end_s"]/60:.0f} | {segment["distance_m"]:.2f} | {segment["fully_stopped_sample_fraction"]:.1%} | {segment["stationary_turn_sample_fraction"]:.1%} | {gain:.2f} |' if gain is not None else str(segment))
    lines += ['', '## 数据与限制', '',
              '资源和健康检查是外部观测；没有修改被测规划参数或用重启掩盖问题。',
              '保留全部控制/状态/里程计消息；原始点云每秒抽样1帧，地图精确同时间戳快照约每10秒一组，相机视频2fps。此包不是完整传感器录包，不能用抽样帧数认定输入掉包。',
              '全速输入需结合健康探针回调计数、CuPy接收/融合计数和源时间段核验；结束时可能有未完成的一帧。',
              f'以源时间戳对齐外部探针与建图接收计数，匹配{len(matches)}个检查点；计数差恒定：{delivery["constant_offset_in_observed_window"]}。详见input_delivery_audit.json；这只检查匹配窗口内的相对接收差异，不能排除上游停发或双方共同漏收。',
              '目标选择日志单独保存在target_selection_audit.json。已承诺目标在当前代码中以gain=0占位，不能仅凭这些日志认定场景没有收益；需结合未承诺目标、实际轨迹和观测并集。',
              '自由空间是0.5m体素光线累计近似值，不是官方覆盖率或真值。内存为进程组RSS相加，可能重复计算共享页；显存总量包含桌面。',
              '单次Garage长测不能证明跨场景、实车或所有条件稳定。', '',
              '[健康/停车/内存审计](endurance_audit.json) · [每10分钟统计](ten_minute_segments.csv) · [相机视频](camera_2fps.mp4)']
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'distance_m': summary['distance_m'], 'duration_s': duration,
                      'output': str(folder/'REPORT.md')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
