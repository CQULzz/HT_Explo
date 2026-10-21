"""Readonly stage44 analysis after all frozen measurements; do not alter old archives."""
from pathlib import Path
import collections,csv,hashlib,json,re,shutil,subprocess,sys,tempfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'presentations'))
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def rows(p):return list(csv.DictReader(p.open()))
job=read(ROOT/'.git/indoor-input-runtime/job.json');suite=Path(job['suite']);out=Path(job['archive']);state=read(suite/'suite.json')
assert (suite/'FINISHED.json').exists() and (out/'files_sha256.json').exists()
# Visualization-only correction after measurement: six version bars must fit
# within one minute bin, rather than overlap the adjacent minute's cluster.
plotter=ROOT/'presentations/plot_tare_route_comparison.py'
text=plotter.read_text()
old_bar="marginal=np.diff(np.interp(minute,r['vt'],r['v']));axes[0,1].bar(np.arange(1,11)+(i-(len(data)-1)/2)*.24,marginal,width=.23,color=c,label=r['label'])"
new_bar="marginal=np.diff(np.interp(minute,r['vt'],r['v']));bar_width=min(.24,.8/len(data));axes[0,1].bar(np.arange(1,11)+(i-(len(data)-1)/2)*bar_width,marginal,width=bar_width*.95,color=c,label=r['label'])"
if old_bar in text:plotter.write_text(text.replace(old_bar,new_bar))
elif new_bar not in text:raise RuntimeError('Unexpected comparison plot source; refuse blind editing')
specs=[]
for label,path in [('39 HT自选目标','ht_successor_pruning_10min_2026-10-20'),('40 恢复原TARE','ht_tare_waypoint_10min_2026-10-20'),('41 接口修正','ht_tare_boundaries_10min_2026-10-20'),('42 同版本车库复测','ht_tare_native_5scene_10min_2026-10-20'),('43 短前缀补搜','ht_tare_short_prefix_10min_2026-10-21')]:
 folder=ROOT/'docs/results'/path/'garage'
 if (folder/'summary.json').exists() and (folder/'endurance_audit.json').exists():specs += ['--run',label+'='+str(folder)]
specs += ['--run','44 稀疏高程降噪='+str(suite/'garage')]
if (suite/'garage/summary.json').exists():subprocess.run([sys.executable,str(plotter),*specs,'--output',str(out/'garage_history')],check=True)
shutil.copy2(plotter,out/'plot_tare_route_comparison.py')
plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
# Exact saved-frame counterexample, independent of historical cache reconstruction.
from matplotlib.patches import Circle,Patch
import cv2
proof=read(ROOT/'.git/indoor-input-runtime/coarse_footprint_counterexample.json')
with np.load(proof['snapshot_file']) as d:
 cx,cy,res=d['ht_geometry'];n,m=d['ht_ht_valid'].shape;extent=(cx-n*res/2,cx+n*res/2,cy-m*res/2,cy+m*res/2)
 P=np.array([d[f'ht_ht_dir_{k}'] for k in range(8)]);best=np.max(np.where(np.isfinite(P),P,-np.inf),axis=0);best=np.where(d['ht_ht_valid']>=.5,best,np.nan)
 radius=int(np.ceil(.6/res))+1;gx,gy=np.mgrid[-radius:radius+1,-radius:radius+1];kernel=(np.hypot(gx*res,gy*res)<=.6+np.sqrt(2)*res).astype(np.uint8)
 blocked=cv2.dilate((d['ht_ht_obstacle']>=.5).astype(np.uint8),kernel);unknown=cv2.dilate((d['ht_ht_observation_valid']<.5).astype(np.uint8),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=1)
 from matplotlib.colors import ListedColormap
 physical=np.where(blocked,2,np.where(unknown,1,0));fig,axes=plt.subplots(1,2,figsize=(13,6),layout='constrained')
 cm=plt.get_cmap('RdYlGn').copy();cm.set_bad('#bfc3c6')
 im=axes[0].imshow(best[::-1,::-1].T,origin='lower',extent=extent,cmap=cm,vmin=0,vmax=1,interpolation='nearest');fig.colorbar(im,ax=axes[0],label='maxθ P')
 axes[1].imshow(physical[::-1,::-1].T,origin='lower',extent=extent,cmap=ListedColormap(['#75bc87','#bfc3c6','#c93335']),vmin=0,vmax=2,interpolation='nearest')
 for ax in axes:
  ax.scatter(*d['robot'][:2],marker='+',s=100,c='#1765ce',label='车体当前位置')
  for v in proof['results']:
   ax.scatter(*v['xy'],s=40,c='black');ax.annotate(str(int(v['prefix_m']))+'m',v['xy'],xytext=(8,0),textcoords='offset points');ax.add_patch(Circle(v['xy'],.6,fill=False,color='black',lw=.8))
  ax.set(xlabel='X / m',ylabel='Y / m');ax.set_aspect('equal')
 axes[0].set_title('中心点高分，上层当前粗格也判可行');axes[1].set_title('0.6m物理足迹门禁：四个终点八方向均BLOCKED')
 axes[1].legend(handles=[Patch(color='#75bc87',label='物理足迹允许（尚未叠HT方向分数）'),Patch(color='#bfc3c6',label='足迹包含未知'),Patch(color='#c93335',label='足迹包含障碍')],fontsize=7)
 fig.suptitle('室内末段同一真实快照：上层地形允许与执行门禁不一致\n圆仅表示既有0.6m足迹，不是新增膨胀或放行结果')
 for ext in ['png','pdf']:fig.savefig(out/('terrain_gate_mismatch.'+ext),dpi=155)
 plt.close(fig)
# Re-evaluate the stopped old recording in a temporary view; never touch its
# already-published raw source or invent the absent final30.5seconds.
old=ROOT/'presentations/scheduled_results/ht_tare_native_5scene_10min_2026-10-20_19-39-37/indoor'
comparison=out/'indoor_history';comparison.mkdir(exist_ok=False)
old_rows=rows(old/'current/timeseries.csv');common_duration=float(old_rows[-1]['t_s'])
origin=read(old/'current/measurement_started.json')['wall_time']
import summarize_tare_ht_pair as common
original_reader=common.reader
def sampled_reader(path,topics):return original_reader(path,['/endurance/registered_scan' if t=='/registered_scan' else t for t in topics])
common.reader=sampled_reader
with tempfile.TemporaryDirectory(prefix='ht-partial-indoor-analysis-') as temporary:
 p=Path(temporary);(p/'current').mkdir()
 for name in ['timeseries.csv','measurement_started.json']:shutil.copy2(old/'current'/name,p/'current'/name)
 (p/'current_bag').symlink_to(old/'evidence_bag',target_is_directory=True)
 _,_,external=common.evaluate(p,'current',common_duration,scan_selection='source_second')
 shutil.copy2(p/'current/observation_volume.csv',comparison/'stage42_partial_observation_volume.csv')
 shutil.copy2(p/'current/external_metrics.json',comparison/'stage42_partial_external_metrics.json')
shutil.copy2(old/'current/timeseries.csv',comparison/'stage42_partial_timeseries.csv')
# Plot old partial only over its actual available interval, candidate over600s.
fig,axes=plt.subplots(2,2,figsize=(14,10),layout='constrained')
for label,m,v,color in [('42旧室内（中断记录）',old_rows,rows(comparison/'stage42_partial_observation_volume.csv'),'#ba5153'),('44稀疏高程候选',rows(out/'indoor/timeseries.csv'),rows(out/'indoor/observation_volume.csv'),'#148c8e')]:
 t=np.array([float(x['t_s']) for x in m]);d=np.array([float(x['distance_m']) for x in m]);vt=[float(x['time_s']) for x in v];vv=[float(x['observed_free_volume_m3']) for x in v]
 axes[0,0].plot(t,d,label=label,c=color);axes[0,1].plot(vt,vv,label=label,c=color)
 axes[1,0].plot([float(x['x_m']) for x in m],[float(x['y_m']) for x in m],label=label,c=color)
 axes[1,1].plot(t,[float(x['planner_runtime_s']) for x in m],label=label,c=color,alpha=.7)
for ax,title,xlabel,ylabel in [(axes[0,0],'累计实际里程','时间 / s','m'),(axes[0,1],'同口径累计观测自由空间','时间 / s','近似体积 / m³'),(axes[1,0],'实际车辆轨迹','X / m','Y / m'),(axes[1,1],'规划耗时（周期采样）','时间 / s','s')]:
 ax.set(title=title,xlabel=xlabel,ylabel=ylabel);ax.legend();ax.grid(alpha=.2)
axes[1,0].set_aspect('equal',adjustable='datalim')
fig.suptitle(f'同室内原生起点/0.5m/s上限：旧记录仅到{common_duration:.3f}s，不补齐600s\n原TARE架构；旧42→44也包含43短前缀改动，单次闭环不是隔离因果或真值覆盖证明')
for ext in ['png','pdf']:fig.savefig(comparison/('indoor_comparison.'+ext),dpi=150)
plt.close(fig)
old_first_finished=next((float(r['t_s']) for r in old_rows if r['finished']=='1'),None)
new_rows=rows(out/'indoor/timeseries.csv');new_at_common=float(np.interp(common_duration,[float(r['t_s']) for r in new_rows],[float(r['distance_m']) for r in new_rows]))
write(comparison/'comparison_scope.json',dict(old_source=str(old),old_git_head=read(old/'manifest.json')['git_head'],candidate=job['candidate_commit'],old_available_motion_end_s=common_duration,old_first_finished_sample_s=old_first_finished,old_distance_m=float(old_rows[-1]['distance_m']),candidate_distance_at_same_time_m=new_at_common,old_observation_volume_m3=external['observed_free_volume_m3'],scope='Old capture was interrupted, no600s completion assertion. Source archive unchanged; metric derived separately with existing source-second algorithm. Single runs; stage43 prefix change is another difference from stage42.'))
# Preserve per-scene failures and actual adaptive-prefix use, not just end status.
issues=[];evidence={};table=[]
for row in state['runs']:
 scene=row['scenario'];trial=suite/scene;a=read(trial/'endurance_audit.json') if (trial/'endurance_audit.json').exists() else {};s=a.get('summary',{});e=a.get('external_metrics') or {};mission=a.get('mission_audit',{}).get('last_sampled_mission','未知');age=a.get('sampled_map_age_s',{})
 logs=(trial/'current/tare.log').read_text(errors='replace') if (trial/'current/tare.log').exists() else ''
 start=read(trial/'current/measurement_started.json')['wall_time'] if (trial/'current/measurement_started.json').exists() else 0
 events=[];holds=[]
 for line in logs.splitlines():
  clock=re.search(r'\[(\d+\.\d+)\]',line);t=float(clock[1])-start if clock else -1
  if not 0<=t<=600:continue
  m=re.search(r'TARE_ROUTE .*prefix=([\d.]+).*poses=(\d+) success=(\d+) adaptive=(\d+) distance=([\d.]+)',line)
  if m:events.append(dict(time_s=t,prefix_m=float(m[1]),poses=int(m[2]),success=int(m[3]),adaptive=int(m[4])))
  m=re.search(r'failed same-goal prefixes.*checked=(\d+) unsupported=(\d+).*searches=(\d+)',line)
  if m:holds.append(dict(time_s=t,checked=int(m[1]),unsupported=int(m[2]),searches=int(m[3])))
 evidence[scene]=dict(adaptive_attempts=sum(v['adaptive'] for v in events),adaptive_successes=sum(v['adaptive'] and v['success'] for v in events),route_hold_cycles=len(holds),zero_search_holds=sum(h['searches']==0 for h in holds),events=events,holds=holds)
 if mission=='BLOCKED':issues.append(scene+'末状态BLOCKED，不能称探索成功')
 route=read(trial/'tare_waypoint_audit/summary.json') if (trial/'tare_waypoint_audit/summary.json').exists() else {}
 if mission=='BLOCKED' and route.get('search_termination',{}).get('EXPANSION_LIMIT',0):issues.append(scene+f"记录中{route['search_termination']['EXPANSION_LIMIT']}次XYθ搜索达到展开上限，不能据此断言无路")
 if e.get('longest_zero_command_s',0)>10:issues.append(scene+f"最长完全停车{e['longest_zero_command_s']:.2f}s，需结合任务/门禁解释")
 if row['state']!='RECORDED':issues.append(scene+'采集未通过全部检查：'+row['state'])
 motion_file=trial/'current/timeseries.csv'
 if mission=='COMPLETED' and motion_file.exists():
  finished=next((float(r['t_s']) for r in rows(motion_file) if r['finished']=='1'),None)
  issues.append(scene+f'在{finished}s采样报告exploration_finished，是否真实全覆盖尚未验证；COMPLETED只表示任务返航条件满足')
 def n(v,d=3):return f'{v:.{d}f}' if isinstance(v,(int,float)) else '未知'
 table.append(f"| {scene} | {row['state']} | {n(s.get('duration_s'),1)} | {n(s.get('distance_m'),2)} | {n(e.get('observed_free_volume_m3'))} | {n(e.get('distance_last60_m'),2)} | {n(e.get('longest_zero_command_s'))} | {n(s.get('planner_runtime_p95_s'))} | {n(age.get('p95'))} | {mission} |")
write(out/'prefix_usage.json',evidence);write(out/'remaining_issues.json',dict(issues=issues,scope='Observed issues only; no universal stability or task-completion proof.'))
lines=['# 阶段44：稀疏高程修正，四场景各600秒','',f"实测冻结提交 `{job['candidate_commit']}`；导航C++沿用 `{job['navigation_control_commit']}`。修改和回归见[修正说明](../../fixes/2026-10-21_sparse_height.md)。保留原TARE六函数/TSP、HT权重/归一化/0.5硬门槛及运动上限。",'',
'## 实际结果','', '| 场景 | 采集 | 秒 | 里程m | 近似观测体积m³ | 末60s里程m | 最长完全停车s | 规划P95s | 地图年龄P95s | 末任务状态 |','|---|---|---:|---:|---:|---:|---:|---:|---:|---|',*table,'',
f'旧室内记录实际仅到{common_duration:.3f}s，首个finished=1采样{old_first_finished}s，里程{float(old_rows[-1]["distance_m"]):.3f}m；新候选在相同时刻里程{new_at_common:.3f}m。旧记录不补成600s；新旧单次轨迹并非单项因果隔离。',
'','![室内旧故障与新候选对照](indoor_history/indoor_comparison.png)','','[同口径与中断边界](indoor_history/comparison_scope.json)。观测量是抽样激光自由空间体素并集，不是全局真实覆盖率。','',
'![同车库历次变化](garage_history/tare_architecture_comparison.png)','','![同尺度车库轨迹](garage_history/tare_trajectories.png)','','![四场景运行诊断](multiscene_diagnostics.png)','',
'## 仍然存在的问题','',*['- '+v for v in (issues or ['本轮未观测到上述阻塞，但单次实验不能证明没有其他缺陷。'])],'',
'![同快照上层与执行门禁反例](terrain_gate_mismatch.png)','','四个真实分支终点中心最大P约0.978～0.999，当前0.2m粗格均存在允许中心；完整车体门禁八方向均BLOCKED。见[frozen_coarse_footprint_counterexample.json](frozen_coarse_footprint_counterexample.json)。这是当前快照的接口反例，不冒称重建了全部历史缓存或证明有一条绕行路线。','',
'在线日志表明室内末段同分支终点预筛拒绝、未进入XYθ搜索；森林则进入搜索并反复达到展开上限，两者不是同一种退出原因。准确门禁类别见prefix_admissibility_audit。室内代表测试位置的足迹碰到障碍格，见frozen_blocked_obstacle_samples.json；这些测试位置不是对全部179个真实端点的复现。不能用地图旧或CPU慢笼统解释。原TARE粗视点图与完整SE2可达性并不等价。新滤波不保证辨认所有低置信厘米孤立物；原训练噪声分布未知。','',
'## 图、视频与逐项证据','']
for row in state['runs']:
 scene=row['scenario'];lines += [f'### {scene}','',f'[完整10分钟视频]({scene}/camera_h264.mp4) · [采集检查]({scene}/suite_validation.json) · [路线分工]({scene}/tare_waypoint_audit/summary.json)','',f'![实际环境]({scene}/late_camera.jpg)','',f'![末段HT硬门禁]({scene}/late_ht_footprint.png)','',f'![实际TARE分支与HT路径]({scene}/tare_waypoint_audit/routes.png)','']
lines += ['没有新原版TARE同限制配对和实车验证，不拿跨场景体积排名。完整数据/视频以stage44.json远端大小与SHA回执为准；报告存在不代表已上传。原始测量与失败记录保留。[通用采集/审计明细](COLLECTION_REPORT.md)。']
shutil.copy2(out/'REPORT.md',out/'COLLECTION_REPORT.md');(out/'REPORT.md').write_text('\n'.join(lines)+'\n')
shutil.copy2(__file__,out/'finalize_extra.py')
for name in ['run.sh','post.sh','finish.sh','publish.py','blocked_obstacle_samples.json','coarse_footprint_counterexample.json']:
 source=ROOT/'.git/indoor-input-runtime'/name
 if source.is_file():shutil.copy2(source,out/('frozen_'+name))
hashes={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='files_sha256.json'};write(out/'files_sha256.json',hashes)
print(json.dumps(dict(archive=str(out),issues=issues,indoor_same_time_distance_m=new_at_common),ensure_ascii=False,indent=2))
