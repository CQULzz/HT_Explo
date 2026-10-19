from pathlib import Path
import hashlib,json,shutil,csv,yaml,subprocess
import numpy as np
root=Path.cwd();raw=root/Path('/tmp/ht_tare41_run_path').read_text().strip();trial=raw/'garage';out=root/'docs/results/ht_tare_boundaries_10min_2026-10-20';read=lambda p:json.loads(p.read_text());write=lambda p,j:p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
validation=read(trial/'suite_validation.json');assert all(validation['checks'].values())
for name in ['latency_audit','execution_geometry_audit','tare_waypoint_audit']:shutil.copytree(trial/name,out/name)
for name in ['blocked_commands.json','pose_admission_audit.json','final_pose_snapshot.npz','planner_parameters.yaml','follower_parameters.yaml','context_consistency.json','stop_episodes.json','context_integrity.json','parameter_capture_attempts.json','source_age_alignment.json','scan_delivery_trace.json','terrain_topic_isolation.json']:shutil.copy2(trial/name,out/'garage'/name)
for name in ['audit_ht_execution_geometry_scene.py','audit_ht_stop_episodes.py','audit_ht_context_integrity.py','archive_tare41_round.py','ht_tare41_postrun.sh','capture_tare41_parameters.py','capture_tare41_isolation.py']:
 p=Path('/tmp')/name;shutil.copy2(p,out/name);shutil.copy2(p,trial/name)
for name in ['audit_tare_waypoint.py','audit_ht_context_dumps.py','audit_ht_source_age_alignment.py','audit_ht_scan_delivery_trace.py','plot_tare_route_comparison.py']:
 shutil.copy2(root/'presentations'/name,out/name);shutil.copy2(root/'presentations'/name,trial/name)
shutil.copytree(root/'docs/fixes/evidence/2026-10-20_tare_waypoint_boundaries',out/'regression_and_counterexamples')
manifest=read(trial/'manifest.json');reference=root/'docs/results/ht_tare_waypoint_10min_2026-10-20/garage';previous=read(reference/'manifest.json');external=trial/'frozen_external_sources';external.mkdir();index={}
for path,digest in manifest['source_hashes'].items():
 p=Path(path)
 if not p.is_relative_to(root) and p.suffix in ['.py','.yaml','.cpp','.world','.sdf']:
  data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest
  name=f'{len(index):02}_'+p.name;(external/name).write_bytes(data);index[name]=dict(original_path=path,sha256=digest)
write(external/'index.json',index);shutil.copytree(external,out/'frozen_external_sources')
source=out/'candidate_sources';source.mkdir()
for path,digest in manifest['source_hashes'].items():
 p=Path(path)
 if p.is_relative_to(root) and p.suffix in ['.py','.yaml','.cpp','.h','.world','.sdf','.txt'] and 'install_standalone' not in str(p):
  data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest;dest=source/p.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
subprocess.run(['git','diff',previous['git_head'],manifest['git_head'],'--','src/tare_planner'],stdout=(out/'tested_source.patch').open('w'),check=True)
params={}
for name in ['planner_parameters.yaml','follower_parameters.yaml']:
 a=yaml.safe_load((reference/name).read_text());b=yaml.safe_load((trial/name).read_text());node=next(iter(b));a=a[node]['ros__parameters'];b=b[node]['ros__parameters'];params[name]={k:dict(before=a.get(k),after=b.get(k)) for k in sorted(a.keys()|b.keys()) if a.get(k)!=b.get(k)}
assert not any(params.values()),params
config=dict(reference_commit=previous['git_head'],candidate_commit=manifest['git_head'],parameter_changes=params,source_changes={p:dict(before=previous['source_hashes'].get(p),after=h) for p,h in manifest['source_hashes'].items() if previous['source_hashes'].get(p)!=h},note='All actual ROS parameters match stage40. Terrain graph snapshot and native HOME priority corrected; original six TARE method bodies unchanged.')
write(out/'configuration_comparison.json',config)
summary=read(trial/'summary.json');audit=read(trial/'endurance_audit.json');m=audit['external_metrics'];age=audit['sampled_map_age_s'];mission=read(trial/'mission_audit.json');contract=read(trial/'tare_waypoint_audit/summary.json');geom=read(trial/'execution_geometry_audit/summary.json');blocked=read(trial/'blocked_commands.json');io=read(trial/'context_integrity.json');ctx=read(trial/'context_consistency.json');isolation=read(trial/'terrain_topic_isolation.json')
assert isolation['/terrain_map']['publishers']==[] and isolation['/terrain_map_ext']['publishers']==[]
with (trial/'current/observation_volume.csv').open() as f:volume=list(csv.DictReader(f))
gain=m['observed_free_volume_m3']-float(np.interp(540,[float(v['time_s']) for v in volume],[float(v['observed_free_volume_m3']) for v in volume]));old=read(reference/'endurance_audit.json');oldm=old['external_metrics'];olds=read(reference/'summary.json');pct40=(m['observed_free_volume_m3']/oldm['observed_free_volume_m3']-1)*100;pct39=(m['observed_free_volume_m3']/6483.-1)*100
issues=f"搜索时间上限{contract['search_termination'].get('TIME_LIMIT',0)}次、展开上限{contract['search_termination'].get('EXPANSION_LIMIT',0)}次，最长完全停车{m['longest_zero_command_s']:.2f}s，末60秒新增{gain:.3f}m³/移动{m['distance_last60_m']:.2f}m；末尾{mission['last_sampled_mission']}。"
write(out/'EXPERIMENT.json',dict(tested_git_head=manifest['git_head'],raw_run=str(raw),recording_scope=manifest['evidence_policy'],metrics=m,mission=mission,tare_waypoint=contract,geometry=geom,blocked_command_audit=blocked,checks=validation['checks'],video=validation['video'],configuration=config,context_integrity=io,ht_map_age_s=age,last60_gain_m3=gain,volume_pct_vs40=pct40,volume_pct_vs39=pct39))
base39=root/'docs/results/ht_successor_pruning_10min_2026-10-20/garage';s39=read(base39/'summary.json');m39=read(base39/'endurance_audit.json')['external_metrics']
rows=[('近似观测自由体积m³',m39['observed_free_volume_m3'],oldm['observed_free_volume_m3'],m['observed_free_volume_m3']),('实际里程m',s39['distance_m'],olds['distance_m'],summary['distance_m']),('末60秒移动m',m39['distance_last60_m'],oldm['distance_last60_m'],m['distance_last60_m']),('完全停车比例',f"{m39['fully_stopped_fraction']:.2%}",f"{oldm['fully_stopped_fraction']:.2%}",f"{m['fully_stopped_fraction']:.2%}"),('原地转向比例',f"{m39['stationary_turn_fraction']:.2%}",f"{oldm['stationary_turn_fraction']:.2%}",f"{m['stationary_turn_fraction']:.2%}"),('最长完全停车s',round(m39['longest_zero_command_s'],3),round(oldm['longest_zero_command_s'],3),round(m['longest_zero_command_s'],3)),('规划P95s',s39['planner_runtime_p95_s'],olds['planner_runtime_p95_s'],summary['planner_runtime_p95_s'])]
table='| 指标 | 39：HT自选目标 | 40：原TARE+HT | 41：接口边界修正 |\n|---|---:|---:|---:|\n'+''.join(f'| {k} | {a} | {b} | {c} |\n' for k,a,b,c in rows)
(out/'REPORT.md').write_text(f'''# 阶段41：保持原TARE决策，修正HT输入一致性与近家返航

**同车库完整600秒：{summary['distance_m']:.2f}m，近似观测自由体积{m['observed_free_volume_m3']:.3f}m³；较39为{pct39:+.1f}%，较40为{pct40:+.1f}%。** {issues}单次闭环不证明统计优越或单项因果提升。前进、倒车、角速度和加速度上限未增加。

## 最终分工与计划

原TARE完成覆盖估计、视点采样、全局/局部TSP及访问顺序、前视点与原航点延伸；HT只找当前odom到TARE当前航点的XYθ可执行路线。航点太远时，沿TARE路线分支取局部前缀；找不到路发零，不改选收益点。[原先行计划](../../plans/2026-10-20_tare_ht_waypoint_plan.md) · [边界修正先行计划](../../plans/2026-10-20_tare_ht_boundary_plan.md)。实测代码`{manifest['git_head']}`。

六个核心函数体仍与原ROS2适配参考`b6760ad`逐字SHA一致。[检查](regression_and_counterexamples/regression/ht_tare41_upstream_contract.json)。并非声称整个包等同于官方ROS1源码；局部XYθ执行器和必要的传感器/控制保护保留。

## 先复现，再修正的两个边界

阶段40闭环后，用真实ViewPointManager构造禁行带，确实出现connected=1/candidate=1而实际最短路为空，测试失败；不能因为视频没卡死就忽略。HT删点先前发生在BFS之后，破坏原TARE图连通性前提。本轮一次读取地形顶点掩码，BFS和候选图共用；异步新地图不会在两步之间再次删点，下一周期再更新。执行仍用最新HT硬检查，因此粗图快照不是过期地图行驶许可。禁行带、异步更新、下一周期同步和解除禁行的真实ROS回归通过。[根因与证据](../../fixes/2026-10-20_tare_waypoint_boundaries.md)

近家返航源条件反例：原前视函数可能不输出目标，但原PublishWaypoint优先HOME；包装层原先先判断前视有效性会错误停车。本轮恢复HOME优先级，并选择原近家ROBOT→HOME分支交给HT。原前视返回标志仍原样供TSP使用；没有绕过HT/几何/传感器检查。此项有明确单元/分支回归，若本轮没有触发任务完成/返航，不能说已完成真实闭环返航验收。

CuPy/HT模型及历史融合不变。导航高程仍来自同源第12层ht_elevation；CMU地形只供模拟器贴地，TARE原地形话题无发布者。[现场隔离检查](garage/terrain_topic_isolation.json)

## 多视点序列与实际执行证据

{contract['coverage_cycles']}个原覆盖周期，原TSP实际调用分布{contract['tsp_calls']}，最大访问序列{contract['maximum_ordered_viewpoints']}个，平均{contract['mean_ordered_viewpoints']:.2f}个。{contract['moving_waypoints']}个允许移动的航点与原TARE输出相符；{contract['local_goals']}个HT局部目标位于对应原路线分支，记录级违例{len(contract['contract_violations'])}。[原TARE→HT接口审计](tare_waypoint_audit/summary.json)

![原TSP序列与HT执行分工](tare_waypoint_audit/architecture.png)

![实际记录中的路线、原航点与HT执行轨迹](tare_waypoint_audit/routes.png)

灰线为TARE未来访问路线，橙线为当前分支，蓝线为发布执行的XYθ路线的XY投影；不是把整条TSP序列都当成已经走过的轨迹。

## 同条件比较，保留改善与退步

{table}

![累计观测、每分钟新增、里程、速度、运动组成和每米收益](comparison/tare_architecture_comparison.png)

![同尺度实际轨迹](comparison/tare_trajectories.png)

39/40/41均车库600秒、近似相同起点及相同运动限制。本轮与40的实际参数逐项完全一致，[源码和配置对照](configuration_comparison.json)。40一次恢复了覆盖结构和地形接口，41只修正两处接口并保存构造失败，不能把闭环轨迹差异直接归因于某一项修复。原TARE历史控制限制更宽松，尚无完全同限制的新600秒原版配对，不宣称已追平原版。

## 验证范围与剩余问题

{issues} 搜索预算失败不等于地形绝对不可通。粗TARE候选图的可达性不是完整SE2可达性保证；某个原TARE航点仍可能在局部HT图中无可执行路径。远端未知用于乐观引导，执行必须通过新鲜局部HT。HT地图噪声、必要绕行、长时间和其他环境仍需单独评估，没有独立物理覆盖真值或完整轮胎动力学/实车验收。

13项采集、4项CTest及原六函数SHA检查通过；视频{validation['video']['decoded_frames']}帧/{validation['video']['duration_s']:.6f}秒完整解码。{io['completed_npz_files']}份上下文/历史图CRC通过：{io['passed']}；{ctx['checked_contexts']}份同源输入样本及模型重算通过：{ctx['all_checks_passed']}。

HT拦截非零{blocked['blocked_nonzero_count']}、未配对{blocked['unmatched_command_rejections']}；几何拦截非零{blocked['geometry_nonzero_count']}、未配对{blocked['unmatched_geometry_rejections']}。几何采样余量重叠{geom['overlap_samples']}/{geom['samples']}，旧指令外推碰余量{geom['moving_predictions_inside_margin']}；采样和外推不等于连续物理接触真值。[几何采样](execution_geometry_audit/summary.json)

观测自由体积按源秒激光{m['processed_volume_scans']}帧计算，0.5m体素并集，跳过{m['skipped_volume_scans']}；MCAP保留全部发布HT/控制/odom/状态，激光按源秒、地图和模型输入周期采样，不是全部原始传感器无损数据。

[完整视频](garage/camera_h264.mp4) · [历次多角度图册](history/index.html) · [PDF](history/all_comparisons.pdf) · [完整数据Release](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261020-tare-boundaries)。完整上传以stage41.json远端大小/SHA256回执为准。GitHub全部保留，本机仅留最近两轮已核验完整原始数据。本轮发布后停止扩展新候选。

![地图与规划时延](latency_audit/latency.png)

![末段实际HT硬门槛](garage/late_ht_footprint.png)
''')
v=read(root/'docs/version_history.json');assert not any(s['number']==41 for s in v['stages']);stage=dict(id='stage-41',number=41,sha=manifest['git_head'],tag='ht-stage-20261020-tare-boundaries',title='原TARE图与HT禁行掩码同步，恢复近家HOME优先级',kind='原TARE架构内的地形/执行接口修正',change='BFS/候选图共用本周期地形掩码；近家rush-home目标优先，再做HT路由；不改六核心TARE函数与TSP',features='真实ROS禁行带、异步更新、解除禁行及HOME无前视回归通过；原40失败证据保留',validation=f"完整车库600秒{summary['distance_m']:.2f}m/{m['observed_free_volume_m3']:.3f}m³，13项采集、4项CTest与六函数SHA通过",known_issues=issues+' 单次闭环不证明因果收益；没有同限制新原版配对、全局SE2可达/实车保证；返航单元回归不等于该600秒触发返航',evidence=[str((out/'REPORT.md').relative_to(root))],control_commit=manifest['git_head'],ht_bridge_commit='42966cb22b0f719df035391f3850b9a654f161e1');v['stages'].append(stage)
for field in ['latest_planner_change','latest_planner_code','latest_verified_trial_code','latest_recorded_trial_code']:v[field]=manifest['git_head']
v['status']='阶段41完成原TARE+HT接口修正600秒，完整数据待发布核验。'+issues;write(root/'docs/version_history.json',v)
(root/'docs/release_notes/ht-stage-20261020-tare-boundaries.md').write_text(f'''## 改了什么

在40恢复原TARE覆盖/TSP的基础上修正地形顶点掩码与BFS不一致、近家HOME优先级。实测{manifest['git_head']}。先保存真实失败反例，再修改；原TARE六核心函数体、所有实际参数、模型和融合不变。

## 实现了什么功能

同一周期BFS和候选图共用HT掩码，异步更新在下一周期切换；执行仍依据最新HT。原近家HOME目标不再被缺失的前视输出拦住，无放宽安全门槛或更换收益目标。

## 实验与验证

真实ROS图构造、异步更新、解除禁行、HOME无前视/原分支回归和原4项CTest通过；六函数SHA一致。车库完整600秒{summary['distance_m']:.2f}m/{m['observed_free_volume_m3']:.3f}m³，较40{pct40:+.1f}%、较39{pct39:+.1f}%。13项采集与视频完整解码通过；全数据、视频和历次图册随附。

## 存在什么问题

{issues} 单次轨迹不能证明某一边界修复导致体积变化；若本轮没有触发返航，只能说返航单元/分支回归通过。尚无同运动限制新原版配对、完整全局SE2可达或实车安全保证。
''')
summaryline=f"阶段41保持原TARE覆盖/TSP/航点顺序，修正HT掩码与BFS同步和近家HOME优先级。完整车库600秒{summary['distance_m']:.2f}m/{m['observed_free_volume_m3']:.3f}m³，较39{pct39:+.1f}%、较40{pct40:+.1f}%。{issues} [报告](docs/results/ht_tare_boundaries_10min_2026-10-20/REPORT.md) · [视频](docs/results/ht_tare_boundaries_10min_2026-10-20/garage/camera_h264.mp4) · [历次图册](docs/results/ht_tare_boundaries_10min_2026-10-20/history/index.html)。完整数据待本轮Release远端核验；不宣称追平原版。"
for filename in ['README.md','VERSIONS.md','docs/experiments/ITERATIONS.md','docs/experiments/NEXT_AUDIT.md']:
 p=root/filename;line=summaryline.replace('(docs/','(../') if filename.startswith('docs/') else summaryline;p.write_text('# 阶段41：原TARE决策与HT航点路由\n\n'+line+'\n\n---\n\n'+p.read_text())
print(json.dumps(dict(output=str(out),metrics=m,pct39=pct39,pct40=pct40,contract=contract),ensure_ascii=False,indent=2))
