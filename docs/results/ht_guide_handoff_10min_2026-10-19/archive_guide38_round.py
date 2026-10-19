from pathlib import Path
import hashlib,json,shutil,yaml,subprocess
root=Path.cwd();raw=root/Path('/tmp/ht_guide38_run_path').read_text().strip();trial=raw/'garage';out=root/'docs/results/ht_guide_handoff_10min_2026-10-19';read=lambda p:json.loads(p.read_text());write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
validation=read(trial/'suite_validation.json');assert all(validation['checks'].values())
for name in ['latency_audit','search_audit','execution_geometry_audit','cell_coverage_audit','scheduling_audit']:shutil.copytree(trial/name,out/name)
for name in ['blocked_commands.json','pose_admission_audit.json','final_pose_snapshot.npz','planner_parameters.yaml','follower_parameters.yaml','context_consistency.json','recovery_wins.json','stop_episodes.json','context_integrity.json','parameter_capture_attempts.json','source_age_alignment.json','scan_delivery_trace.json','guide_handoff_audit.json']:shutil.copy2(trial/name,out/'garage'/name)
scripts={n:Path('/tmp')/n for n in ['audit_ht_execution_geometry_scene.py','audit_ht_search_termination_direct.py','audit_ht_cell_coverage.py','audit_ht_recovery_wins.py','audit_ht_stop_episodes.py','audit_ht_context_integrity.py','archive_guide38_round.py','ht_guide38_postrun.sh']}
scripts.update({n:root/'presentations'/n for n in ['audit_ht_context_dumps.py','audit_ht_search_scheduling.py','audit_ht_source_age_alignment.py','audit_ht_scan_delivery_trace.py','audit_ht_guide_handoff.py','plot_ht_guide_handoff.py']})
for name,source in scripts.items():shutil.copy2(source,out/name);shutil.copy2(source,trial/name)
manifest=read(trial/'manifest.json');external=trial/'frozen_external_sources';external.mkdir();index={}
for path,digest in manifest['source_hashes'].items():
 p=Path(path)
 if not p.is_relative_to(root) and p.suffix in ['.py','.yaml','.cpp','.world','.sdf']:
  data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest
  name=f'{len(index):02}_'+p.name;(external/name).write_bytes(data);index[name]=dict(original_path=path,sha256=digest)
write(external/'index.json',index);shutil.copytree(external,out/'frozen_external_sources')
reference=root/'docs/results/ht_serial_mapper_10min_2026-10-19/garage';old=read(reference/'manifest.json');changed={p:dict(before=old['source_hashes'].get(p),after=h) for p,h in manifest['source_hashes'].items() if old['source_hashes'].get(p)!=h};assert {Path(p).name for p in changed}=={'tare_planner_node','local_coverage_planner.h','exploration_progress.h','local_coverage_planner.cpp','sensor_coverage_planner_ground.cpp'}
params={n:yaml.safe_load((reference/n).read_text())==yaml.safe_load((trial/n).read_text()) for n in ['planner_parameters.yaml','follower_parameters.yaml']};assert all(params.values())
config=dict(reference_commit=old['git_head'],candidate_commit=manifest['git_head'],effective_parameters_equal=params,changed_manifest_entries=changed,unchanged_entries=len(manifest['source_hashes'])-len(changed),scope='Four navigation sources/headers and planner binary changed. HT, mapper, follower, model, rates and all effective parameters unchanged. Task identity and world status preserve pending guidance through tour omission; progress watchdog retained.')
write(out/'configuration_comparison.json',config);shutil.copy2(out/'configuration_comparison.json',trial/'configuration_comparison.json')
context=read(trial/'context_consistency.json');io=read(trial/'context_integrity.json');assert context['all_checks_passed'] and io['passed'];examples=out/'inference_examples';examples.mkdir()
for row in context['model_replays']:shutil.copy2(root/row['file'],examples/Path(row['file']).name)
shutil.copytree(root/'docs/fixes/evidence/2026-10-19_guide_handoff',out/'regression');shutil.copytree(root/'docs/fixes/evidence/2026-10-19_guide_handoff',trial/'regression')
(trial/'tested_source.patch').write_bytes(subprocess.check_output(['git','diff',old['git_head'],manifest['git_head'],'--','src/tare_planner']));shutil.copy2(trial/'tested_source.patch',out/'tested_source.patch')
summary=read(trial/'summary.json');audit=read(trial/'endurance_audit.json');m=audit['external_metrics'];mission=read(trial/'mission_audit.json');search=read(trial/'search_audit/summary.json')['all'];geom=read(trial/'execution_geometry_audit/summary.json');blocked=read(trial/'blocked_commands.json');age=audit['sampled_map_age_s'];guide=read(trial/'guide_handoff_audit.json');plot=read(out/'comparison/plot_evidence.json')
write(out/'EXPERIMENT.json',dict(tested_git_head=manifest['git_head'],raw_run=str(raw),recording_scope=manifest['evidence_policy'],metrics=m,mission=mission,search=search,geometry=geom,blocked_command_audit=blocked,checks=validation['checks'],video=validation['video'],configuration=config,context_integrity={k:v for k,v in io.items() if k!='files'},ht_map_age_s=age,guide_handoff={k:v for k,v in guide.items() if k not in ['switches','task_states']},efficiency=plot))
p=root/'docs/version_history.json';versions=read(p);assert not any(s['number']==38 for s in versions['stages']);versions['stages'].append(dict(id='stage-38',number=38,sha=manifest['git_head'],tag='ht-stage-20261019-guide-handoff',title='全局待办与局部委派交接保持，减少目标反复切换',kind='探索目标交接修复',change='按全局单元任务ID及EXPLORING状态保留引导，不把退出巡游列表当作任务完成；原进展超时与硬约束保留',features='交替tour委派、任务真实解除、无进展超时与旧行为回退回归通过；新增逐周期任务日志',validation=f"完整车库600秒{summary['distance_m']:.2f}m/{m['observed_free_volume_m3']:.3f}m³，末分钟新增553.750m³；13项采集及4项CTest通过",known_issues='对比37体积+28.4%、转向27%→20.3%、重复进入29.2%→14.7%；但低于36的7900.375m³，超时47→81、最长停车1.15→1.40s。仅单轮，整体效率/跨场景/实车仍未解决',evidence=['docs/results/ht_guide_handoff_10min_2026-10-19/REPORT.md'],control_commit=manifest['git_head'],ht_bridge_commit=versions['latest_ht_bridge_code']));versions['latest_planner_code']=manifest['git_head'];versions['latest_verified_trial_code']=manifest['git_head'];versions['latest_recorded_trial_code']=manifest['git_head'];versions['status']='阶段38：修复全局/局部任务交接，车库600秒202.58m/5807.000m³；相对37改善但仍未追平36，搜索超时增多，完整数据待本轮远端发布校验';write(p,versions)
prefix=f'''# 体积为什么变动，以及阶段38的修改和实测

**已修复一个确定的任务交接错误，并在同车库完整运行600秒：202.58米、5807.000m³。** 对比阶段37，体积提高28.4%、里程提高12.7%；仍低于阶段36，不能宣称所有波动消失。

## 为什么会波动

1. **单轮累计体积没有减少。** 阶段36/37/38的累计观测自由体素并集均单调不减；7900.375、4522.625、5807.000m³是不同实验结果。滚动局部地图有效面积/本帧数量本来会变化，不能与累计体积混用。[原始审计](regression/volume_monotonicity.json)、[本轮曲线证据](comparison/plot_evidence.json)。
2. **车辆走了不同路线。** 走回已经观察过的路，即使持续运动，新增体积也很少；之前37末分钟22.735米仅增8.375m³。输入/执行时序可能改变后续目标分支，单轮对照不能把全部差异归为某一改动。
3. **代码确实有任务交接错误。** TARE会从全局巡游中暂时移除委派局部窗口的任务，旧HT代码把“不在巡游列表”当作放弃当前引导的理由。目标未完成也被切换，继而拒绝当前局部承诺，导致反复折返。[原因、反例与回归](../../fixes/2026-10-19_guide_handoff.md)。

## 这次改了什么

全局引导携带单元任务ID，以全局EXPLORING状态决定是否继续，不单看巡游列表。真正任务解除时释放；保留到达、无进展60秒/静止12秒超时、冷却和每轮实际路线重搜，HT硬门槛/几何/速度/运动约束不变。

实测版本`{manifest['git_head'][:7]}`，相对37只有4项导航源文件/头文件和规划二进制改变，其余60项冻结条目相同；实际导航与控制参数一致。[冻结与参数对照](configuration_comparison.json)、[实际源代码差异](tested_source.patch)。四项CTest通过，包含交接保持、任务解除与超时反例；验证采集完整与验证导航性能分别统计。

## 三轮同条件对比

![累计、增量、轨迹、目标切换与运动组成](comparison/guide_handoff_comparison.png)

| 指标 | 阶段36 | 阶段37 修改前 | 阶段38 本轮 |
|---|---:|---:|---:|
| 累计近似观测自由体积m³ | 7900.375 | 4522.625 | 5807.000 |
| 实际里程m | 187.25 | 179.78 | 202.58 |
| 最后60秒新增m³ | 174.625 | 8.375 | 553.750 |
| 最后60秒里程m | 20.805 | 22.735 | 21.660 |
| 1m轨迹格重复进入占比 | 15.0% | 29.2% | 14.7% |
| 原地转向指令占比 | 21.7% | 27.0% | 20.3% |
| 完全停车占比 | 7.0% | 3.25% | 3.73% |
| 最长完全停车s | 4.95 | 1.15 | 1.40 |
| HT地图年龄P95 / 最大s | 2.115 / 4.117 | .842 / 1.840 | .822 / 1.790 |
| 搜索TIME_LIMIT次数 | 71 | 47 | 81 |
| 全程末尾任务 | EXPLORING | EXPLORING | EXPLORING |

同车库、近似相同起点、0.5m/s上限、相同0.5m自由体素并集、600个源秒激光且跳过0。每轮独立历史，累计体积是射线近似而非物理覆盖真值。回访按去除连续静止重复采样后的1m格进入序列，受边界抖动影响。

相对37，记录到的引导切换34→6次，300–540秒27→4次。新增日志有221个规划周期`in_tour=0,pending=1`，实际保持引导；仍有2次无进展超时，说明没有无限锁定目标。旧日志无任务ID，单元状态按最近中心推断，不冒充精确内部状态重放。待办仍在时到达旧连接点/超时也可合法换目标，不把所有切换算错误。

**退步与限制：** 体积仍比36低26.5%；搜索超时47→81，最大搜索.205s，最长停车1.15→1.40s。车辆末尾仍在探索，600秒到点停止录制，未完成整个环境。当前只验证这一轮车库，不保证不同随机时序/其他环境/实车稳定。

## 数据完整性与图册

13/13采集核验通过，四项CTest通过；9000帧/600秒视频完整解码。61份最终上下文及历史图CRC通过，无坏文件/partial，保存样本同源与三份冻结模型重算通过。577份记录几何样本未见名义余量重叠；1次几何晚拦截、1次HT晚拦截均配对零指令，未配对/拦截非零为0。这不是连续物理安全证明。

600个源帧匹配全trace，计数偏置恒143，3084个收到/处理回调与trace一致；只支持窗口内没有净相对漏收，不能排除源头漏发或共同漏收。真实参数第一次启动前发现失败，空文件保留，启动后成功获取且与37一致。

[历次多角度图册](history/index.html) · [合并PDF](history/all_comparisons.pdf) · [各轮指标和来源](history/measurements.csv)。每版改动、功能、已知缺陷全部列入，失败轮不隐藏。

![三轮累计、速度及轨迹](comparison/comparison.png)

![逐次搜索耗时与终止原因](search_audit/searches.png)

![各模块实际时延](latency_audit/latency.png)

![本轮末段HT硬门槛](garage/late_ht_footprint.png)

## 视频和完整数据

[600秒视频](garage/camera_h264.mp4) · [GitHub完整记录、视频和SHA256](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-guide-handoff)。记录为全部发布HT/控制/位姿/状态、源秒激光、周期地图/上下文；不是全频原始传感器无损录制。发布完成以仓库`stage38.json`远端校验回执为准。GitHub保留全部，本机只在远端核对后保留最近两轮完整录包，图文/视频/回归样本保留。

---

'''
(out/'REPORT.md').write_text(prefix+(out/'REPORT.md').read_text())
print(json.dumps(dict(output=str(out),tested=manifest['git_head'],search=search,guide={k:v for k,v in guide.items() if k not in ['switches','task_states']}),ensure_ascii=False,indent=2))
