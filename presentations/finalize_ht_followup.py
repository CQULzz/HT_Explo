#!/usr/bin/env python3
"""Audit a completed fixed-code trial, compare the preceding run and export evidence."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def read_json(path):
    return json.loads(path.read_text())


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('folder', type=Path)
    parser.add_argument('--baseline', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw, out = args.folder.resolve(), args.output.resolve()
    if out.exists():
        raise RuntimeError(f'Refusing to overwrite {out}')
    audit = read_json(raw / 'endurance_audit.json')
    manifest = read_json(raw / 'manifest.json')
    video = read_json(raw / 'video_validation.json')
    shutdown = read_json(raw / 'current/shutdown.json')
    duration = manifest['planned_duration_s']
    checks = {
        'planned_timer_completed': (raw / 'COMPLETED.json').exists(),
        'enough_motion_samples': audit['summary']['sample_count'] >= duration * 1.7,
        'no_runtime_parent_failure': not audit['runtime_failures'],
        'video_full_decode_passed': video.get('full_decode_returncode') == 0,
        'no_forced_shutdown': not any(x.get('signal') in ('SIGTERM', 'SIGKILL') for x in shutdown),
        'no_remaining_live_descendants': shutdown[-1].get('remaining_live_descendants') == [],
    }
    source_checks = {name: Path(name).is_file() and hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
                     for name, digest in manifest['source_hashes'].items()}
    checks['all_frozen_sources_unchanged'] = all(source_checks.values())
    lifecycle_errors = {}
    forbidden = re.compile(r'terminate called|Traceback \(most recent call last\)|'
                           r'The following exception was never retrieved|exit code -(?:6|11)\b|'
                           r'context cannot be slept|context not valid')
    for log in (raw / 'current').glob('*.log'):
        matched = [line for line in log.read_text(errors='replace').splitlines() if forbidden.search(line)]
        if matched:
            lifecycle_errors[log.name] = matched
    checks['no_lifecycle_exception_in_logs'] = not lifecycle_errors
    validation = dict(checks=checks, source_hashes_unchanged=source_checks, video=video,
                      lifecycle_errors=lifecycle_errors, source_folder=str(raw),
                      note='These checks do not establish full coverage or absence of inefficient revisits.')
    pools=read_json(raw/'current/ht_cpu_threads.json')
    checks['blas_workers_bounded']=bool(pools['blas_pools']) and all(p['num_threads']==1 for p in pools['blas_pools'])
    checks['pytorch_workers_bounded']=pools['pytorch_threads']==2
    diagnostics=read_json(raw/'current/ht_diagnostics.json')
    stages={}
    for name in ('source_age_at_callback_s','fusion_and_quality_s','support_and_history_publish_s',
                 'network_inference_s','ht_serialize_publish_s','elapsed_s'):
        values=np.asarray([r[name] for r in diagnostics if name in r],float)
        if values.size:
            stages[name]=dict(count=int(values.size),median_s=float(np.median(values)),
                              p95_s=float(np.quantile(values,.95)),max_s=float(values.max()))
    write_json(raw/'ht_processing_stages.json',dict(thread_configuration=pools,stages=stages))
    write_json(raw / 'validation_checks.json', validation)
    if not all(checks.values()):
        raise RuntimeError('Trial needs investigation: ' + str({k:v for k,v in checks.items() if not v}))

    subprocess.run([sys.executable, str(Path(__file__).with_name('compare_ht_progress.py')),
                    '--baseline', str(args.baseline.resolve()), '--current', str(raw),
                    '--output', str(raw / 'comparison')], check=True)
    comparison = read_json(raw / 'comparison/comparison.json')
    motion = rows(raw / 'current/timeseries.csv')
    volume = rows(raw / 'current/observation_volume.csv')
    vt = np.asarray([float(r['time_s']) for r in volume])
    vv = np.asarray([float(r['observed_free_volume_m3']) for r in volume])
    mission = audit['mission_audit']
    completed = mission['first_completed_sample_s']
    active_end = completed if completed is not None else duration
    finished = mission['first_exploration_finished_sample_s']
    visited = set()
    last_time = last_distance = 0.0
    intervals = []
    def append_interval(t, distance):
        if t - last_time >= 10:
            intervals.append(dict(start_s=last_time, end_s=t, duration_s=t-last_time,
                                  distance_m=distance-last_distance,
                                  observed_free_volume_gain_m3=float(np.interp(t, vt, vv)-np.interp(last_time, vt, vv)),
                                  includes_return=finished is not None and t >= finished))
    active_rows = [r for r in motion if float(r['t_s']) <= active_end]
    for row in active_rows:
        t, distance = float(row['t_s']), float(row['distance_m'])
        cell = math.floor(float(row['x_m'])), math.floor(float(row['y_m']))
        if cell not in visited:
            append_interval(t, distance)
            visited.add(cell)
            last_time, last_distance = t, distance
    append_interval(float(active_rows[-1]['t_s']), float(active_rows[-1]['distance_m']))
    intervals.sort(key=lambda r:r['duration_s'], reverse=True)
    write_json(raw / 'revisit_intervals.json', dict(
        definition='Intervals without first entry into a new 1m trajectory cell; completed waiting excluded. This is not directly a coverage or loop detector; return transit is labelled.',
        intervals=intervals[:20]))

    import summarize_tare_ht_pair as common
    from rclpy.serialization import deserialize_message
    from geometry_msgs.msg import TwistStamped
    from std_msgs.msg import String
    origin = read_json(raw / 'current/measurement_started.json')['wall_time']
    phases = {name:dict(samples=0, fully_zero=0, stationary_turn=0, reverse=0,
                        max_abs_v=0.0, max_abs_w=0.0, follower_status={})
              for name in ('active', 'completed_wait')}
    reader = common.reader(raw / 'evidence_bag', ['/cmd_vel', '/ht_follower_status'])
    while reader.has_next():
        topic, data, ns = reader.read_next()
        t = ns / 1e9 - origin
        if not 0 <= t < duration:
            continue
        phase = phases['active' if t < active_end else 'completed_wait']
        if topic == '/cmd_vel':
            cmd = deserialize_message(data, TwistStamped).twist
            v, w = cmd.linear.x, cmd.angular.z
            phase['samples'] += 1
            phase['fully_zero'] += abs(v)<.01 and abs(w)<.05
            phase['stationary_turn'] += abs(v)<.01 and abs(w)>=.05
            phase['reverse'] += v<-.05
            phase['max_abs_v'] = max(phase['max_abs_v'], abs(v))
            phase['max_abs_w'] = max(phase['max_abs_w'], abs(w))
        else:
            status = deserialize_message(data, String).data
            phase['follower_status'][status] = phase['follower_status'].get(status, 0)+1
    for phase in phases.values():
        for key in ('fully_zero', 'stationary_turn', 'reverse'):
            phase[key+'_fraction'] = phase[key]/max(1,phase['samples'])
    write_json(raw / 'control_phase_audit.json', dict(active_end_s=active_end, phases=phases))
    checks['speed_and_turn_limits_respected'] = all(p['max_abs_v']<=.500001 and p['max_abs_w']<=.800001 for p in phases.values())
    checks['completed_wait_commands_zero'] = phases['completed_wait']['max_abs_v'] == 0 and phases['completed_wait']['max_abs_w'] == 0
    validation['full_rate_control_samples'] = sum(p['samples'] for p in phases.values())
    checks['enough_full_rate_controls'] = validation['full_rate_control_samples'] >= 19 * duration
    write_json(raw / 'validation_checks.json', validation)
    if not all(checks.values()):
        raise RuntimeError('Control validation failed: ' + str(checks))

    out.mkdir(parents=True)
    for name in ('manifest.json','validation_checks.json','mission_audit.json','target_selection_audit.json',
                 'input_delivery_audit.json','ten_minute_segments.csv','stability.png','performance.png',
                 'endurance_audit.json','camera_h264.mp4','revisit_intervals.json','control_phase_audit.json'):
        shutil.copy2(raw / name, out / name)
    shutil.copy2(raw/'ht_processing_stages.json',out/'ht_processing_stages.json')
    for source, name in [('current/timeseries.csv','timeseries.csv'),
                         ('current/observation_volume.csv','observation_volume.csv'),
                         ('current/cupy_processing_stats.json','cupy_processing_stats.json'),
                         ('current/shutdown.json','shutdown.json')]:
        shutil.copy2(raw / source, out / name)
    for path in (raw / 'comparison').iterdir():
        shutil.copy2(path, out / path.name)
    for path in out.glob('*.csv'):
        path.write_bytes(path.read_bytes().replace(b'\r\n',b'\n'))
    old, new = comparison['baseline'], comparison['current']
    age = audit['sampled_map_age_s']
    longest = intervals[0] if intervals else None
    def minute(value):
        return f'{value/60:.2f} 分钟' if value is not None else '未达到'
    lines = ['# 跨目标进展记忆与生命周期修复：60 分钟复测', '',
             f'Garage 独立启动，计划记录 {duration/60:.0f} 分钟，速度上限 0.5 m/s；不重启节点，不在运行中修改控制源码、配置或可执行文件。',
             f'控制版本 `{manifest["git_head"]}`，全部 {len(source_checks)} 项源码/配置/程序哈希在结束时复核一致。', '',
             '| 指标 | 上一轮 | 本轮 |', '|---|---:|---:|',
             f'| 实际里程(m) | {old["distance_m"]:.2f} | {new["distance_m"]:.2f} |',
             f'| 近似累计观测自由体积(m³) | {old["observed_free_volume_m3"]:.3f} | {new["observed_free_volume_m3"]:.3f} |',
             f'| 到访1米轨迹格 | {old["visited_1m_xy_cells"]} | {new["visited_1m_xy_cells"]} |', '',
             f'探索结束/开始返航：{minute(finished)}；确认到家停稳 COMPLETED：{minute(completed)}。最终距起始里程计位置 {mission["final_distance_to_measurement_start_m"]:.3f} m。',
             '任务完成不表示场景真值覆盖率100%；完成后的零速等待须与活动期停滞区分。', '',
             '![修改前后同场景对比](comparison.png)', '',
             f'1 Hz采样地图年龄：P95 {age["p95"]:.3f} s，最大 {age["max"]:.3f} s，超过3秒 {audit["map_age_over3s_samples"]} 个采样点；3秒安全停车限制未放宽。',
             f'活动期全量控制：完全零速 {phases["active"]["fully_zero_fraction"]:.1%}，原地转向 {phases["active"]["stationary_turn_fraction"]:.1%}，倒车 {phases["active"]["reverse_fraction"]:.1%}。',
             '本轮无记录到的被测父进程运行期意外退出，关停日志无上述生命周期异常、无强制终止、无残留活子进程。', '']
    lines += ['CPU线程核验：PyTorch 2线程，各BLAS库均为1线程；分段耗时见 [HT处理计时](ht_processing_stages.json)。', '']
    if longest:
        lines += [f'最长未进入新轨迹格区间：{longest["duration_s"]/60:.2f} 分钟，行驶 {longest["distance_m"]:.2f} m，新增近似观测 {longest["observed_free_volume_gain_m3"]:.3f} m³，是否涉及返航：{longest["includes_return"]}。',
                  '轨迹格不增长不必然意味着绕圈，需同时查看新增观测、运动与返航阶段。详见 revisit_intervals.json。', '']
    lines += ['![地图时效与资源](stability.png)', '', '![运行性能](performance.png)', '',
              '[完整视频：H.264，相机2fps](camera_h264.mp4) · [运行审计](endurance_audit.json) · [哈希、控制与视频核验](validation_checks.json) · [修改说明](../../fixes/2026-10-17_endurance_followup.md)', '',
              '限制：一次Garage仿真；近似观测使用0.5m体素、15m光线范围、每秒最多一帧，不是官方覆盖率。MCAP保存全量控制/状态/里程计、抽样点云及地图，不能用抽样帧数认定掉包。视频2fps不能用于判断控制流畅度。远端引导仍用距离启发，未引入完整全局可执行规划图。']
    (out / 'REPORT.md').write_text('\n'.join(lines)+'\n')
    shutil.copy2(out / 'REPORT.md', raw / 'FINAL_REPORT.md')
    write_json(raw / 'FINALIZED.json', dict(output=str(out), validation_passed=True,
                                           completed_s=completed, distance_m=new['distance_m'],
                                           observed_free_volume_m3=new['observed_free_volume_m3']))
    print(json.dumps(read_json(raw / 'FINALIZED.json'), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
