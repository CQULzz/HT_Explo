from pathlib import Path
import hashlib,json,shutil,yaml

root=Path.cwd();raw=root/Path('/tmp/ht_serial37_run_path').read_text().strip();trial=raw/'garage';out=root/'docs/results/ht_serial_mapper_10min_2026-10-19';read=lambda p:json.loads(p.read_text())
validation=read(trial/'suite_validation.json');assert all(validation['checks'].values())
for name in ['latency_audit','search_audit','execution_geometry_audit','cell_coverage_audit','scheduling_audit']:shutil.copytree(trial/name,out/name)
for name in ['blocked_commands.json','pose_admission_audit.json','final_pose_snapshot.npz','planner_parameters.yaml','follower_parameters.yaml','context_consistency.json','recovery_wins.json','stop_episodes.json','context_integrity.json','parameter_capture_attempts.json','source_age_alignment.json']:shutil.copy2(trial/name,out/'garage'/name)
scripts={'audit_ht_execution_geometry_scene.py':'/tmp/audit_ht_execution_geometry_scene.py','audit_ht_search_termination_direct.py':'/tmp/audit_ht_search_termination_direct.py','audit_ht_cell_coverage.py':'/tmp/audit_ht_cell_coverage.py','audit_ht_recovery_wins.py':'/tmp/audit_ht_recovery_wins.py','audit_ht_stop_episodes.py':'/tmp/audit_ht_stop_episodes.py','audit_ht_context_integrity.py':'/tmp/audit_ht_context_integrity.py','audit_ht_context_dumps.py':root/'presentations/audit_ht_context_dumps.py','audit_ht_search_scheduling.py':root/'presentations/audit_ht_search_scheduling.py','audit_ht_source_age_alignment.py':root/'presentations/audit_ht_source_age_alignment.py','archive_serial37_round.py':'/tmp/archive_serial37_round.py','ht_serial37_postrun.sh':'/tmp/ht_serial37_postrun.sh'}
for name,source in scripts.items():shutil.copy2(source,out/name);shutil.copy2(source,trial/name)
manifest=read(trial/'manifest.json');external=trial/'frozen_external_sources';external.mkdir();index={}
for path,digest in manifest['source_hashes'].items():
 p=Path(path)
 if not p.is_relative_to(root) and p.suffix in ['.py','.yaml','.cpp','.world','.sdf']:
  data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest
  name=f'{len(index):02}_'+p.name;(external/name).write_bytes(data);index[name]=dict(original_path=path,sha256=digest)
(external/'index.json').write_text(json.dumps(index,indent=2)+'\n');shutil.copytree(external,out/'frozen_external_sources')
reference=root/'docs/results/ht_frozen_garage_10min_2026-10-19/garage';old=read(reference/'manifest.json');changed={p:dict(before=old['source_hashes'].get(p),after=h) for p,h in manifest['source_hashes'].items() if old['source_hashes'].get(p)!=h};assert {Path(p).name for p in changed}=={'elevation_mapping_node','elevation_mapping_ros.py'}
params={n:yaml.safe_load((reference/n).read_text())==yaml.safe_load((trial/n).read_text()) for n in ['planner_parameters.yaml','follower_parameters.yaml']};assert all(params.values())
config=dict(reference_commit=old['git_head'],candidate_commit=manifest['git_head'],navigation_control_commit='391fa0f98fc2a0adab2c018b4c5a1c7c29efff91',ht_bridge_commit='445b5c1490d6bb198c35bee23e95fc0f7781407e',effective_parameters_equal=params,changed_manifest_entries=changed,unchanged_entries=len(manifest['source_hashes'])-len(changed),scope='Only independent CuPy node source and installed entry point differ. No fusion formula, model, queue, timing rates, source timestamp, HT or navigation threshold changes; callback ordering and trajectory may differ.')
(out/'configuration_comparison.json').write_text(json.dumps(config,ensure_ascii=False,indent=2)+'\n');shutil.copy2(out/'configuration_comparison.json',trial/'configuration_comparison.json')
context=read(trial/'context_consistency.json');io=read(trial/'context_integrity.json');assert context['all_checks_passed'] and io['passed'];examples=out/'inference_examples';examples.mkdir()
for row in context['model_replays']:shutil.copy2(root/row['file'],examples/Path(row['file']).name)
shutil.copytree(root/'docs/fixes/evidence/2026-10-19_serial_mapping_executor',out/'regression');shutil.copytree(root/'docs/fixes/evidence/2026-10-19_serial_mapping_executor',trial/'regression')
for name in ['ht_allocator_managed','ht_allocator_device']:shutil.copytree('/tmp/'+name,trial/'regression'/name)
shutil.copytree(root/'patches/cupy/2026-10-19_serial_map_executor',out/'cupy_patch');shutil.copytree(root/'patches/cupy/2026-10-19_serial_map_executor',trial/'cupy_patch')
summary=read(trial/'summary.json');audit=read(trial/'endurance_audit.json');m=audit['external_metrics'];mission=read(trial/'mission_audit.json');search=read(trial/'search_audit/summary.json')['all'];geom=read(trial/'execution_geometry_audit/summary.json');blocked=read(trial/'blocked_commands.json');latency=read(trial/'latency_audit/audit.json');oldm=read(reference/'endurance_audit.json')['external_metrics'];oldage=read(reference/'endurance_audit.json')['sampled_map_age_s'];age=audit['sampled_map_age_s'];video=validation['video'];align=read(trial/'source_age_alignment.json')
experiment=dict(tested_git_head=manifest['git_head'],raw_run=str(raw),recording_scope=manifest['evidence_policy'],metrics=m,mission=mission,search=search,geometry=geom,blocked_command_audit=blocked,checks=validation['checks'],video=video,configuration=config,context_integrity={k:v for k,v in io.items() if k!='files'},ht_map_age_s=age,source_age_alignment=align)
(out/'EXPERIMENT.json').write_text(json.dumps(experiment,ensure_ascii=False,indent=2)+'\n')
p=root/'docs/version_history.json';versions=read(p);versions['stages'].append(dict(id='stage-37',number=37,sha=manifest['git_head'],tag='ht-stage-20261019-serial-mapper',title='地图串行执行与独立TF接收，修复调度长等待',kind='建图调度修复',change='CuPy主执行器改为单线程，TF由独立子节点/单线程接收；融合与安全门槛保留',features='真实TF回放复现原四线程P95 1.106s，修复布局.0021s；实际ROS等待未来TF及关闭回归通过',validation=f"完整车库600秒{summary['distance_m']:.2f}m/{m['observed_free_volume_m3']:.3f}m³，13项采集通过，HT年龄P95{age['p95']:.3f}s/最大{age['max']:.3f}s",known_issues=f"仍{search['termination'].get('TIME_LIMIT',0)}次搜索超时，最长停车{m['longest_zero_command_s']:.3f}s；单轮不证明所有场景稳定，未验收独立覆盖真值/实车",evidence=['docs/results/ht_serial_mapper_10min_2026-10-19/REPORT.md'],control_commit=versions['latest_planner_code'],ht_bridge_commit=versions['latest_ht_bridge_code']));versions['latest_cupy_node_code']=manifest['git_head'];versions['latest_verified_trial_code']=manifest['git_head'];versions['latest_recorded_trial_code']=manifest['git_head'];versions['status']=f"阶段37地图调度修复，车库600秒{summary['distance_m']:.2f}m/{m['observed_free_volume_m3']:.3f}m³，地图年龄P95{age['p95']:.3f}s/最大{age['max']:.3f}s；完成多角度图后按用户要求停止";p.write_text(json.dumps(versions,ensure_ascii=False,indent=2)+'\n')
prefix=f'''# 地图调度修复：车库完整600秒与历次多角度对比

**{summary['distance_m']:.2f}米 / {m['observed_free_volume_m3']:.3f}立方米，末尾任务{mission['last_sampled_mission']}。** 最后一分钟{m['distance_last60_m']:.3f}米，最长停车{m['longest_zero_command_s']:.3f}秒。定时录满600秒不表示场景已经全探索完。

## 为什么改、改了什么

阶段36有地图时效长尾。先排除不成立的解释：串行固定输入的GPU运算本身毫秒级，改分配器未见提速；无真实TF的简单多线程负载也未复现秒级等待。加入原MCAP的实际TF输入后，四线程P95 1.106s/最大1.905s，28s用24.56s进程CPU；地图单线程、TF独立接收布局P95 .0021s，CPU2.68s，受控复现支持修复调度竞争。[原因、反例与回归](../../fixes/2026-10-19_serial_mapping_executor.md)。

实际修改独立CuPy工作区的地图节点源码及安装入口，二者同版；地图回调串行，TF由独立子节点/单线程接收。实际ROS回归证明：地图回调等待尚未发布的新TF时仍能接收并返回，关闭幂等、无线程残留。保持融合公式、模型、可靠队列深度30、源时间戳/观测年龄和全部定时频率。HT工作区与CuPy工作区仍独立。[完整补丁](cupy_patch/)。

实测提交`{manifest['git_head'][:7]}`，导航仍391fa0f、HT桥接445b5c1；65项冻结条目只有CuPy节点与安装入口两项变化，其余63项一致。全部实际导航/跟踪参数一致。[逐项对照](configuration_comparison.json)。相同车库/起点/0.5m/s上限、HT硬门槛0.5与3秒时效保护；回调时序仍可能改变路线，不宣称逐帧等价或全部提升归于单一低层机制。

## 本轮与修改前

![相同场景的体积、里程、速度与轨迹](comparison/comparison.png)

| 指标 | 阶段36修改前 | 阶段37修改后 |
|---|---:|---:|
| 近似自由体积m³ | {oldm['observed_free_volume_m3']:.3f} | {m['observed_free_volume_m3']:.3f} |
| 行驶距离m | {read(reference/'summary.json')['distance_m']:.2f} | {summary['distance_m']:.2f} |
| 最后60秒行驶m | {oldm['distance_last60_m']:.3f} | {m['distance_last60_m']:.3f} |
| HT地图年龄P95s（1Hz采样） | {oldage['p95']:.3f} | {age['p95']:.3f} |
| HT地图年龄最大s（1Hz采样） | {oldage['max']:.3f} | {age['max']:.3f} |
| 最长停车s | {oldm['longest_zero_command_s']:.3f} | {m['longest_zero_command_s']:.3f} |
| 原地转向比例 | {oldm['stationary_turn_fraction']:.1%} | {m['stationary_turn_fraction']:.1%} |
| 倒车指令比例 | {oldm['reverse_command_fraction']:.1%} | {m['reverse_command_fraction']:.1%} |
| HT_MAP_STALE控制状态条数 | {oldm['follower_status_samples'].get('HT_MAP_STALE',0)} | {m['follower_status_samples'].get('HT_MAP_STALE',0)} |
| PATH_STALE控制状态条数 | {oldm['follower_status_samples'].get('PATH_STALE',0)} | {m['follower_status_samples'].get('PATH_STALE',0)} |

体积基于{m['processed_volume_scans']}个源秒激光的0.5m自由体素并集，跳过{m['skipped_volume_scans']}；不是真值覆盖率。每版本一次闭环试验，同时看效率与停顿，不能据单项指标宣称普遍优越。停车按|v|<.01且|ω|<.05统计，原地转向另计。

## 每次更改，从多个角度看

[历次图册：逐版总览、累计曲线、每分钟新增观测、运动构成、延迟分布、统一尺度轨迹与任务状态](history/REPORT.md)。室内与车库分开作图，失败轮和阶段34的退出诊断异常不删。原来的相对测量秒口径从旧MCAP统一源秒重算，原历史报告不回写；无本协议600秒曲线的早期阶段只列证据，不补造曲线。[全部版本数据覆盖表](history/version_data_coverage.csv)。

![车库各版本多指标总览](history/garage_01_overview.png)

![室内各次修改的每分钟新增观测](history/indoor_03_minute_gain.png)

## 录制和剩余问题

{sum(validation['checks'].values())}/{len(validation['checks'])}项采集、冻结、退出核验通过；视频{video['decoded_frames']}帧/{video['duration_s']:.6f}s完整解码，允许一帧误差。{io['completed_npz_files']}份最终上下文和历史图ZIP CRC通过，坏文件{len(io['damaged_files'])}、遗留partial{len(io['remaining_partial_files'])}。{context['checked_contexts']}份窗口内上下文同源核对、三份冻结模型重算通过；仅验证周期保存的样本。

搜索终止{search['termination']}，仍须关注搜索预算、全局待办/回访、转向与真正物理不可达。晚拒绝后非零指令{blocked['blocked_nonzero_count']}、未配对拦截{blocked['unmatched_command_rejections']}；记录几何样本不是连续时刻物理安全证明。独立覆盖真值、完整轮胎/滑移动力学、其他当前版场景和实车未验收，不能说系统所有问题都已解决。

![各阶段实际计时](latency_audit/latency.png)

![搜索终止与耗时](search_audit/searches.png)

![末段HT硬门槛](garage/late_ht_footprint.png)

## 数据、视频与停止

[完整视频](garage/camera_h264.mp4) · [全部已录制数据与SHA256](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-serial-mapper)。记录为发布HT/控制/位姿/状态、源秒激光和周期地图/上下文，不是所有原始传感器无损采集。GitHub完整保留，本机最近两轮，先验证远端再清理旧录包；报告/图表/视频和回归样本保留。

按用户本次要求：修复、完整验证和出图完成后停止本次自动迭代，不再继续启动其他环境或新候选。本轮仿真计时结束即由记录器正常关闭，上传与图表完成后不留后台实验。

---

'''
(out/'REPORT.md').write_text(prefix+(out/'REPORT.md').read_text())
print(json.dumps(dict(out=str(out),metrics=m,map_age=age,search=search),ensure_ascii=False,indent=2))
