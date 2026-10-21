"""Read completed captures, audit commands, compare historical curves and report facts."""
from pathlib import Path
import sys
import json
import csv
import re
import hashlib
import argparse
import shutil
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'presentations'))
from finalize_matched_tare_comparison import motion_audit


def read(path): return json.loads(path.read_text())
def write(path, data): path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n')
def rows(path): return list(csv.DictReader(path.open()))
def datafile(root, name): return root/name if (root/name).exists() else root/'current'/name
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def assess(suite, out):
    out.mkdir(parents=True, exist_ok=True)
    state = read(suite/'suite.json'); analyses = {}; provenance = {}
    plt.rcParams.update({'font.family': 'Noto Sans CJK JP', 'axes.unicode_minus': False})
    historical = {'indoor': ROOT/'docs/results/ht_tare_matched_10min_2026-10-21',
                  'campus': ROOT/'docs/results/ht_tare_campus_matched_10min_2026-10-21'}
    lines = ['# 仿真复测结果：室内与校园各600秒', '',
             '**本轮测试结果须与下方异常一起阅读；完整录制通过不等于探索任务没有问题。**', '',
             f'冻结提交：`{state["git_head"]}`；算法基线为`develop@8b10207`。实车分支和外参未参与本轮。',
             '每场独立重启，同一版本、原生起点，前进0.5m/s、倒车0.25m/s、角速度0.8rad/s；测量期间未修改算法和参数。', '',
             '| 场景 | 实际时长/s | 实际里程/m | 近似观测自由体积/m³ | 触发返航/s | 到家完成/s | 地图年龄P95/s |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for run in state['runs']:
        scene = run['scenario']; folder = suite/scene
        summary = read(folder/'summary.json'); audit = read(folder/'endurance_audit.json')
        mission = read(folder/'mission_audit.json'); origin = read(folder/'current/measurement_started.json')['wall_time']
        motion_path = folder/'motion_envelope_audit.json'
        motion = read(motion_path) if motion_path.exists() else motion_audit(folder)
        write(out/scene/'motion_envelope_audit.json', motion)
        shutil.copytree(folder/'current/effective_parameters', out/scene/'effective_parameters', dirs_exist_ok=True)
        log = (folder/'current/tare.log').read_text(errors='replace')
        events = []
        for line in log.splitlines():
            m = re.search(r'\[(\d+\.\d+)\].*TARE_COMPLETION global_return=(\d) local_complete=(\d) global_order_nodes=(\d+) local_route_nodes=(\d+) uncovered=(\d+) frontier=(\d+)', line)
            if m:
                events.append(dict(time_s=float(m[1])-origin, global_return=int(m[2]), local_complete=int(m[3]),
                                   global_order_nodes=int(m[4]), local_route_nodes=int(m[5]), uncovered=int(m[6]), frontier=int(m[7]), log=line))
        search = re.findall(r'HT_WAYPOINT_SEARCH.*termination=(\w+).*expanded=(\d+) direct=(\d+)', log)
        from collections import Counter
        d = dict(duration_s=summary['duration_s'], distance_m=summary['distance_m'],
                 volume_m3=audit['external_metrics']['observed_free_volume_m3'],
                 first_return_trigger_s=mission['first_exploration_finished_sample_s'],
                 first_completed_s=mission['first_completed_sample_s'], final_mission=mission['last_sampled_mission'],
                 map_age_p95_s=audit['sampled_map_age_s']['p95'], map_age_max_s=audit['sampled_map_age_s']['max'],
                 map_age_over3s_samples=audit['map_age_over3s_samples'],
                 longest_zero_command_sampled_s=audit['longest_fully_zero_sampled_intervals'][0]['duration_s'] if audit['longest_fully_zero_sampled_intervals'] else 0,
                 command_envelope=motion, completion_events=events,
                 search_termination_counts=dict(Counter(s[0] for s in search)),
                 search_attempts=len(search), direct_connection_successes=sum(s[0]=='REACHED' and s[2]=='1' for s in search),
                 capture_checks=read(folder/'suite_validation.json')['checks'],
                 interpretation='Completion is an internal decision, not proof of full ground-truth coverage. This run alone cannot isolate a source-level cause.')
        analyses[scene] = d
        def fmt(v): return '未触发' if v is None else f'{v:.2f}'
        lines.append(f'| {scene} | {d["duration_s"]:.0f} | {d["distance_m"]:.2f} | {d["volume_m3"]:.3f} | {fmt(d["first_return_trigger_s"])} | {fmt(d["first_completed_s"])} | {d["map_age_p95_s"]:.3f} |')

        fig, axes = plt.subplots(2, 3, figsize=(15, 8), layout='constrained')
        cases = [('历史原TARE（10-21）', historical[scene]/'original', '#718196'),
                 ('历史HT（10-21，07c1abd）', historical[scene]/'ht', '#d28a22'),
                 ('本轮HT（8b10207）', folder, '#137eac')]
        comparison = []
        for label, case, color in cases:
            mfile, vfile = datafile(case, 'timeseries.csv'), datafile(case, 'observation_volume.csv')
            mm, vv = rows(mfile), rows(vfile)
            t = np.array([float(r['t_s']) for r in mm]); dist = np.array([float(r['distance_m']) for r in mm])
            vt = np.array([float(r['time_s']) for r in vv]); vol = np.array([float(r['observed_free_volume_m3']) for r in vv])
            definition_file = case/'metric_definition.json'
            shared_metric_evidence = None
            if not definition_file.exists() and case.name == 'original':
                # Historical paired exports kept the shared metric definition
                # under HT only. Require the original's own recorded selection
                # and the paired processor; do not invent a missing file.
                definition_file = case.parent/'ht/metric_definition.json'
                processor = case.parent/'finalize_matched_tare_comparison.py'
                external_file = datafile(case, 'external_metrics.json')
                assert read(external_file)['scan_selection'] == 'source_second'
                assert "common.evaluate(folder,'current',600,scan_selection='source_second')" in processor.read_text()
                shared_metric_evidence = {str(p):sha(p) for p in [processor, external_file]}
            definition = read(definition_file)
            for key, expected in [('voxel_size_m', .5), ('ray_sample_step_m', .25), ('max_range_m', 15), ('endpoint_exclusion_m', .25)]:
                assert definition[key] == expected, (case, key)
            axes[0,0].plot(vt/60, vol, label=label, color=color)
            axes[0,1].plot(t/60, dist, label=label, color=color)
            edges = np.arange(0, 601, 30)
            axes[0,2].plot(edges[1:]/60, np.diff(np.interp(edges, vt, vol)), label=label, color=color)
            axes[1,0].plot([float(r['x_m']) for r in mm], [float(r['y_m']) for r in mm], label=label, color=color)
            comparison.append(dict(label=label, folder=str(case), distance_m=float(dist[-1]), volume_m3=float(vol[-1]),
                                   start_pose=read(case/'summary.json')['start_pose_xyyaw'],
                                   metric_definition_file=str(definition_file), shared_metric_evidence=shared_metric_evidence,
                                   inputs_sha256={str(p):sha(p) for p in [mfile, vfile, definition_file]}))
        hh = rows(folder/'health.csv'); hh = [r for r in hh if origin<=float(r['wall_time'])<origin+600]
        axes[1,1].plot([(float(r['wall_time'])-origin)/60 for r in hh], [float(r['map_source_age_s']) for r in hh], color='#137eac')
        axes[1,1].axhline(3, color='#c64747', ls='--', label='3秒超时线')
        mm = rows(folder/'current/timeseries.csv')
        axes[1,2].plot([float(r['t_s'])/60 for r in mm], [float(r['cmd_speed_mps']) for r in mm], label='v / m/s')
        axes[1,2].plot([float(r['t_s'])/60 for r in mm], [float(r['cmd_yaw_rate_rps']) for r in mm], label='ω / rad/s', alpha=.7)
        titles = [('近似累计观测自由体积','时间/min','m³'), ('实际里程','时间/min','m'),
                  ('每30秒新增近似自由体积','时间/min','m³'), ('同坐标实际轨迹','X/m','Y/m'),
                  ('本轮HT源地图年龄','时间/min','秒'), ('本轮实际发布指令','时间/min','v / ω')]
        for ax, (title, xlabel, ylabel) in zip(axes.flat, titles):
            ax.set(title=title, xlabel=xlabel, ylabel=ylabel); ax.grid(alpha=.2)
            ax.legend(fontsize=7)
        axes[1,0].set_aspect('equal', adjustable='datalim')
        fig.suptitle(f'{scene}：本轮与历史单次结果（历史TARE不是本轮新跑）\n相同场景/运动上限/体积口径；初始化、负载与随机性未统计消除，不作单模块因果结论')
        fig.savefig(out/f'{scene}_comparison.png', dpi=150); plt.close(fig)
        d['historical_reference'] = dict(
            ht_volume_m3=comparison[1]['volume_m3'], tare_volume_m3=comparison[0]['volume_m3'],
            ht_distance_m=comparison[1]['distance_m'], tare_distance_m=comparison[0]['distance_m'],
            volume_change_vs_historical_ht_percent=100*(d['volume_m3']/comparison[1]['volume_m3']-1))
        provenance[scene] = comparison
        write(out/scene/'planning_audit.json', d)
        write(out/scene/'completion_events.json', events)

    lines += ['', '## 同场景历史参照', '']
    for scene, d in analyses.items():
        h=d['historical_reference']
        lines += [f'- {scene}：历史HT近似体积 {h["ht_volume_m3"]:.3f}m³、里程 {h["ht_distance_m"]:.2f}m；本轮体积相对变化 {h["volume_change_vs_historical_ht_percent"]:+.2f}%。历史同运动上限原TARE为 {h["tare_volume_m3"]:.3f}m³。']
    lines += ['', '历史为单次参照，配置/代码变化和运行随机性同时存在，不能据此证明某个模块造成提升或退步。', '', '## 已发现的现象与可确认原因', '']
    for scene, d in analyses.items():
        def event(value): return '未触发' if value is None else f'约{value:.2f}秒'
        lines += [f'### {scene}', '',
                  f'内部任务末状态 `{d["final_mission"]}`。返航触发：{event(d["first_return_trigger_s"])}；完成驻留：{event(d["first_completed_s"])}。',
                  f'地图年龄超过3秒的采样 {d["map_age_over3s_samples"]} 次；最长采样全零指令区间 {d["longest_zero_command_sampled_s"]:.1f}s。停车必须结合任务状态判断。',
                  f'源时间戳指令审计：速度上限{"通过" if d["command_envelope"]["cap_passed"] else "未通过"}，常规加速度超限 {d["command_envelope"]["normal_acceleration_excess_count"]} 次。显式全零停止按原口径单列。',
                  f'XYθ搜索日志共 {d["search_attempts"]} 次：`{d["search_termination_counts"]}`；成功直接连接 {d["direct_connection_successes"]} 次。日志计数不等于TARE总规划周期。', '']
        matched = next((e for e in d['completion_events'] if e['global_return'] and e['local_complete']), None)
        if matched:
            lines += [f'返航判定的直接证据：t={matched["time_s"]:.3f}s 时 `global_return=1`、`local_complete=1`、全局顺序节点 {matched["global_order_nodes"]}，仍统计到未覆盖点 {matched["uncovered"]} / 前沿 {matched["frontier"]}。',
                      '代码中的完成条件据此设置exploration_finished并转入返航。局部完成表示没有被选出的、满足条件的收益视点，不要求未覆盖点/前沿计数归零。为什么剩余区域没有进入可选择视点或全局探索子空间，仍需覆盖/候选图的更细证据；不能仅据本次日志认定为某一阈值或某次输入修正造成。', '']
        if d['first_completed_s'] is not None and d['first_completed_s']<60:
            lines += ['**本轮很早结束且里程明显偏短，持续探索能力需要复核；不能把后续长时间零指令当成“稳定探索了10分钟”，也不能把内部COMPLETED当成环境已全部探索的真值。**', '']
        lines += [f'![{scene}多角度对比]({scene}_comparison.png)',
                  f'![{scene}末段八方向HT]({scene}/late_ht.png)',
                  f'[GitHub完整10分钟视频](https://github.com/CQULzz/HT_Explo/releases/download/ht-sim-20261022-input-contracts/ht-sim-20261022-input-contracts-{scene}.mp4)；本机文件为`{scene}/camera_h264.mp4`。', '']
    lines += ['## 测试与数据说明', '',
              '独立编译通过；99项Python桥接回归通过，6/6 CTest目标通过，其中GTest为79通过、4个缺历史录制样本的用例跳过；不把跳过算通过。',
              '初次Python收集缺CuPy测试依赖，随后两项回归缺sparse checkout样本；补齐对应环境与Git样本后重跑通过，未改断言。裸终端CuPy预检未带NVRTC库路径失败；使用实际runner相同CUDA环境后通过。',
              '保存原始MCAP、CSV、地图/模型输入、参数JSON、日志、源/二进制哈希和完整解码视频。录制范围为全部发布控制/HT/状态，激光按源秒采样和周期快照，不是全频原始传感器无损记录。',
              '体积口径：0.5m自由体素并集、0.25m射线步长、15m截断、回波前0.25m排除；属于近似观测量，不是真值覆盖率。历史曲线为已存在的单次运行；没有在本轮重新运行原TARE。',
              '任务/地图状态为1Hz采样，运动表为0.5秒采样；表中完成时间是首次采样时间，不能解释为毫秒级状态转换测量。',
              '本轮不更改导航算法以追求好看的测试结果。源码相同不保证无限时间、任意场景或实车无问题。',
              '[规划原理报告](../../planning/2026-10-22_planning_principles.pdf) · [逐项审计](analysis.json) · [历史输入与SHA256](comparison_provenance.json)', '']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    write(out/'analysis.json', dict(measured_commit=state['git_head'], algorithm_base='8b10207', runs=analyses,
                                  claim='Measured simulation behavior and offline checks only; not a universal safety/stability pass.'))
    write(out/'comparison_provenance.json', provenance)
    write(out/'files_sha256.json', {str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='files_sha256.json'})


if __name__ == '__main__':
    p=argparse.ArgumentParser();p.add_argument('--suite',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assess(a.suite,a.output)
