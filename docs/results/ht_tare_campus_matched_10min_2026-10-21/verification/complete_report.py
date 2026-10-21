#!/usr/bin/env python3
"""Add the human interpretation after the campus replay has finished."""
import csv
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

ROOT = Path('/home/lzz/my test/HT_Explo-fixposition')
runtime = ROOT / '.git/campus-matched-runtime'
job = json.loads((runtime / 'job.json').read_text())
out = Path(job['archive'])
if 'CAMPUS_POSTPROCESSING_COMPLETE' not in (runtime / 'post.log').read_text():
    raise RuntimeError('Wait for the full replay/decode pipeline before final review')
metrics = json.loads((out / 'comparison_metrics.json').read_text())
curves = {}
gains = {}
for name in ('original', 'ht'):
    rows = list(csv.DictReader((out / name / 'current/observation_volume.csv').open()))
    t = [float(r['time_s']) for r in rows]
    v = [float(r['observed_free_volume_m3']) for r in rows]
    curves[name] = np.interp(np.arange(601), t, v)
    gains[name] = dict(last60_volume_m3=float(v[-1] - np.interp(540, t, v)),
                       per_minute_volume_m3=np.diff(np.interp(np.arange(0, 601, 60), t, v)).tolist())
delta = curves['ht'] - curves['original']
tail = int(np.flatnonzero(delta <= 0)[-1] + 1) if delta[-1] > 0 else None
o = metrics['original']; h = metrics['ht']
ratio = h['external']['observed_free_volume_m3'] / o['external']['observed_free_volume_m3'] - 1
verification = out / 'verification'
verification.mkdir(exist_ok=True)
for source in sorted((runtime / 'verification').iterdir()):
    if source.is_file():
        shutil.copy2(source, verification / source.name)
shutil.copy2(Path(__file__), verification / 'complete_report.py')
details = dict(volume_difference_m3=float(delta[-1]), volume_relative_difference=ratio,
               persistent_tail_advantage_start_s_on_1s_interpolated_curve=tail, gains=gains,
               scope='Single paired end-to-end trial; interpolation is for interpreting the curve, not new sensor observations.')
(verification / 'curve_interpretation.json').write_text(json.dumps(details, ensure_ascii=False, indent=2) + '\n')
issues = json.loads((verification / 'ht_acceleration_exceptions.json').read_text())
assert issues['excess_count'] == 1
x = issues['issues'][0]
intro = (f"本次Campus结果：HT最终近似观测自由体积多{ratio:.2%}（{delta[-1]:.0f}m³），"
         f"实际里程{h['summary']['distance_m']:.2f}m，原TARE为{o['summary']['distance_m']:.2f}m。"
         f"前9分钟总体原TARE领先；在按1秒插值的曲线上，HT从约{tail}秒起持续领先至600秒。"
         f"最后一分钟新增量分别为HT {gains['ht']['last60_volume_m3']:.1f}m³、TARE {gains['original']['last60_volume_m3']:.1f}m³。"
         "两组末状态均EXPLORING；本轮没有重现室内HT末段的长时间低收益，但不能由单次运行证明普遍优势。\n\n")
finding = ("## 仍存在的问题与核验\n\n"
           "- HT原地转向指令占12.57%，原TARE为0.96%；HT整个TARE规划周期P95为0.919s，原TARE为0.500s。该周期含探索决策等步骤，不能当成单独XYθ搜索耗时。\n"
           f"- HT在第{x['current']['receipt_t_s']:.3f}秒有一次常规角加速度审计超限："
           f"相邻指令间隔{x['header_dt_s']:.6f}s，角速度变化{x['dw']:.3f}rad/s，"
           f"差分为{x['yaw_accel_rps2']:.3f}rad/s²，高于设定1.2；原地转向中发生，不是显式全零急停例外。"
           "代码xytheta_follower.cpp用固定dt=0.05计算每步限幅；本次指令时间间隔短于50ms，这是直接可核对的不一致。"
           "这属于指令差分，不能据此宣称实际车体角加速度或测量抖动来源已证实。本轮按用户要求未修改控制代码，检查保持失败。\n"
           "- 原版localPlanner/pathFollower在完整测量结束后的SIGINT阶段抛出ROS context异常，关闭检查失败；HT未检出相同关闭异常。总体COMPLETED_WITH_ISSUES，完整计时不等于稳定性全项通过。\n"
           "- 两边各处理600帧源秒激光，无指标帧被跳过；两边实际速度上限通过。72项HT运行输入/二进制在测后与冻结哈希一致；原TARE六个关键决策函数体与适配基线一致。"
           "[核验记录与额外诊断](verification/README.md)。\n\n")
p = out / 'REPORT.md'
body = p.read_text()
if '## 仍存在的问题与核验' not in body:
    first, rest = body.split('\n\n', 1)
    body = first + '\n\n' + intro + rest
    body = body.replace('## 口径与限制\n', finding + '## 口径与限制\n', 1)
    body = body.replace('| 最后60秒里程/m |', f"| 最后60秒新增体积/m³ | {gains['original']['last60_volume_m3']:.3f} | {gains['ht']['last60_volume_m3']:.3f} |\n| 最后60秒里程/m |", 1)
    p.write_text(body)
(verification / 'README.md').write_text('''# 额外核验（不修改导航）

本目录记录2026-10-22的测后核验。采集时间和冻结版本保持frozen_job.json所记的2026-10-21。

- `tare_contract.json`：运行`python3 scripts/check_tare_waypoint_contract.py`，六函数体对照通过；参考b6760adb。
- `cleanup_timing_tests.log`：`python3 -m unittest discover -s presentations -p test_matched_tare_cleanup.py -v`，四项通过。
- `runtime_hashes_after_measurement.json`：逐个重算HT manifest.source_hashes的SHA256，72项一致。
- `curve_interpretation.json`：原始observation_volume.csv按相同规则计算每分钟及末60秒新增量；持续领先时刻使用1秒插值曲线，仅作读图辅助。
- `ht_acceleration_exceptions.json`：读取完整MCAP的/cmd_vel，按与motion_envelope_audit.json相同条件复算：0<相邻header间隔<0.3s，排除当前v=w=0，若|Δv|>0.5Δt+0.005或|Δω|>1.2Δt+0.005记超限。保留前后指令与同时间附近状态。
- `complete_report.py`：本次解读脚本快照；对已处理的同一job生成本目录和报告解读，运行前检查后处理完成标记。

原始MCAP在Release完整raw附件；逐组采集/运动/退出审计见上级original和ht目录。一次性后处理入口：先source /opt/ros/jazzy/setup.bash，再执行process_campus_comparison.py --state JOB；JOB格式见frozen_job.json，入口仅接受MEASUREMENTS_COMPLETE且结果目录尚不存在的状态。封存后不要覆盖原证据；复算时使用独立派生目录并按各单步脚本重算，不能直接重复运行一次性入口。RViz是实际窗口离线回放，不是在线延迟或无故障证据。
''')
files = {str(p.relative_to(out)): hashlib.file_digest(p.open('rb'), 'sha256').hexdigest()
         for p in sorted(out.rglob('*')) if p.is_file() and p.name != 'files_sha256.json'}
(out / 'files_sha256.json').write_text(json.dumps(files, ensure_ascii=False, indent=2) + '\n')
print('Reviewed', out)
