from pathlib import Path
import csv, hashlib, json, shutil

root=Path.cwd()
raw=root/Path('/tmp/ht_garage36_run_path').read_text().strip()
trial=raw/'garage'
out=root/'docs/results/ht_frozen_garage_10min_2026-10-19'
read=lambda p:json.loads(p.read_text())
manifest=read(trial/'manifest.json')
validation=read(trial/'suite_validation.json')
assert all(validation['checks'].values())
for name in ['latency_audit','search_audit','execution_geometry_audit','cell_coverage_audit','scheduling_audit']:
    shutil.copytree(trial/name,out/name)
for name in ['blocked_commands.json','pose_admission_audit.json','final_pose_snapshot.npz','planner_parameters.yaml','follower_parameters.yaml','context_consistency.json','recovery_wins.json','stop_episodes.json','context_integrity.json','parameter_capture_attempts.json','planner_parameters_wrong_node_attempt.yaml']:
    shutil.copy2(trial/name,out/'garage'/name)
for name,source in [('audit_ht_execution_geometry_scene.py','/tmp/audit_ht_execution_geometry_scene.py'),('audit_ht_search_termination_direct.py','/tmp/audit_ht_search_termination_direct.py'),('audit_ht_cell_coverage.py','/tmp/audit_ht_cell_coverage.py'),('audit_ht_recovery_wins.py','/tmp/audit_ht_recovery_wins.py'),('audit_ht_stop_episodes.py','/tmp/audit_ht_stop_episodes.py'),('audit_ht_context_integrity.py','/tmp/audit_ht_context_integrity.py'),('audit_ht_context_dumps.py',root/'presentations/audit_ht_context_dumps.py'),('audit_ht_search_scheduling.py',root/'presentations/audit_ht_search_scheduling.py')]:
    shutil.copy2(source,out/name)
    shutil.copy2(source,trial/name)
external=trial/'frozen_external_sources';external.mkdir();index={}
for path,digest in manifest['source_hashes'].items():
    p=Path(path)
    if not p.is_relative_to(root) and p.suffix in ['.py','.yaml','.cpp','.world','.sdf']:
        data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest
        name=f'{len(index):02}_'+p.name;(external/name).write_bytes(data)
        index[name]=dict(original_path=path,sha256=digest)
(external/'index.json').write_text(json.dumps(index,indent=2)+'\n')
shutil.copytree(external,out/'frozen_external_sources')
ctx=read(trial/'context_consistency.json');io=read(trial/'context_integrity.json')
assert ctx['all_checks_passed'] and io['passed']
examples=out/'inference_examples';examples.mkdir()
for row in ctx['model_replays']:shutil.copy2(root/row['file'],examples/Path(row['file']).name)
oldroot=root/'docs/results/ht_multiscene_10min_2026-10-17/garage'
old=read(oldroot/'manifest.json');indoor=read(root/'docs/results/ht_atomic_context_10min_2026-10-19/indoor/manifest.json')
common=manifest['source_hashes'].keys() & indoor['source_hashes'].keys()
changed={p:dict(indoor=indoor['source_hashes'][p],garage=manifest['source_hashes'][p]) for p in sorted(common) if indoor['source_hashes'][p]!=manifest['source_hashes'][p]}
assert not changed,changed
commonold=manifest['source_hashes'].keys() & old['source_hashes'].keys()
config=dict(tested_commit=manifest['git_head'],navigation_control_commit='391fa0f98fc2a0adab2c018b4c5a1c7c29efff91',ht_bridge_commit='445b5c1490d6bb198c35bee23e95fc0f7781407e',indoor_reference_commit=indoor['git_head'],shared_entries_identical=len(common),scene_specific_only=[p for p in manifest['source_hashes'] if p not in common],historical_garage_reference_commit=old['git_head'],historical_common_changed={p:dict(before=old['source_hashes'][p],after=manifest['source_hashes'][p]) for p in sorted(commonold) if old['source_hashes'][p]!=manifest['source_hashes'][p]},limitations='Same current control/model/bridge as stage35, different scene-specific world/configuration. Historical garage changed multiple components; the comparison cannot identify one fix effect.')
(out/'configuration_comparison.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n');shutil.copy2(out/'configuration_comparison.json',trial/'configuration_comparison.json')
summary=read(trial/'summary.json');audit=read(trial/'endurance_audit.json');m=audit['external_metrics'];mission=read(trial/'mission_audit.json');search=read(trial/'search_audit/summary.json')['all'];geom=read(trial/'execution_geometry_audit/summary.json');blocked=read(trial/'blocked_commands.json');sched=read(trial/'scheduling_audit/summary.json');video=validation['video']
experiment=dict(tested_git_head=manifest['git_head'],raw_run=str(raw),recording_scope=manifest['evidence_policy'],mission=mission,metrics=m,geometry=geom,blocked_command_audit=blocked,search=search,scheduling=sched,checks=validation['checks'],video=video,configuration=config,context_integrity={k:v for k,v in io.items() if k!='files'})
(out/'EXPERIMENT.json').write_text(json.dumps(experiment,ensure_ascii=False,indent=2)+'\n')
comparison=read(out/'comparison/comparison.json')['runs'];oldresult=comparison[0];current=comparison[1]
vchange=(current['observed_free_volume_m3']/oldresult['observed_free_volume_m3']-1)*100
prefix=f'''# 同一冻结版本：车库完整600秒验证

**{summary['distance_m']:.2f}米 / {m['observed_free_volume_m3']:.3f}立方米，末尾任务{mission['last_sampled_mission']}。** 最后一分钟{m['distance_last60_m']:.3f}米，最长全零{m['longest_zero_command_s']:.3f}秒。计时到600秒结束，不代表环境已经全部探索完。

## 本轮测什么

实测提交`{manifest['git_head'][:7]}`，导航控制391fa0f、桥接445b5c1，与阶段35室内相同。共同冻结清单的{len(common)}项全部相同，仅另选车库世界和场景配置，没有再修改控制、建图、模型或搜索预算。源文件/参数/二进制冻结核验全部通过。[配置及历史差异](configuration_comparison.json)。

速度上限0.5m/s，HT概率硬门槛0.5、3秒地图时效保护；车库实际几何余量为0.7m，加半个0.2m格对角线后参考半径{geom['radius_m']:.6f}m，规划另有0.12m跟踪预留。几何离线分析读取本轮实际参数，不沿用室内0.5m余量。HT物理支撑半径仍0.6m。该分析使用记录接收顺序/最新位姿和点云，未重建精确回调、局部网格裁剪或物理碰撞真值。

## 历史同场景对照

![同车库、同起点和速度的完整600秒对比](comparison/comparison.png)

| 版本 | 实测代码 | 里程m | 近似自由体积m³ | 最终状态 |
|---|---|---:|---:|---|
| 10月17日历史HT | {oldresult['git_head'][:7]} | {oldresult['distance_m']:.2f} | {oldresult['observed_free_volume_m3']:.3f} | {oldresult['final_mission']} |
| 本轮阶段36 | {current['git_head'][:7]} | {current['distance_m']:.2f} | {current['observed_free_volume_m3']:.3f} | {current['final_mission']} |

自由体积相对历史为{vchange:+.1f}%，请同时看轨迹、停车和任务状态。历史到当前有多项建图/语义/规划/任务管理修正，不能把差异归因于某一项修改。对比工具核对相同场景、0.5m/s速度、体积定义和起始位姿容差。每版本一次闭环试验，不是统计优越性证明，也没有用室内体积与车库排名。

体积由{m['processed_volume_scans']}个源秒激光计算0.5m自由体素并集近似，跳过{m['skipped_volume_scans']}，不是真值覆盖率。[指标定义](garage/metric_definition.json)。

## 实际问题与完整性

![搜索耗时、终止及拒绝类别](search_audit/searches.png)

本轮{search['count']}次搜索，终止{search['termination']}，其中{search['direct_connections']}次通过逐段检查的简单连接；搜索最大{search['elapsed_s']['max']:.6f}秒。全零停顿的时间和对应搜索见[停车记录](garage/stop_episodes.json)，完整控制拦截配对见[指令核查](garage/blocked_commands.json)。零平移可能包含原地旋转，不能都叫卡死；搜索超时也不证明地形本身不可通行。

{sum(validation['checks'].values())}/{len(validation['checks'])}项录制、冻结、退出检查通过。视频{video['decoded_frames']}帧/{video['duration_s']:.6f}秒完整解码（允许一帧误差）。{io['completed_npz_files']}份最终上下文ZIP和历史图CRC通过，坏文件{len(io['damaged_files'])}、遗留partial {len(io['remaining_partial_files'])}；{ctx['checked_contexts']}份窗口内上下文与同源图、三份冻结模型重算通过。仅验证保存的周期样本，不等于每一帧模型或物理真值都正确。[文件完整性](garage/context_integrity.json) · [输入/模型核查](garage/context_consistency.json)。

参数首查误用了不存在的/tare_planner名称，空YAML保留；节点列表确认后从/tare_planner_node成功获取参数。这是人工诊断查询错误，不是运行节点消失。[查询说明](garage/parameter_capture_attempts.json)。

![逐单元任务与待办](cell_coverage_audit/cell_coverage.png)

![几何参考距离](execution_geometry_audit/clearance.png)

![末段八方向HT硬门槛](garage/late_ht_footprint.png)

![末段实际环境](garage/late_camera.jpg)

单次完整记录不保证无限时间、多环境或实车稳定；仍需区分地图/路径时效、规划预算、全局目标回访和真正物理不可达。当前只证明所列条件下实际测得的结果，不是独立真值覆盖或完整轮胎/滑移动力学验收。

## 数据与视频

[完整600秒视频](garage/camera_h264.mp4) · [全部已录制数据及SHA256](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-frozen-garage)。完整数据是发布HT/控制/位姿/状态、源秒激光和周期地图/上下文，不是全部原始传感器无损采集。GitHub完整保留，本机保留最近两轮；上传校验后再清理旧录包，报告视频不删。

---

'''
oldtext=(out/'REPORT.md').read_text().replace('本次只发布选取的数据与视频。','本导出目录只含精选数据与视频；完整录包另见本轮Release及发布校验回执。')
(out/'REPORT.md').write_text(prefix+oldtext)
(out/'files_sha256.json').write_text(json.dumps({str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p.name!='files_sha256.json'},indent=2)+'\n')
print(json.dumps(dict(out=str(out),metrics=m,search=search,geometry=geom),ensure_ascii=False,indent=2))
