from pathlib import Path
import shutil,json
root=Path('/home/lzz/ht_campus_repeat_1200s_20261118');run=root/'runs/explicit_labels_campus_repeat_1200s_01';repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');dest=repo/'validation/campus_repeat_1200s_20261118';local=Path('/mnt/d/HT-Campus-Repeat-1200s-20261118/results');dest.mkdir(exist_ok=False)
for n in ['data','logs','source','reference']:(dest/n).mkdir()
for n in ['RESULT.json','ANALYSIS.json','PHASES.json','COMMAND_AUDIT.json','RECORDING_VALIDATION.json','FREEZE.json','CLEANUP.json','COMMANDS.json','STOP_DIAGNOSIS.json','END_MOTION_CHECK.json','BACKTRACKING.json','backtracking_segments.csv','comparison.png','backtracking.png','end_motion.png','tare_planner_node.yaml','localPlanner.yaml','pathFollower.yaml','cupy_to_ht_bridge.yaml','vehicleSimulator.yaml']:shutil.copy2(run/n,dest/n)
for n in ['PLAN.json','BUDGET.json']:shutil.copy2(root/n,dest/n)
for n in ['metrics.csv','SUMMARY.json','START.json']:shutil.copy2(run/'observations'/n,dest/'data'/n)
for n in ['simulation.log','mapper.log','model.log','observer.log','bag.log']:shutil.copy2(run/n,dest/'logs'/n)
for n in ['CAMPUS_REFERENCE.json','REFERENCE_GROUND_PROXY.json','COVERAGE_ASSESSMENT.json','campus_reference_coverage.png']:shutil.copy2(root/'analysis'/n,dest/'reference'/n)
for n in ['run.py','env.sh','run_1200s.sh','simulation.launch.py','startup_collect.py','recording_qos.yaml']:shutil.copy2(root/n,dest/'source'/n)
for p in Path('/mnt/d/HT-Campus-Repeat-1200s-20261118').iterdir():
 if p.is_file() and p.suffix in ['.py','.sh']:shutil.copy2(p,dest/'source'/p.name)
shutil.copy2(Path('/mnt/d/HT-Campus-Repeat-1200s-20261118/PREVIOUS_STOP_MAP_CHECK.json'),dest/'PREVIOUS_STOP_MAP_CHECK.json')
(dest/'.gitattributes').write_text('*.log -text -whitespace\n*.yaml -text -whitespace\n*.csv -text -whitespace\n')
a=json.loads((run/'ANALYSIS.json').read_text());old=json.loads((repo/'validation/campus_1200s_20261118/ANALYSIS.json').read_text());bt=json.loads((run/'BACKTRACKING.json').read_text());cov=json.loads((root/'analysis/COVERAGE_ASSESSMENT.json').read_text());audit=json.loads((run/'COMMAND_AUDIT.json').read_text());v=json.loads((run/'RECORDING_VALIDATION.json').read_text());cl=json.loads((run/'CLEANUP.json').read_text());stop=json.loads((run/'STOP_DIAGNOSIS.json').read_text());ph=json.loads((run/'PHASES.json').read_text());res=json.loads((run/'RESULT.json').read_text());bt0=bt['previous'];bt1=bt['repeat']
phase_table='\n'.join(f"| {p['begin_s']//60}—{p['end_s']//60}分钟 | {p['distance_m']:.3f} | {p['sampled_observation_volume_added_m3']:.3f} |" for p in ph['phases'])
report=f'''# campus 20分钟同配置复跑与回头路诊断（2026-11-18）

用户要求重新试一次，并关注回头路。当前导航仍为11dd46d5561a0b426ebc800e192d9f42d0d8b00d；资料基线e46bf8a。原305冻结文件启动前SHA一致，五节点实际参数比较见ANALYSIS.json。沿用Helios32 crop_box、URDF包络、固定0.65m explicit_labels_v1和稳健只读采集器；无导航/安全门限改动。

## 本轮与上轮

| 项目 | 上轮 | 本轮 |
|---|---:|---:|
| 完整采集墙钟秒 | 1200.000515 | {a['duration_s']:.6f} |
| 累计里程m | {old['distance_m']:.3f} | {a['distance_m']:.3f} |
| 末30秒里程m | 0 | {a['last30_distance_m']:.3f} |
| finish | true | {str(a['finish']).lower()} |
| 首次完成信号秒 | {old['finish_signal_elapsed_s']:.3f} | {a['finish_signal_elapsed_s']} |
| 最后非零速度采样秒 | {old['last_nonzero_sample_elapsed_s']:.3f} | {a['last_nonzero_sample_elapsed_s']} |
| 最终base距起点m | {old['final_base_distance_to_initial_m']:.3f} | {a['final_base_distance_to_initial_m']:.3f} |
| 空间重复路线比例 | {bt0['overall']['route_revisit_fraction']:.2%} | {bt1['overall']['route_revisit_fraction']:.2%} |

本轮域219、Gazebo11559、Xvfb:106，输入就绪后完整采1200秒；仿真推进{a.get('sim_time_advanced_s')}秒、RTF {a.get('sim_real_time_factor')}，不混算仿真和墙钟。预检无其他Gazebo，上轮存在并行AEDE负载；没有共同显式随机种子，因此不把不同路线/结果归因于代码改善。

## 回头路的量化口径

对扣除雷达0.1725m偏移后的base XY轨迹按距离加权：一段中点距至少30秒以前的轨迹采样点≤1m，记为空间重复。倒车命令另算，不将倒车直接等同走旧路。必要转场、返航，以及原地换视角补观测都可能重复，不能把此比例全部称作无效运动。

本轮宣布完成前重复比例：{bt1['before_finish']['route_revisit_fraction']}；完成后重复比例：{bt1['after_finish']['route_revisit_fraction']}，详细距离/逐段时间见BACKTRACKING.json和backtracking_segments.csv。

| 时段 | 里程增量m | 采样观测体积代理增量m³ |
|---|---:|---:|
{phase_table}

![空间重复路段](backtracking.png)

## 停车及采集证据

末30秒命令原因：{json.dumps(stop['last30s_command_reasons'],ensure_ascii=False)}。连续上下文拒绝开始秒={stop['trailing_context_invalid_begin_s']}，次数={stop['trailing_context_invalid_audits']}。实际低平移速度区间（含原地转向分类）见PHASES.json，末120秒真实运动见END_MOTION_CHECK.json/end_motion.png，没有视频尾部补帧参与判断。异常JSON消息数={stop['malformed_diagnostic_count']}，原文保留。

独立原图审计passed={audit['passed']}，{json.dumps(audit['counts'],ensure_ascii=False)}。完整采集={res['collection_complete']}，前后冻结一致={res['freeze_unchanged']}，{v['messages']}条消息的MCAP可用CRC/metadata检查与{v['frozen_files']}条冻结归档核对通过。SIGINT干净退出={cl['clean_child_exit']}，本轮相关残留={len(cl['relevant_processes_remaining'])}；错误原文保留。门禁审计不代表模型真值准确性或完整探索验收。

## 上轮为什么停住：已核对原图

上轮最终base点的ht_measured_valid=1、ht_observation_valid=1、ht_obstacle=0，但ht_valid=0且8方向发布值均非有限。向目标0.5m处有有效上下文，但当前点首先不通过门禁。神经上下文要求约2.09m的51×51窗口满足≥90%邻近已知支撑且无未决不确定项，不能把有单点地面观测当作整个神经窗口可用。具体哪个原始高程/方差样本首先使窗口失效，尚未重建；不将此地图检查冒称完整根因修复。原图数值见PREVIOUS_STOP_MAP_CHECK.json。

## 独立场景对照

相同官方campus参考，1Hz实测端点、15m范围、0.5m体素、0.75m匹配容差。参考表面匹配{cov['reference_surface_matched_fraction']:.3%}；保守连通地形估计匹配{cov['ground_proxy_observed_fraction']:.3%}，未匹配且距轨迹>20m格数{cov['unobserved_ground_proxy_cells_over20m_from_recorded_route']}。这些不是可达地面真值覆盖率；完整模型包含不可访问表面，地形估计也可能漏窄道，不能据软件零计数或代理比例宣布全campus完成。

![整个campus参考与实际观测](reference/campus_reference_coverage.png)

## 保存与停止

完整原始数据：`{run}`，Windows精简：D:/HT-Campus-Repeat-1200s-20261118/results。新账本已关闭，旧账本未重置，不自动增加候选/实验。仅推送精简证据到fix/ht-execution-20261113，不新增Release/上传原始MCAP或视频；未完整远端备份数据不清理，不部署实车。
'''
(dest/'REPORT_zh.md').write_text(report);shutil.copytree(dest,local,dirs_exist_ok=True);print(report)
