from pathlib import Path
import hashlib,json,shutil,yaml,subprocess
root=Path.cwd();raw=root/Path('/tmp/ht_prune39_run_path').read_text().strip();trial=raw/'garage';out=root/'docs/results/ht_successor_pruning_10min_2026-10-20';read=lambda p:json.loads(p.read_text());write=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
validation=read(trial/'suite_validation.json');assert all(validation['checks'].values())
for name in ['latency_audit','search_audit','execution_geometry_audit','cell_coverage_audit','scheduling_audit']:shutil.copytree(trial/name,out/name)
for name in ['blocked_commands.json','pose_admission_audit.json','final_pose_snapshot.npz','planner_parameters.yaml','follower_parameters.yaml','context_consistency.json','recovery_wins.json','stop_episodes.json','context_integrity.json','parameter_capture_attempts.json','source_age_alignment.json','scan_delivery_trace.json','guide_handoff_audit.json']:shutil.copy2(trial/name,out/'garage'/name)
scripts={n:Path('/tmp')/n for n in ['audit_ht_execution_geometry_scene.py','audit_ht_search_pruning.py','audit_ht_cell_coverage.py','audit_ht_recovery_wins.py','audit_ht_stop_episodes.py','audit_ht_context_integrity.py','archive_prune39_round.py','ht_prune39_postrun.sh','capture_prune39_parameters.py']}
scripts.update({n:root/'presentations'/n for n in ['audit_ht_context_dumps.py','audit_ht_search_scheduling.py','audit_ht_source_age_alignment.py','audit_ht_scan_delivery_trace.py','audit_ht_guide_handoff.py','plot_ht_guide_handoff.py']})
for name,source in scripts.items():shutil.copy2(source,out/name);shutil.copy2(source,trial/name)
manifest=read(trial/'manifest.json');external=trial/'frozen_external_sources';external.mkdir();index={}
for path,digest in manifest['source_hashes'].items():
 p=Path(path)
 if not p.is_relative_to(root) and p.suffix in ['.py','.yaml','.cpp','.world','.sdf']:
  data=p.read_bytes();assert hashlib.sha256(data).hexdigest()==digest
  name=f'{len(index):02}_'+p.name;(external/name).write_bytes(data);index[name]=dict(original_path=path,sha256=digest)
write(external/'index.json',index);shutil.copytree(external,out/'frozen_external_sources')
reference=root/'docs/results/ht_guide_handoff_10min_2026-10-19/garage';old=read(reference/'manifest.json');changed={p:dict(before=old['source_hashes'].get(p),after=h) for p,h in manifest['source_hashes'].items() if old['source_hashes'].get(p)!=h};assert {Path(p).name for p in changed}=={'tare_planner_node','xytheta_planner.h','ht_route.cpp'}
params={n:yaml.safe_load((reference/n).read_text())==yaml.safe_load((trial/n).read_text()) for n in ['planner_parameters.yaml','follower_parameters.yaml']};assert all(params.values())
config=dict(reference_commit=old['git_head'],candidate_commit=manifest['git_head'],effective_parameters_equal=params,changed_manifest_entries=changed,unchanged_entries=len(manifest['source_hashes'])-len(changed),scope='Same endpoint-key/cost dominance rule moved before costly validity checks; no fusion/model/controller/candidate/utility/key/control/sampling/threshold/budget changes. Accepted search edges still receive the original hard checks. Wall-time-limited trajectories can differ.')
write(out/'configuration_comparison.json',config);shutil.copy2(out/'configuration_comparison.json',trial/'configuration_comparison.json')
context=read(trial/'context_consistency.json');io=read(trial/'context_integrity.json');assert context['all_checks_passed'] and io['passed'];examples=out/'inference_examples';examples.mkdir()
for row in context['model_replays']:shutil.copy2(root/row['file'],examples/Path(row['file']).name)
shutil.copytree(root/'docs/fixes/evidence/2026-10-20_successor_pruning',out/'regression');shutil.copytree(root/'docs/fixes/evidence/2026-10-20_successor_pruning',trial/'regression')
(trial/'tested_source.patch').write_bytes(subprocess.check_output(['git','diff',old['git_head'],manifest['git_head'],'--','src/tare_planner']));shutil.copy2(trial/'tested_source.patch',out/'tested_source.patch')
analysis=(root/'docs/analysis/2026-10-20_tare_gap.md').read_text().replace('../results/tare_ht_pair_2026-10-16/REPORT.md','https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/tare_ht_pair_2026-10-16/REPORT.md');(out/'TARE_GAP_ANALYSIS.md').write_text(analysis);shutil.copy2(out/'TARE_GAP_ANALYSIS.md',trial/'TARE_GAP_ANALYSIS.md')
summary=read(trial/'summary.json');audit=read(trial/'endurance_audit.json');m=audit['external_metrics'];mission=read(trial/'mission_audit.json');search=read(trial/'search_audit/summary.json')['all'];geom=read(trial/'execution_geometry_audit/summary.json');blocked=read(trial/'blocked_commands.json');age=audit['sampled_map_age_s'];guide=read(trial/'guide_handoff_audit.json');plot=read(out/'comparison/plot_evidence.json');last60=plot[-1]['last60_gain_m3'];oldm=read(reference/'endurance_audit.json')['external_metrics'];pct=(m['observed_free_volume_m3']/oldm['observed_free_volume_m3']-1)*100
write(out/'EXPERIMENT.json',dict(tested_git_head=manifest['git_head'],raw_run=str(raw),recording_scope=manifest['evidence_policy'],metrics=m,mission=mission,search=search,geometry=geom,blocked_command_audit=blocked,checks=validation['checks'],video=validation['video'],configuration=config,context_integrity={k:v for k,v in io.items() if k!='files'},ht_map_age_s=age,guide_handoff={k:v for k,v in guide.items() if k not in ['switches','task_states']},efficiency=plot))
issues=f"体积较38{pct:+.1f}%，TIME_LIMIT {search['termination'].get('TIME_LIMIT',0)}次；单目标覆盖/直线引导结构未改，没有同控制约束的新原版TARE配对，不证明追平TARE"
p=root/'docs/version_history.json';versions=read(p);assert not any(s['number']==39 for s in versions['stages']);versions['stages'].append(dict(id='stage-39',number=39,sha=manifest['git_head'],tag='ht-stage-20261020-successor-pruning',title='XYθ支配边提前剪枝，减少注定丢弃的硬检查',kind='搜索开销优化与TARE差距分析',change='相同终点键/代价支配检查放到HT/几何检查前，接受边仍逐段硬验证；预算/候选/覆盖评分不变',features='冻结公开输入固定256展开查询减少约67%；18组合成实际成功路线代价/逐姿态相同。预算内4目标新旧仍均超时，保留反例',validation=f"完整车库600秒{summary['distance_m']:.2f}m/{m['observed_free_volume_m3']:.3f}m³，13项采集及4项CTest通过；剪枝{int(search['dominated_edges_pruned'])}条",known_issues=issues,evidence=['docs/results/ht_successor_pruning_10min_2026-10-20/REPORT.md'],control_commit=manifest['git_head'],ht_bridge_commit=versions['latest_ht_bridge_code']));versions['latest_planner_code']=manifest['git_head'];versions['latest_verified_trial_code']=manifest['git_head'];versions['latest_recorded_trial_code']=manifest['git_head'];versions['status']='阶段39完整600秒已测，搜索支配边剪枝；'+issues+'。全数据待本轮发布校验';write(p,versions)
oldsummary=read(reference/'summary.json');oldage=read(reference/'endurance_audit.json')['sampled_map_age_s'];oldsearch=read(reference.parent/'search_audit/summary.json')['all']
rows=[('近似观测自由体积m³',oldm['observed_free_volume_m3'],m['observed_free_volume_m3']),('实际里程m',oldsummary['distance_m'],summary['distance_m']),('末60秒新增m³',553.75,round(last60,3)),('末60秒里程m',round(oldm['distance_last60_m'],3),round(m['distance_last60_m'],3)),('原地转向占比',f"{oldm['stationary_turn_fraction']:.1%}",f"{m['stationary_turn_fraction']:.1%}"),('最长完全停车s',round(oldm['longest_zero_command_s'],3),round(m['longest_zero_command_s'],3)),('地图年龄P95s',round(oldage['p95'],3),round(age['p95'],3)),('搜索次数',oldsearch['count'],search['count']),('TIME_LIMIT次数',oldsearch['termination'].get('TIME_LIMIT',0),search['termination'].get('TIME_LIMIT',0)),('直接连接成功',oldsearch['direct_connections'],search['direct_connections'])]
rows.extend([('完全停车占比',f"{oldm['fully_stopped_fraction']:.2%}",f"{m['fully_stopped_fraction']:.2%}"),('最长无平移含转向s',round(oldm['longest_no_translation_command_s'],3),round(m['longest_no_translation_command_s'],3)),('地图年龄最大s',round(oldage['max'],3),round(age['max'],3)),('规划runtime P95s',oldsummary['planner_runtime_p95_s'],summary['planner_runtime_p95_s'])])
table='| 指标 | 阶段38 | 阶段39 |\n|---|---:|---:|\n'+''.join(f'| {k} | {a} | {b} |\n' for k,a,b in rows)
prefix=f'''# 阶段39：搜索开销优化，以及为什么当前HT仍落后于TARE

**同车库完整600秒：{summary['distance_m']:.2f}米、{m['observed_free_volume_m3']:.3f}m³，体积较38为{pct:+.1f}%。** 末尾任务{mission['last_sampled_mission']}，完整记录到点停止不代表探索完成。

## 先回答“为什么远不及TARE”

[详细代码与数据分析](TARE_GAP_ANALYSIS.md)：HT开启时绕过原局部TSP，只输出到单个目标的XYθ路线，以单点收益/到达时间做选择；多视点覆盖序列、视点间收益重叠和全局进出端衔接没有完整保留。全局引导多处用到终点的直线距离，而非沿拓扑绕行路线的剩余距离。必要绕行和长远覆盖收益容易吃亏。这是代码中已明确的结构差异，尚未消融量化贡献，不能把全部差距归为它或计算慢。

历史180秒原版/旧HT自由体积6242.625/3224.625m³（51.7%）不是当前版本准确比率。当时前进上限都0.5m/s，原版倒车/角速度/加速度却更宽松。当前还缺完全同运动约束的新原版600秒配对，不能冒充已经验证的公平比较。

本轮只优化搜索开销，**没有修改上述覆盖目标与全局引导结构**，不宣称一次剪枝就追平原版。阶段38的306/394条节流输出日志gain=0，结合平台期须核对中转是否真实推进；不能简单禁止必要零收益通行。

## 改了什么，什么证据支持

原搜索先做逐段HT/几何检查，最后才丢弃终点键已有更便宜/相等路线的边。本轮提前执行完全相同的终点键/代价比较；可能进入队列的边仍按原顺序逐段通过全部硬检查。没有跨地图缓存、量化碰撞位置、放宽未知或增加预算。

固定公开输入4个目标、各256次展开：查询约11700→3800（约减少67%），终止/展开相同；它们都是未到达结果，不把空路线相同作为成功路线证明。另18组合成障碍/方向patch/直连开关回归，真实成功路线代价与逐姿态完全相同。反例保留：4目标在.075/.15秒预算下新旧24次仍全TIME_LIMIT，计算更省不代表目标有路。[根因与回归范围](../../fixes/2026-10-20_successor_pruning.md)。

实测`{manifest['git_head'][:7]}`，65项冻结条目只规划头文件、调用日志及规划二进制3项改变，其他62项相同；全部实际参数一致。[配置逐项对照](configuration_comparison.json) · [实际代码差异](tested_source.patch)。

## 同场景比较：改善与退步一起保留

![累计、每分钟新增、轨迹、引导和运动组成](comparison/pruning_comparison.png)

{table}

本轮累计提前剪去{int(search['dominated_edges_pruned'])}条支配边；这不是放过未检查的可接受路线。不同轮次目标/轨迹不同，超时次数与查询总数并非同一工作量微基准，应结合冻结输入结果看。仍有搜索超时、回访、目标选择和独立物理覆盖真值问题。{issues}。

两轮同车库、近似同起点、前进上限0.5m/s、相同HT/几何/运动限制；源秒激光{m['processed_volume_scans']}帧、跳过{m['skipped_volume_scans']}，0.5m自由体素并集近似，不是物理真值覆盖率。每版本一轮闭环，输入调度/随机采样和路线分支均可能影响结果，不能据此宣称单项因果收益或统计稳定。

## 验证、视频和全部数据

13/13采集核验、4项CTest通过；视频{validation['video']['decoded_frames']}帧/{validation['video']['duration_s']:.6f}秒完整解码。{io['completed_npz_files']}份最终上下文/历史图CRC通过，无损坏/partial；{context['checked_contexts']}份同源保存样本与三模型重算通过。记录几何采样及晚拦截见[审计](garage/blocked_commands.json)，采样不是连续物理安全证明。

[完整600秒视频](garage/camera_h264.mp4) · [本轮Release完整数据与SHA256](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261020-successor-pruning) · [历次多角度图册](history/index.html) · [合并PDF](history/all_comparisons.pdf)。发布完成以仓库stage39.json远端SHA256/大小校验回执为准；源秒激光和周期地图不是所有原始传感器无损录制。GitHub保留全部，本机校验后只留最近两轮完整录包，图文视频和回归样本保留。

![三轮累计曲线、速度与轨迹](comparison/comparison.png)

![搜索耗时与终止原因](search_audit/searches.png)

![模块时延](latency_audit/latency.png)

![末段实际HT硬门槛](garage/late_ht_footprint.png)

## 后续优先级

恢复多视点覆盖收益与全局拓扑接力，把XYθ可执行路线成本/可达性用于覆盖任务排序。先做有界候选/分段连接，避免全部视点两两完整Hybrid A*。在相同角速度、倒车、加速度条件下补原版对照，再分离多视点/单点、拓扑/欧氏引导、HT误拒与计算预算的贡献。暂时无路不能核销成已覆盖，不能为了好看体积直接放宽硬门槛。

---

'''
(out/'REPORT.md').write_text(prefix+(out/'REPORT.md').read_text());print(json.dumps(dict(output=str(out),metrics=m,search=search,pct=pct),ensure_ascii=False,indent=2))
