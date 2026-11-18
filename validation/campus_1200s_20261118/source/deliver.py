from pathlib import Path
import json,shutil,csv,hashlib
root=Path('/home/lzz/ht_campus_1200s_20261118');run=root/'runs/explicit_labels_campus_1200s_03';repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');dest=repo/'validation/campus_1200s_20261118';local=Path('/mnt/d/HT-Campus-1200s-20261118/results');dest.mkdir(exist_ok=False)
for n in ['data','logs','source','failed_start_01','interrupted_02','reference']: (dest/n).mkdir()
for n in ['RESULT.json','ANALYSIS.json','PHASES.json','COMMAND_AUDIT.json','RECORDING_VALIDATION.json','CLEANUP.json','FREEZE.json','COMMANDS.json','tare_planner_node.yaml','localPlanner.yaml','pathFollower.yaml','cupy_to_ht_bridge.yaml','vehicleSimulator.yaml','comparison.png']:shutil.copy2(run/n,dest/n)
for n in ['PLAN.json','BUDGET.json']:shutil.copy2(root/n,dest/n)
for n in ['metrics.csv','SUMMARY.json','START.json']:shutil.copy2(run/'observations'/n,dest/'data'/n)
for n in ['simulation.log','model.log','mapper.log','observer.log','bag.log']:shutil.copy2(run/n,dest/'logs'/n)
for n in ['CAMPUS_REFERENCE.json','REFERENCE_GROUND_PROXY.json','COVERAGE_ASSESSMENT.json','campus_reference_coverage.png']:shutil.copy2(root/'analysis'/n,dest/'reference'/n)
for n in ['run.py','simulation.launch.py','run_1200s.sh','env.sh','recording_qos.yaml']:shutil.copy2(root/n,dest/'source'/n)
for n in ['prepare.py','retry_setup.py','prepare_reference.py','prepare_ground_proxy.py','postprocess_long.py','assess_coverage.py','deliver.py','postprocess.sh','audit.sh','coverage.sh']:shutil.copy2(Path('/mnt/d/HT-Campus-1200s-20261118')/n,dest/'source'/n)
failed=root/'runs/explicit_labels_campus_1200s_01'
for n in ['RESULT.json','simulation.log','observer.log','FREEZE.json','COMMANDS.json']:shutil.copy2(failed/n,dest/'failed_start_01'/n)
(dest/'.gitattributes').write_text('*.log -text -whitespace\n*.yaml -text -whitespace\ndata/*.csv -text -whitespace\n')
interrupted=root/'runs/explicit_labels_campus_1200s_02'
for n in ['RESULT.json','simulation.log','observer.log','FREEZE.json','MALFORMED_DIAGNOSTICS.json']:
 shutil.copy2(interrupted/n,dest/'interrupted_02'/n)
for n in ['metrics.csv','SUMMARY.json','START.json']:shutil.copy2(interrupted/'observations'/n,dest/'interrupted_02'/n)
for n in ['COVERAGE_ASSESSMENT.json','campus_reference_coverage.png']:shutil.copy2(root/'analysis_interrupted02'/n,dest/'interrupted_02'/n)
shutil.copy2(root/'setup/COLLECTOR_FIX_TEST.json',dest/'COLLECTOR_FIX_TEST.json')
shutil.copy2(root/'startup_collect.py',dest/'source/startup_collect.py')
a=json.loads((run/'ANALYSIS.json').read_text());ph=json.loads((run/'PHASES.json').read_text());v=json.loads((run/'RECORDING_VALIDATION.json').read_text());audit=json.loads((run/'COMMAND_AUDIT.json').read_text());cov=json.loads((root/'analysis/COVERAGE_ASSESSMENT.json').read_text());cleanup=json.loads((run/'CLEANUP.json').read_text());res=json.loads((run/'RESULT.json').read_text())
phase_table='\n'.join(f"| {int(p['begin_s'])//60}—{int(p['end_s'])//60}分钟 | {p['distance_m']:.3f} | {p['sampled_observation_volume_added_m3']:.3f} |" for p in ph['phases'])
conclusion='采集结束时软件仍未完成探索，不能判为campus完整探索通过。' if not a['finish'] else '软件发出完成信号，但必须结合独立场景对照核验，不以该信号或零计数判定完整覆盖。'
report=f'''# campus 20分钟探索实验（2026-11-18）

用户要求一次20min长时间探索，核验当前配置能否完整探索campus。{conclusion}

## 实际设置

实际导航代码11dd46d5561a0b426ebc800e192d9f42d0d8b00d；资料基线369d2dd。保持TARE双分辨率、HT八方向门禁、URDF包络、Helios标称32×1800/仿真10Hz、crop_box及0.65m explicit_labels_v1先验，启动前原305个冻结文件SHA一致。域221、Gazebo11549、Xvfb:105。输入就绪后采集1200秒墙钟，仿真推进另计。

首轮雷达实体spawn排队后超时，输入尚未就绪即中止，失败完整保留。仅将实体创建延迟60/62/64秒改为120/122/124秒、载体90秒改为150秒后使用唯一基础设施重试。第二轮在约784秒出现goal_x/goal_y=-nan诊断，observer解析非法JSON后中断，未完成20分钟，原文保留。仅追加一次观察器容错重试：原文记录解析错误后继续，3项检查通过，不改变导航策略、模型、速度或门禁。代理原自定2次上限因只读采集器故障扩为3次，原attempts不重置，第三轮为最终一次。运行时另一组独立AEDE基准仿真并行，未中断或改动；其CPU/GPU负载是比较混杂因素。未建立同一显式随机种子。

## 结果

- 实际采集{a['duration_s']:.6f}秒墙钟，完整采集={res['collection_complete']}，里程{a['distance_m']:.6f}米，末30秒{a['last30_distance_m']:.6f}米。
- finish={a['finish']}，首次完成信号秒={a['finish_signal_elapsed_s']}，最后非零速度采样秒={a['last_nonzero_sample_elapsed_s']}。
- 仿真推进{a.get('sim_time_advanced_s')}秒，实时因子{a.get('sim_real_time_factor')}；不与1200秒墙钟混算。
- 扫描/HT观察器接收频率{a['wall_rates']['scans']:.4f}/{a['wall_rates']['ht_maps']:.4f}Hz；抽样图龄P95 {a['sampled_ht_age_s']['p95']:.6f}秒，>1秒比例{a['fraction_sampled_age_over_1s']:.3%}。重打时间戳不是物理端到端延迟。
- 独立原图命令审计passed={audit['passed']}，计数{json.dumps(audit['counts'],ensure_ascii=False)}。缺图不能用邻帧替代。
- 全部MCAP可用CRC/metadata核对通过，{v['messages']}条消息、{len(v['files'])}段；{v['frozen_files']}个归档条目与冻结一致，测试前后冻结一致={res['freeze_unchanged']}。
- SIGINT子进程干净退出={cleanup['clean_child_exit']}，本轮相关残留={len(cleanup['relevant_processes_remaining'])}；既有清理缺陷原文保留。

| 时段 | 实际里程增量m | 采样观测体积代理增量m³ |
|---|---:|---:|
{phase_table}

实际base位置低速持续至少10秒的区间（含原地转向分类）：

```json
{json.dumps(ph['low_translation_intervals_at_least_10s'],ensure_ascii=False,indent=2)}
```

## 独立场景对照与完整性判据

官方campus参考点云3117380点，空间约336×311m。将本次实际配准扫描按1Hz、距精确配对雷达位姿15m内取端点，0.5m体素、0.75m最近观测体素中心容差，与参考比较；没有补造未知区域。参考表面匹配比例{cov['reference_surface_matched_fraction']:.3%}。另以参考点云最低地表、0.2—1.0m障碍带、3×3足迹邻域和每0.5m邻格≤0.2m高度差生成保守连通地形估计，匹配比例{cov['ground_proxy_observed_fraction']:.3%}；其中未匹配且距实际路线20m以上的格数{cov['unobserved_ground_proxy_cells_over20m_from_recorded_route']}。

以上两项都是诊断代理，不是真值可达地面覆盖率：完整模型含屋顶/建筑等不可通行结构，保守点云地形估计又会漏掉窄道，不能将未匹配点一律视为可达未探索，也不能把代理比例高直接视为全campus通过。必须结合剩余区域位置、实际路线和任务状态判读。上次完成后的零计数包含停止更新后的零初始化，不能当作实测全图覆盖完成。新增里程不等同新增探索。

![整张campus参考与实际观测](reference/campus_reference_coverage.png)

![轨迹与进度](comparison.png)

## 保存与停止

本轮实际数据：`{run}`；失败首轮在同root的runs/explicit_labels_campus_1200s_01；中断的第二轮为runs/explicit_labels_campus_1200s_02。Windows精简结果：D:/HT-Campus-1200s-20261118/results。完整MCAP和冻结留本地，不新增Release或上传原始包/视频，未完整远端备份前不得清理。新账本3/3次已用并关闭，不自动追加实验或候选，不部署实车。
'''
(dest/'REPORT_zh.md').write_text(report);shutil.copytree(dest,local,dirs_exist_ok=True);print(report)
