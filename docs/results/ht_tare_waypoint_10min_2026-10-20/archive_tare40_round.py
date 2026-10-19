from pathlib import Path
import hashlib,json,shutil,csv,yaml,subprocess
import numpy as np
root=Path.cwd();raw=root/Path('/tmp/ht_tare40_run_path').read_text().strip();trial=raw/'garage';out=root/'docs/results/ht_tare_waypoint_10min_2026-10-20'
read=lambda p:json.loads(p.read_text());write=lambda p,j:p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
validation=read(trial/'suite_validation.json');assert all(validation['checks'].values())
for name in ['latency_audit','execution_geometry_audit','tare_waypoint_audit']:shutil.copytree(trial/name,out/name)
for name in ['blocked_commands.json','pose_admission_audit.json','final_pose_snapshot.npz','planner_parameters.yaml','follower_parameters.yaml','context_consistency.json','stop_episodes.json','context_integrity.json','parameter_capture_attempts.json','source_age_alignment.json','scan_delivery_trace.json','terrain_topic_isolation.json']:shutil.copy2(trial/name,out/'garage'/name)
for name in ['audit_ht_execution_geometry_scene.py','audit_ht_stop_episodes.py','audit_ht_context_integrity.py','archive_tare40_round.py','ht_tare40_postrun.sh','capture_tare40_parameters.py','capture_tare40_isolation.py']:
 p=Path('/tmp')/name;shutil.copy2(p,out/name);shutil.copy2(p,trial/name)
for name in ['audit_tare_waypoint.py','audit_ht_context_dumps.py','audit_ht_source_age_alignment.py','audit_ht_scan_delivery_trace.py']:
 shutil.copy2(root/'presentations'/name,out/name);shutil.copy2(root/'presentations'/name,trial/name)
manifest=read(trial/'manifest.json');reference=root/'docs/results/ht_successor_pruning_10min_2026-10-20/garage';old_manifest=read(reference/'manifest.json')
external=trial/'frozen_external_sources';external.mkdir();index={}
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
  data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest
  dest=source/p.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
shutil.copytree(root/'docs/fixes/evidence/2026-10-20_tare_waypoint',out/'upstream_and_regression')
subprocess.run(['git','diff',old_manifest['git_head'],manifest['git_head'],'--','src/tare_planner','tools/ht_cupy_bridge','presentations/run_scheduled_comparison.py','presentations/run_ht_endurance.py'],stdout=(out/'tested_source.patch').open('w'),check=True)
parameters={}
for name in ['planner_parameters.yaml','follower_parameters.yaml']:
 a=yaml.safe_load((reference/name).read_text());b=yaml.safe_load((trial/name).read_text());node=next(iter(b));a=a[node]['ros__parameters'];b=b[node]['ros__parameters'];parameters[name]={k:dict(before=a.get(k),after=b.get(k)) for k in sorted(a.keys()|b.keys()) if a.get(k)!=b.get(k)}
config=dict(reference_commit=old_manifest['git_head'],candidate_commit=manifest['git_head'],parameter_changes=parameters,
 source_changes={p:dict(before=old_manifest['source_hashes'].get(p),after=h) for p,h in manifest['source_hashes'].items() if old_manifest['source_hashes'].get(p)!=h},
 note='Architecture/terrain input change. Same motion limits and garage scenario; do not claim a single isolated micro-optimization.')
write(out/'configuration_comparison.json',config)
summary=read(trial/'summary.json');audit=read(trial/'endurance_audit.json');m=audit['external_metrics'];age=audit['sampled_map_age_s'];mission=read(trial/'mission_audit.json');contract=read(trial/'tare_waypoint_audit/summary.json');geom=read(trial/'execution_geometry_audit/summary.json');blocked=read(trial/'blocked_commands.json');io=read(trial/'context_integrity.json');ctx=read(trial/'context_consistency.json');isolation=read(trial/'terrain_topic_isolation.json')
assert isolation['/terrain_map']['publishers']==[] and isolation['/terrain_map_ext']['publishers']==[]
assert 'tare_planner_node' not in isolation['/simulation/terrain_map']['subscribers']
with (trial/'current/observation_volume.csv').open() as f:volume=list(csv.DictReader(f))
gain=m['observed_free_volume_m3']-float(np.interp(540,[float(v['time_s']) for v in volume],[float(v['observed_free_volume_m3']) for v in volume]))
old=read(reference/'endurance_audit.json');oldm=old['external_metrics'];olds=read(reference/'summary.json');pct=(m['observed_free_volume_m3']/oldm['observed_free_volume_m3']-1)*100
issues=f"XYθ搜索超时{contract['search_termination'].get('TIME_LIMIT',0)}次；最长完全停车{m['longest_zero_command_s']:.2f}s，末60秒新增{gain:.3f}m³/移动{m['distance_last60_m']:.2f}m；末尾{mission['last_sampled_mission']}。"
write(out/'EXPERIMENT.json',dict(tested_git_head=manifest['git_head'],raw_run=str(raw),recording_scope=manifest['evidence_policy'],metrics=m,mission=mission,tare_waypoint=contract,geometry=geom,blocked_command_audit=blocked,checks=validation['checks'],video=validation['video'],configuration=config,context_integrity=io,ht_map_age_s=age,last60_gain_m3=gain))
rows=[('累计近似观测自由体积m³',oldm['observed_free_volume_m3'],m['observed_free_volume_m3']),('实际里程m',olds['distance_m'],summary['distance_m']),('末60秒里程m',oldm['distance_last60_m'],m['distance_last60_m']),('完全停车比例',f"{oldm['fully_stopped_fraction']:.2%}",f"{m['fully_stopped_fraction']:.2%}"),('原地转向比例',f"{oldm['stationary_turn_fraction']:.2%}",f"{m['stationary_turn_fraction']:.2%}"),('最长完全停车s',round(oldm['longest_zero_command_s'],3),round(m['longest_zero_command_s'],3)),('最长无平移s（含转向）',round(oldm['longest_no_translation_command_s'],3),round(m['longest_no_translation_command_s'],3)),('地图年龄P95s',round(old['sampled_map_age_s']['p95'],3),round(age['p95'],3)),('地图年龄最大s',round(old['sampled_map_age_s']['max'],3),round(age['max'],3)),('整体规划P95s',olds['planner_runtime_p95_s'],summary['planner_runtime_p95_s'])]
table='| 指标 | 阶段39：HT自选目标 | 阶段40：原TARE顺序+HT |\n|---|---:|---:|\n'+''.join(f'| {k} | {a} | {b} |\n' for k,a,b in rows)
report=f'''# 阶段40：原版TARE决定访问顺序，HT负责航点路由

**完整车库600秒：{summary['distance_m']:.2f}米，近似累计观测自由体积{m['observed_free_volume_m3']:.3f}m³，较阶段39为{pct:+.1f}%。** {issues}这是单次闭环结果，不是统计优越性或探索完成真值。

## 按用户要求改了什么

[先行计划](../../plans/2026-10-20_tare_ht_waypoint_plan.md)先于实现提交。代码`{manifest['git_head']}`：默认`tare_waypoint`，恢复原版局部覆盖、局部TSP、全局任务更新、全局TSP、路径拼接和前视点选择。六个核心函数体与独立ROS2适配原版参考`b6760ad`逐字SHA一致，[核对结果](upstream_and_regression/regression/ht_tare40_upstream_contract.json)。不是说整个ROS2包与官方ROS1仓库逐字相同。

TARE使用自己的完整视点序列、采样/收益去重、路径长度目标和TSP求解器；HT不再通过单点收益/时间、指南冷却和目标承诺改写访问目标。原版航点延伸也保留。过远航点沿TARE路线分支取局部前缀，再用XYθ找从当前odom过去的可执行路径。HT找路失败发零，不改选其他收益点。所有执行轨迹仍经原运动学约束、HT硬门槛、点云几何和控制拦截，速度限制未提高。

地形高度来自CuPy/HT同源历史高程，第12层`ht_elevation`与八方向图坐标/时间一致；墙顶不作地面。粗视点只需存在可通方向，执行仍逐段检查实际方向。远端未观测位置只用于原TARE乐观引导，不授权开进未知地形。CMU地形仅在`/simulation/terrain_map`供车辆模拟器贴地，TARE原地形输入话题无发布者，[现场话题核对](garage/terrain_topic_isolation.json)。

## 接口是否真的按这个分工运行

{contract['coverage_cycles']}个覆盖周期记录原TSP，实际调用次数分布{contract['tsp_calls']}。最大完整访问序列{contract['maximum_ordered_viewpoints']}个索引，平均{contract['mean_ordered_viewpoints']:.2f}个；原版最多10次优化，但已有覆盖/空队列时走原版单次分支，不能说每周期必算10次。录包保留完整顺序、覆盖路线、原版航点、HT局部目标和实际执行路线。

{contract['moving_waypoints']}个允许移动的航点与最近原TARE航点相同，{contract['local_goals']}个局部目标核对是否位于对应分支；审计违例{len(contract['contract_violations'])}，总体接口检查{contract['contract_passed']}。消息级检查不等于连续安全或实际逐视点到访证明。[审计数据](tare_waypoint_audit/summary.json)

![多视点TSP、规划次数、实际轨迹与搜索状态](tare_waypoint_audit/architecture.png)

![完整TARE序列、选中分支、航点与HT路线](tare_waypoint_audit/routes.png)

灰线是TARE未来访问路线，橙线是当前分支，蓝线是实际发布的HT路线XY投影，星号是原TARE延伸航点；它们不是已经走过的轨迹。

## 同车库对比，改善和退步一起保留

{table}

![阶段36/38/39/40累计体积、里程、速度、轨迹](comparison/comparison.png)

同场景近似同起点、前进0.5m/s和相同转向/倒车/加速度限制。具体参数和变动源码见[冻结配置对照](configuration_comparison.json)与[代码差异](tested_source.patch)。地形输入、目标组织、路线分支都改变，所以本轮不是单项算力消融。原始TARE历史角速度/倒车/加速度更宽松，尚未补齐完全同约束的新600秒原版配对，不能把本轮体积比当成已追平原版。

## 仍存在什么问题

{issues} 搜索预算失败不等于地形绝对不可通；硬约束也可能因地图误差拒绝真实平地。完整序列恢复不保证每个TARE航点在当前局部HT图中可达。没有全方向历史HT缓存或全局SE2可达性保证，局部有效窗口仍约9.87m见方；粗历史高度/可行性用于引导，执行用新鲜局部HT。尚未验证无限时长、其他环境、轮胎动力学和实车。

执行日志中的拦截非零配对{blocked['blocked_nonzero_count']}，未配对{blocked['unmatched_command_rejections']}；几何拦截非零{blocked['geometry_nonzero_count']}，几何未配对{blocked['unmatched_geometry_rejections']}。几何采样余量重叠{geom['overlap_samples']}/{geom['samples']}，旧指令外推碰余量{geom['moving_predictions_inside_margin']}条；采样和外推不是连续物理接触真值，单列证据不隐藏。[几何审计](execution_geometry_audit/summary.json)

## 验证、图册和完整数据

13项采集检查全部通过，4项CTest及新增桥接检查通过；视频{validation['video']['decoded_frames']}帧/{validation['video']['duration_s']:.6f}秒完整解码。{io['completed_npz_files']}份最终上下文和历史图CRC通过：{io['passed']}；{ctx['checked_contexts']}份输入上下文核对与模型重算通过：{ctx['all_checks_passed']}。

源秒激光{m['processed_volume_scans']}帧、跳过{m['skipped_volume_scans']}，0.5m自由体素并集是近似观测量，不是物理覆盖真值。MCAP含全部发布HT/控制/状态/odom、按源秒保留激光、周期地图及精确HT输入输出，不是所有原始传感器无损录制。

[完整600秒视频](garage/camera_h264.mp4) · [历次多角度图册](history/index.html) · [PDF](history/all_comparisons.pdf) · [GitHub完整数据Release](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261020-tare-waypoint)。完整发布以仓库`docs/experiments/publications/stage40.json`远端大小/SHA256回执为准。GitHub保留全部，本机仅保留最近两轮已核验完整原始数据。

![本轮时延](latency_audit/latency.png)

![结束附近实际八方向HT硬门槛](garage/late_ht_footprint.png)
'''
(out/'REPORT.md').write_text(report)
v=read(root/'docs/version_history.json');assert not any(s['number']==40 for s in v['stages'])
stage=dict(id='stage-40',number=40,sha=manifest['git_head'],tag='ht-stage-20261020-tare-waypoint',title='原TARE覆盖/TSP访问顺序 + HT航点XYθ路由',kind='恢复原探索架构，替换地形与局部执行',change='六个核心函数体与原ROS2基线一致，保留多视点TSP与原航点延伸；HT只规划当前航点/原路线前缀',features='同源历史高程供视点高度；隔离模拟器地形；记录TSP顺序、原航点、局部前缀与实际XYθ路线',validation=f"完整车库600秒{summary['distance_m']:.2f}m/{m['observed_free_volume_m3']:.3f}m³；13项采集、4项CTest；接口检查{contract['contract_passed']}",known_issues=issues+' 单次运行；未补齐同运动约束新原版配对；不保证全局SE2可达或实车安全',evidence=[str((out/'REPORT.md').relative_to(root))],control_commit=manifest['git_head'],ht_bridge_commit=manifest['git_head'])
v['stages'].append(stage);v['updated_at']='2026-10-20';v['latest_planner_change']=manifest['git_head'];v['latest_planner_code']=manifest['git_head'];v['latest_ht_bridge_code']=manifest['git_head'];v['latest_verified_trial_code']=manifest['git_head'];v['latest_recorded_trial_code']=manifest['git_head'];v['status']='阶段40原TARE覆盖/TSP+HT航点路由600秒完成，数据待发布核验；'+issues;write(root/'docs/version_history.json',v)
notes=f'''## 改了什么

恢复原TARE六个核心函数体与多视点TSP，HT只处理odom到原航点的XYθ路线；保留原航点延伸，同源历史高程替代导航地形。先行计划e2370b0，实测{manifest['git_head']}。

## 实现了什么功能

TARE访问顺序/原航点/原路线分支/局部目标/实际执行轨迹分别录包。仿真地形输入隔离，原TARE地形话题无发布者。HT无路发零，不替换收益目标。

## 实验与验证

车库完整600秒{summary['distance_m']:.2f}m、{m['observed_free_volume_m3']:.3f}m³，较39体积{pct:+.1f}%。13项采集、4项CTest，视频完整解码；原六函数SHA一致，接口违例{len(contract['contract_violations'])}。报告、数据、视频和历次多角度图册随附；raw.tar分卷包含本轮全部已录数据，采样传感器范围以报告为准。

## 存在什么问题

{issues} 单次闭环不证明一般优越；没有同运动约束的新原版600秒配对。局部HT/几何采样不是连续安全或独立物理覆盖真值，尚未完成多环境和实车验收。
'''
(root/'docs/release_notes/ht-stage-20261020-tare-waypoint.md').write_text(notes)
summaryline=f"阶段40已按先行计划恢复原TARE多视点覆盖/TSP，HT只路由当前航点。完整车库600秒{summary['distance_m']:.2f}m/{m['observed_free_volume_m3']:.3f}m³，较39体积{pct:+.1f}%。{issues} [报告](docs/results/ht_tare_waypoint_10min_2026-10-20/REPORT.md)，[视频](docs/results/ht_tare_waypoint_10min_2026-10-20/garage/camera_h264.mp4)，[历次图册](docs/results/ht_tare_waypoint_10min_2026-10-20/history/index.html)。全原始数据待Release远端校验；不宣称追平原版。"
for filename,relative in [('README.md',False),('VERSIONS.md',False),('docs/experiments/ITERATIONS.md',True),('docs/experiments/NEXT_AUDIT.md',True)]:
 p=root/filename;line=summaryline.replace('(docs/','(../') if relative else summaryline
 p.write_text('# 阶段40：原TARE顺序与HT路由\n\n'+line+'\n\n---\n\n'+p.read_text())
print(json.dumps(dict(output=str(out),tested=manifest['git_head'],volume_pct_vs39=pct,metrics=m,contract=contract),ensure_ascii=False,indent=2))
