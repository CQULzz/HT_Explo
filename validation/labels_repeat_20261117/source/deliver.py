from pathlib import Path
import json,shutil
root=Path('/home/lzz/ht_labels_repeat_20261117');run=root/'runs/explicit_labels_campus_repeat_01';repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');dest=repo/'validation/labels_repeat_20261117';local=Path('/mnt/d/HT-Labels-Repeat-20261117/results')
dest.mkdir(exist_ok=False);(dest/'data').mkdir();(dest/'logs').mkdir();(dest/'source').mkdir()
for n in ['RESULT.json','ANALYSIS.json','COMMAND_AUDIT.json','RECORDING_VALIDATION.json','FREEZE.json','CLEANUP.json','COMMANDS.json','tare_planner_node.yaml','localPlanner.yaml','pathFollower.yaml','cupy_to_ht_bridge.yaml','vehicleSimulator.yaml','comparison.png']:
 shutil.copy2(run/n,dest/n)
for n in ['PLAN.json','BUDGET.json']:shutil.copy2(root/n,dest/n)
for n in ['metrics.csv','SUMMARY.json','START.json']:shutil.copy2(run/'observations'/n,dest/'data'/n)
for n in ['simulation.log','mapper.log','model.log','observer.log','bag.log']:shutil.copy2(run/n,dest/'logs'/n)
for n in ['run.py','run_300s.sh','env.sh','simulation.launch.py','recording_qos.yaml']:shutil.copy2(root/n,dest/'source'/n)
for n in ['prepare.py','postprocess.py','deliver.py']:shutil.copy2(Path('/mnt/d/HT-Labels-Repeat-20261117')/n,dest/'source'/n)
(dest/'.gitattributes').write_text('*.log -text -whitespace\n*.yaml -text -whitespace\ndata/*.csv -text -whitespace\n')
a=json.loads((run/'ANALYSIS.json').read_text());audit=json.loads((run/'COMMAND_AUDIT.json').read_text());v=json.loads((run/'RECORDING_VALIDATION.json').read_text());cleanup=json.loads((run/'CLEANUP.json').read_text());res=json.loads((run/'RESULT.json').read_text())
old=json.loads((repo/'validation/labels_300s_20261116/ANALYSIS.json').read_text());finish='未发出' if a['finish_signal_elapsed_s'] is None else f"{a['finish_signal_elapsed_s']:.3f}秒"
text=f'''# campus 同配置300秒复跑（2026-11-17）

用户要求“你再探索一次试试”。本轮不修改导航，沿用实际测试代码11dd46d5561a0b426ebc800e192d9f42d0d8b00d、Helios32标称32×1800/仿真10Hz、车体crop_box、固定0.65m起点先验和explicit_labels_v1。运行前上次305个冻结文件逐一SHA相同；本轮仅隔离输出、ROS域223、Gazebo11539及Xvfb:103。未建立可重复的同一显式随机种子，不能把路线差异归因于代码改善。

## 结果

| 指标 | 上次 | 本轮 |
|---|---:|---:|
| 就绪后采集墙钟秒 | 300.002104 | {a['duration_s']:.6f} |
| 累计里程m | 37.686604 | {a['distance_m']:.6f} |
| 末30秒里程m | 0 | {a['last30_distance_m']:.6f} |
| 采样观测体积代理m³ | 3645.625 | {a['sampled_free_volume_m3']:.3f} |
| 完成信号 | 52.101秒 | {finish} |
| finish最终值 | true | {str(a['finish']).lower()} |

- 扫描/HT接收频率：{a['wall_rates']['scans']:.4f}/{a['wall_rates']['ht_maps']:.4f}Hz墙钟。
- 抽样HT年龄P95：{a['sampled_ht_age_s']['p95']:.6f}秒，>1秒比例{a['fraction_sampled_age_over_1s']:.4%}。桥使用主机重打戳，不能称物理端到端测量延迟。
- 独立原图命令审计passed={audit['passed']}，计数{json.dumps(audit['counts'],ensure_ascii=False)}。缺图不以邻帧替代。
- 五节点参数语义比较：{json.dumps(a['parameter_comparison_with_previous'],ensure_ascii=False)}。
- 完整采集={res['collection_complete']}；前后冻结一致={res['freeze_unchanged']}；完整归档逐条冻结检查={v['frozen_archive_matches_manifest']}（{v['frozen_files']}个文件）；MCAP可用CRC/metadata计数核对通过，共{v['messages']}消息。
- SIGINT子进程干净退出={cleanup['clean_child_exit']}，相关残留={len(cleanup['relevant_processes_remaining'])}，错误原文见CLEANUP.json。

末段规划诊断：

```text
{a['last_planner_diagnostic']}
```

## 解释与限制

本轮是否再次提前完成，以完成信号、末30秒运动和完整轨迹共同判断。未修改任务生成、完成条件、HT门限或起点标签语义；单次同配置复跑不同路线不能证明前次缺陷已修复。全campus真值覆盖率没有核验；观测体积是采样射线代理，不能当可通过地面面积或完整覆盖率。上次完成后零计数含停止更新造成的零初始化，不是全图实测覆盖完成证据。

![同配置轨迹、里程与观测量比较](comparison.png)

## 保存和预算

完整录包/冻结：`{run}`。Windows精简结果：`D:/HT-Labels-Repeat-20261117/results`。本轮没有新RViz视频，也不上传视频/原始MCAP。新账本已关闭，最多2次仅基础设施失败重试，实际使用{json.loads((root/'BUDGET.json').read_text())['used_attempts']}次，不自动追加探索。旧数据不覆盖、不清理。
'''
(dest/'REPORT_zh.md').write_text(text);shutil.copytree(dest,local,dirs_exist_ok=True);print(text)
