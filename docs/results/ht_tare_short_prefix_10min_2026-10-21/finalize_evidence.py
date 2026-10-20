import json,hashlib,re,shutil,subprocess
from pathlib import Path
ROOT=Path.cwd();job=json.loads((ROOT/'.git/short-prefix-runtime/job.json').read_text());suite=Path(job['suite']);out=Path(job['archive']);trial=suite/'garage';prior=Path(job['previous_suite'])/'garage'
def read(p):return json.loads(p.read_text())
def run(args):subprocess.run(args,check=True)
state=read(suite/'suite.json')
if state['state']!='COMPLETED' or not all(r.get('state')=='RECORDED' and all(r.get('checks',{}).values()) for r in state['runs']):raise RuntimeError('Keep failed evidence; no successful600s assertion')
run(['python3','presentations/audit_tare_waypoint.py',str(trial),'--output',str(trial/'tare_waypoint_audit')])
run(['python3','presentations/archive_ht_multiscene.py',str(suite),'--scenarios','garage','--output',str(out)])
shutil.copytree(trial/'tare_waypoint_audit',out/'tare_waypoint_audit')
for name in ['planner_parameters.yaml','follower_parameters.yaml','parameter_capture_attempts.json','terrain_topic_isolation.json']:
 if (trial/name).exists():shutil.copy2(trial/name,out/'garage'/name)
run(['python3','presentations/plot_tare_route_comparison.py','--run','41 接口修正='+str(ROOT/'docs/results/ht_tare_boundaries_10min_2026-10-20/garage'),'--run','42 同版本复测='+str(prior),'--run','43 短前缀补搜='+str(trial),'--output',str(out/'comparison')])
origin=read(trial/'current/measurement_started.json')['wall_time'];events=[];holds=[]
for line in (trial/'current/tare.log').read_text(errors='replace').splitlines():
 clock=re.search(r'\[(\d+\.\d+)\]',line);t=float(clock[1])-origin if clock else -1
 if not 0<=t<=600:continue
 m=re.search(r'TARE_ROUTE .*prefix=([\d.]+).*poses=(\d+) success=(\d+) adaptive=(\d+) distance=([\d.]+)',line)
 if m:events.append(dict(time_s=t,prefix_m=float(m[1]),poses=int(m[2]),success=int(m[3]),adaptive=int(m[4]),distance_m=float(m[5])))
 if 'failed same-goal prefixes' in line:holds.append(dict(time_s=t,log=line))
usage=dict(events=events,adaptive_attempts=sum(e['adaptive'] for e in events),adaptive_successes=sum(e['adaptive'] and e['success'] for e in events),short_successes=sum(e['adaptive'] and e['success'] and e['prefix_m']<1 for e in events),route_hold_cycles=len(holds),holds=holds)
(out/'adaptive_usage.json').write_text(json.dumps(usage,ensure_ascii=False,indent=2)+'\n')
old=read(prior/'endurance_audit.json');new=read(trial/'endurance_audit.json');routing=read(trial/'tare_waypoint_audit/summary.json');nm=read(trial/'manifest.json');om=read(prior/'manifest.json')
changes=[p for p,h in nm['source_hashes'].items() if om['source_hashes'].get(p)!=h]
(out/'runtime_changes.json').write_text(json.dumps(dict(previous_tested_commit=om['git_head'],tested_commit=nm['git_head'],changed_runtime_files=changes),ensure_ascii=False,indent=2)+'\n')
lines=['# 阶段43：原TARE路线短前缀补搜，车库600秒','',f"实测代码 `{job['candidate_commit']}`。保持原TARE六函数/TSP/waypoint、HT硬阈值和运动限制。新旧初始位姿接近但并不完全相同；每候选单次闭环，不能保证统计优越或单项因果。",'',
'## 原因和修改','',
'旧车库末段22周期固定1/2/3/4米终点全部不允许，没有进入XYθ搜索；同一TARE分支短于1米处仍有支持。保留快速路径，失败后细采样同分支短前缀，避开后方锚点，仍用完整HT/几何/运动检查和原0.35秒周期搜索预算。没有换收益点、提高速度或放行未知。',
'[计划](../../plans/2026-10-21_tare_ht_short_prefix_plan.md) · [根因及回归](../../fixes/2026-10-21_tare_short_prefix.md) · [室内问题诊断](../../fixes/2026-10-21_indoor_ht_gate.md)。','',
'## 同场景实际结果','',
'| 版本 | 实测秒 | 里程m | 近似自由体积m³ | 末60秒里程m | 完全停车 | 原地转向 | 最长完全停车s | 规划P95s | 地图年龄P95s | 末状态 |',
'|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
stage41=read(ROOT/'docs/results/ht_tare_boundaries_10min_2026-10-20/garage/endurance_audit.json')
for label,d in [('41接口修正',stage41),('42同导航复测',old),('43短前缀补搜',new)]:
 e=d['external_metrics'];s=d['summary'];m=d['mission_audit'];age=d['sampled_map_age_s']
 lines.append(f"| {label} | {s['duration_s']} | {s['distance_m']:.2f} | {e['observed_free_volume_m3']:.3f} | {e['distance_last60_m']:.2f} | {100*e['fully_stopped_fraction']:.2f}% | {100*e['stationary_turn_fraction']:.2f}% | {e['longest_zero_command_s']:.3f} | {s['planner_runtime_p95_s']:.3f} | {age['p95']:.3f} | {m['last_sampled_mission']} |")
delta=new['external_metrics']['observed_free_volume_m3']-old['external_metrics']['observed_free_volume_m3']
exercise=('本轮新增补搜没有触发，不能用本轮体积变化证明补搜收益；针对性回归验证了固定终点漏搜的修正。' if not usage['adaptive_attempts'] else '本轮实际补搜是否解除停滞须结合逐次事件后的运动与增量，不能把终点允许当作可行路径。')
lines+=['',f'相对42体积变化{delta:+.3f}m³。采样激光自由空间并集不是物理真值；不能把里程大等同于探索好。',exercise,'',
'![累计体积、每分钟增量、里程、速度和运动组成](comparison/tare_architecture_comparison.png)','',
'![同尺度实际轨迹](comparison/tare_trajectories.png)','',
'## 实际补搜与剩余问题','',
f"新增补搜尝试{usage['adaptive_attempts']}次，成功{usage['adaptive_successes']}次，其中短于1米成功{usage['short_successes']}次；路由保持停车日志{usage['route_hold_cycles']}周期。[逐次摘要](adaptive_usage.json)。原TARE→HT分工检查{routing['contract_passed']}，记录级违例{len(routing['contract_violations'])}；记录审计不是连续物理安全或全局可达性证明。",'',
'![原TARE访问顺序与HT路由](tare_waypoint_audit/architecture.png)','',
'![实际分支与XYθ路线投影](tare_waypoint_audit/routes.png)','',
'![末段HT硬门槛](garage/late_ht_footprint.png)','',
'![末段实际相机](garage/late_camera.jpg)','',
'四项CTest、六原函数SHA、10项记录流程回归通过。完整采集13项检查和视频验证见[本轮校验](garage/suite_validation.json)。[视频](garage/camera_h264.mp4) · [运行文件差异](runtime_changes.json)。',
'时间/展开预算失败、短步推进和地图噪声仍需看真实记录。室内12个低分点切断走廊的问题尚未在线修复；没有新增同限制原版TARE对照或实车试验。','',
'完整已录文件上传Release后以stage43.json回执为准；本地报告与视频不代表原始数据已上传，未验证资料不删除。']
(out/'REPORT.md').write_text('\n'.join(lines)+'\n')
shutil.copy2(__file__,out/'finalize_evidence.py')
hashes={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='files_sha256.json'}
(out/'files_sha256.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(archive=str(out),metrics=state['runs'][0]['metrics'],adaptive={k:v for k,v in usage.items() if k not in ('events','holds')},contract=routing['contract_passed']),ensure_ascii=False,indent=2))
