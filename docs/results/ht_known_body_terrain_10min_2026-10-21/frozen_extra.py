"""Stage45 closed-loop comparison; all measurement sources remain unchanged."""
from pathlib import Path
import csv,hashlib,json,re,shutil,subprocess,sys
ROOT=Path.cwd();runtime=ROOT/'.git/terrain-gate-runtime'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
job=read(runtime/'job.json');suite=Path(job['suite']);out=Path(job['archive']);state=read(suite/'suite.json');new=suite/'indoor';old=ROOT/'docs/results/ht_sparse_height_4scene_10min_2026-10-21/indoor'
assert (out/'files_sha256.json').exists()
shutil.copy2(out/'REPORT.md',out/'COLLECTION_REPORT.md')
complete=(out/'indoor/timeseries.csv').exists() and (out/'indoor/observation_volume.csv').exists() and (new/'summary.json').exists()
if complete:subprocess.run([sys.executable,'presentations/plot_tare_route_comparison.py','--run','44 稀疏高程='+str(old),'--run','45 足迹反馈='+str(new),'--scene-label','同室内','--output',str(out/'comparison')],check=True)
tables=[];issues=[];details={}
for label,p in [('44 稀疏高程',old),('45 足迹反馈',new)]:
 a=read(p/'endurance_audit.json') if (p/'endurance_audit.json').exists() else {};s=a.get('summary',{});e=a.get('external_metrics') or {};mission=a.get('mission_audit',{}).get('last_sampled_mission','未知');age=a.get('sampled_map_age_s',{})
 def n(v,d=3):return f'{v:.{d}f}' if isinstance(v,(int,float)) else '未知'
 tables.append(f"| {label} | {n(s.get('duration_s'),1)} | {n(s.get('distance_m'),2)} | {n(e.get('observed_free_volume_m3'))} | {n(e.get('distance_last60_m'),2)} | {n(e.get('longest_zero_command_s'))} | {n(s.get('planner_runtime_p95_s'))} | {n(age.get('p95'))} | {mission} |")
 details[label]=dict(summary=s,external=e,mission=mission,map_age=age)
new_a=details['45 足迹反馈'];e=new_a['external'];s=new_a['summary'];mission=new_a['mission']
if not complete:issues.append('新记录未获得可比较的完整时序；不能称600s复测成功')
if mission=='BLOCKED':issues.append('室内末状态BLOCKED，仍有路线问题')
if e.get('longest_zero_command_s',0)>10:issues.append(f"最长完全停车{e['longest_zero_command_s']:.3f}s，结合任务状态判断")
if mission=='COMPLETED':issues.append('任务返航完成不等于全环境覆盖，须核查早退/真实覆盖')
issues += ['森林8000次展开上限与隧道53s结束线索本轮未复测，不能宣称已解决','单次600s不证明所有环境、长时运行或真实车辆稳定；无新增同限制原版TARE配对']
old_m=read(old/'manifest.json');new_m=read(new/'manifest.json')
changed=[p for p,h in new_m['source_hashes'].items() if old_m['source_hashes'].get(p)!=h]
write(out/'runtime_changes.json',dict(previous_commit=old_m['git_head'],tested_commit=job['candidate_commit'],changed_runtime_files=changed))
origin=read(new/'current/measurement_started.json')['wall_time'];hold_events=[]
for line in (new/'current/tare.log').read_text(errors='replace').splitlines():
 clock=re.search(r'\[(\d+\.\d+)\]',line);t=float(clock[1])-origin if clock else -1
 m=re.search(r'failed same-goal prefixes.*checked=(\d+) unsupported=(\d+).*searches=(\d+)',line)
 if m and 0<=t<=600:hold_events.append(dict(time_s=t,checked=int(m[1]),unsupported=int(m[2]),searches=int(m[3])))
write(out/'route_holds.json',dict(count=len(hold_events),zero_search_holds=sum(e['searches']==0 for e in hold_events),events=hold_events))
write(out/'remaining_issues.json',dict(issues=issues,scope='Observed issues and unverified scope; timer completion is not exploration success.'))
write(out/'comparison_metrics.json',details)
lines=['# 阶段45：已知障碍足迹反馈，室内600秒复测','',f"实测冻结提交`{job['candidate_commit']}`，基线为阶段44`{job['previous_candidate']}`。原TARE六函数/TSP/访问顺序、HT权重/预处理/0.5门槛、车体尺寸、搜索预算与运动上限保持。",'',
'## 原因与修改','',
'同快照的四个原分支终点中心分数约0.978～0.999，上层粗格允许，完整车体八方向却都BLOCKED。修正配置分数语义下的地形聚合与精确查询，并把无预测时新观测到的车体障碍写回历史；保留未知探索引导，实际路径仍严格拒绝未知。',
'[原因、反例与回归](../../fixes/2026-10-21_known_body_terrain.md) · [上一轮四场景及接口反例图](../ht_sparse_height_4scene_10min_2026-10-21/REPORT.md)。','',
'## 同场景实际比较','',
'| 版本 | 实测s | 里程m | 近似观测体积m³ | 末60s里程m | 最长完全停车s | 规划P95s | 地图年龄P95s | 末任务 |','|---|---:|---:|---:|---:|---:|---:|---:|---|',*tables,'']
if complete:lines += ['![体积、增量、里程、速度与运动组成](comparison/tare_architecture_comparison.png)','','![同尺度实际轨迹](comparison/tare_trajectories.png)','']
lines += ['高程和速度设置相同；每版本单次闭环，不保证统计优越或排除所有随机路径差异。体积为抽样激光自由空间体素并集近似，不是物理覆盖真值。','',
'## 实际路线和剩余问题','',*['- '+x for x in issues],'',f'本轮同目标前缀保持日志{len(hold_events)}周期，其中未进入搜索{sum(e["searches"]==0 for e in hold_events)}周期。终点允许不代表完整路径可达，原TARE粗图也不等于全局SE2可达保证。','',
'[运行文件变化](runtime_changes.json) · [全部分工/时间戳/模型输入审计](COLLECTION_REPORT.md)。四项最终CTest50.65s、六函数SHA通过；旧代码失败反例与中途补齐的缺测历史反例均保留。','',
'[视频](indoor/camera_h264.mp4) · [采集校验](indoor/suite_validation.json)','',
'![末段实际环境](indoor/late_camera.jpg)','','![末段HT硬门禁](indoor/late_ht_footprint.png)','','![实际TARE分支与HT路径](indoor/tare_waypoint_audit/routes.png)','',
'完整已录数据发布后以stage45.json逐资产远端大小/SHA回执为准。未验证原始数据不删除。']
(out/'REPORT.md').write_text('\n'.join(lines)+'\n')
for name in ['run.sh','post.sh','extra.py','publish.py']:
 source=runtime/name
 if source.exists():shutil.copy2(source,out/('frozen_'+name))
shutil.copy2(ROOT/'presentations/plot_tare_route_comparison.py',out/'plot_tare_route_comparison.py')
write(out/'files_sha256.json',{str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='files_sha256.json'})
print(json.dumps(dict(archive=str(out),issues=issues,metrics=details),ensure_ascii=False,indent=2))
