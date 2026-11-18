from pathlib import Path
import ast, csv, gzip, hashlib, json, re, shutil
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Rectangle

root=Path('/home/lzz/ht_window_recovery_20261118')
work=Path('/mnt/d/HT-Window-Recovery-20261118')
repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes')
dest=repo/'validation/window_recovery_20261118'
dest.mkdir(exist_ok=True)
for name in ['source','logs','fixture']:(dest/name).mkdir(exist_ok=True)
(dest/'.gitattributes').write_text('* -text\n*.log -whitespace\n*.csv -whitespace\n')
for name in ['CONTEXT_WINDOWS.json','FIXTURE.json','baseline.log','baseline_trace.csv','long_search.log','short_diagnostic.log','candidate_probe.log','candidate_trace.csv','ctest.log']:
 shutil.copy2(root/'analysis'/name,dest/name)
for name in ['build_candidate.log','build_final_test.log','build_candidate_probe.log']:
 shutil.copy2(root/'setup'/name,dest/'logs'/name)
for path in work.glob('*'):
 if path.is_file() and path.suffix in ['.py','.cpp']:(dest/'source'/path.name).write_text(path.read_text(encoding='utf-8-sig').rstrip()+'\n')
for name in ['env.sh','build_candidate.sh','probe_candidate.sh','finish_checks.sh']:
 shutil.copy2(root/name,dest/'source'/name)
raw=root/'analysis/campus_stop.cdr'
with gzip.GzipFile(filename=str(dest/'fixture/campus_stop.cdr.gz'),mode='wb',mtime=0) as out:out.write(raw.read_bytes())
assert gzip.decompress((dest/'fixture/campus_stop.cdr.gz').read_bytes())==raw.read_bytes()

def trace(name):
 rows=list(csv.DictReader((dest/name).open()))
 return {k:np.array([float(row[k]) for row in rows]) for k in ['elapsed_s','x','y','yaw','v','w']}
b=trace('baseline_trace.csv');c=trace('candidate_trace.csv');goal=np.array([.172499999,0])
dist=lambda v:float(np.hypot(v['x'][-1]-v['x'][0],v['y'][-1]-v['y'][0]))
progress=lambda v:float(np.hypot(v['x'][0]-goal[0],v['y'][0]-goal[1])-np.hypot(v['x'][-1]-goal[0],v['y'][-1]-goal[1]))
windows=json.loads((dest/'CONTEXT_WINDOWS.json').read_text());cell=windows[1]['uncertain_cells'][0]['xy']
baseline_report=(dest/'baseline.log').read_text();candidate_report=(dest/'candidate_probe.log').read_text()
assert 'active_seen=0 completed=0 moving_ticks=0' in baseline_report
assert 'active_seen=1 completed=1' in candidate_report and 'invalidated=0' in candidate_report
assert progress(c)>=.25
checks={'scope':'Frozen recorded map counterfactual, unicycle execution at200Hz, fixed gate query source_age=.4s. Not live ROS/Gazebo exploration or new sensor evidence.',
 'baseline':{'net_displacement_m':dist(b),'net_goal_progress_m':progress(b),'finish_flag':True,'recovery_completed':False},
 'candidate':{'net_displacement_m':dist(c),'net_goal_progress_m':progress(c),'finish_flag':True,'recovery_completed':True,'fixture_elapsed_to_completion_s':float(c['elapsed_s'][-1]),'all_nonzero_commands_checked_by_gate':True,'invalidated':0},
 'gate':{'min_probability':.5,'source_age_s':.4,'timeout_s':1.,'support_radius_m':.58182230175,'body_min_xyz':[-.4649301,-.3497950000007719,-.2351843],'body_max_xyz':[.4649308,.34979500000080593,.6502000536441803]},
 'tests':{'ctest_groups_passed':4,'ctest_groups_failed':0,'raw_map_sha256':hashlib.sha256(raw.read_bytes()).hexdigest(),'interior_window_queries_matched_recorded_masks':4,'outer_context_guard_checked':True}}
(dest/'VALIDATION.json').write_text(json.dumps(checks,indent=2))

old=repo/'validation/campus_repeat_1200s_20261118';m=json.loads((old/'data/MAP_SNAPSHOTS.json').read_text())['snapshots'][-1];a=np.load(old/'data/ht_map_last.npz');res=m['resolution_m'];cx,cy,_=m['center_xyz'];size=m['rows']*res
fig,axes=plt.subplots(1,2,figsize=(12,5));ax=axes[0]
ax.imshow((a['ht_valid']>=.5).T[::-1,::-1],extent=[cx-size/2,cx+size/2,cy-size/2,cy+size/2],origin='lower',cmap=ListedColormap(['#e5e7eb','#b8d7cc']),interpolation='nearest')
query=windows[1]['query_xy'];width=51*res
ax.add_patch(Rectangle((query[0]-width/2,query[1]-width/2),width,width,fill=False,edgecolor='#d97706',label='Rejected 51x51 context'))
ax.scatter(*cell,marker='x',s=75,c='#dc2626',label='One uncertain cell (old height expired)')
ax.plot(c['x'],c['y'],c='#087f75',linewidth=3,label='Checked recovery prefix')
ax.scatter(c['x'][0],c['y'][0],c='black',s=28,label='Recorded stopped base')
ax.scatter(c['x'][-1],c['y'][-1],c='#087f75',s=25)
ax.set(xlim=(-5.,-1.4),ylim=(-3.2,-.2),xlabel='World X (m)',ylabel='World Y (m)',title='Recorded context mask and checked prefix');ax.set_aspect('equal');ax.legend(fontsize=8,loc='upper left')
ax=axes[1];ax.plot(c['elapsed_s'],c['v'],label='Candidate linear m/s');ax.plot(c['elapsed_s'],c['w'],label='Candidate angular rad/s');ax.plot([0,c['elapsed_s'][-1]],[0,0],'--',label='Baseline zero output');ax.set(xlabel='Fixture simulated time (s)',ylabel='Command',title=f'Frozen-map goal progress: {progress(c):.3f} m');ax.legend(fontsize=8);ax.grid(alpha=.2)
fig.tight_layout();fig.savefig(dest/'context_recovery.png',dpi=160);plt.close(fig)

sources=['CMakeLists.txt','src/ht_gate.hpp','src/ht_recovery.hpp','src/ht_recovery_return_test.cpp']
frozen={}
for name in sources:
 original=repo/'src/cmu_local_planner_ht'/name;candidate=root/'candidate/src/cmu_local_planner_ht'/name
 assert original.read_bytes()==candidate.read_bytes(),name
 frozen['source/'+name]=hashlib.sha256(original.read_bytes()).hexdigest()
for name in ['localPlanner','pathFollower']:
 p=root/'candidate/install/cmu_local_planner_ht/lib/cmu_local_planner_ht'/name;frozen['binary/'+name]=hashlib.sha256(p.read_bytes()).hexdigest()
(dest/'RUNTIME.json').write_text(json.dumps({'navigation_install':str(root/'candidate/install'),'navigation_source':str(root/'candidate/src/cmu_local_planner_ht'),'base_commit':'65a0ee46806c43d26c3f9a13347594ef6c651f98','frozen':frozen,'next_run_environment_order':['source /home/lzz/ht_campus_repeat_1200s_20261118/env.sh','source /home/lzz/ht_window_recovery_20261118/candidate/install/setup.bash'],'limitations':'Compiled offline candidate. Historical runtime installations and previous20min evidence are unchanged; next test must explicitly source candidate/install last. No new Gazebo run or formal budget consumed.'},indent=2))

report=f'''# HT窗口边界与返航恢复修复（2026-11-18）

已修复两个执行层问题：探索完成信号禁用了未完成的返航恢复；旧恢复搜索坚持至少0.75m目标进展，丢弃了较短但能够安全执行的前缀。原始20分钟终点地图上的冻结对照，旧版保持零输出，新版完成一个恢复前缀，净目标进展{progress(c):.6f}m、净位移{dist(c):.6f}m；所有非零命令通过原门禁。**这是停车现场的离线执行验证，不是新的20分钟探索、完整返航或实车验收。**

## 原图窗口和历史格证据

重建原记录ht_map_last.npz的4个内侧51×51窗口，全部与记录的ht_valid一致。起始base格上下文有效；朝目标0.5/0.75/1m的查询窗口近已知支撑比例均为100%，但含同一个不确定格[88,126]，世界位置({cell[0]:.6f},{cell[1]:.6f})，触发uncertain窗口否决。它不是“整个窗口90%支撑不足”。

结束时历史归档保留该格高程-0.250265m，最后接受时间1794988005.662311；相对最后记录图已老化1194.568995秒，超过历史600秒期限，无更新的接受模式或拒绝高度。源码将已过期的留存高度视为未知，不能由附近的近邻填充重新变成真实可通过地面。该格的未知状态又否决了周围约2.09m的神经窗口。已确认本次终点这个格的过期证据，未重建每一帧原始源图和方差；不能将它套到所有历史停车事件。

tools/cmu_minimal/analyze_context_window.py从已记录的measured/physical/obstacle掩码重建该判据，只适用于ht_qualify_evidence=false的完整内侧窗口。靠近边缘、缺少原输入外25格时会报错，不猜测外部数据。JSON及原始图索引见CONTEXT_WINDOWS.json、上一轮data/MAP_SNAPSHOTS.json。

## 修改行为

- ht_recovery.hpp不再把exploration_finish当作禁用条件。只要仍有未到达的有效目标，原生输出持续零/拒绝0.4秒，恢复就能尝试；暂停、零速度上限、里程计时效及HT门禁继续检查。到达保留目标后报告RETURN_GOAL_REACHED，不重新启动恢复；未修改TARE目标和完成消息。
- 搜索优先原进展目标。受窗口边界/计算预算限制而无法找到原前缀时，允许已有搜索树中至少0.25m净目标进展的前缀；近目标时不低于原请求进展。先试最佳进展节点，若其轨迹或控制器仿真不通过，再试第一个合格前缀。纯转向、退离目标、任意微小进展不能以此接管。每个结果仍完整检查路径、车体扫掠、HT分数/上下文/未知/障碍、制动包络和控制器仿真，在线每条输出再检查。不是把坏HT格改成好格。
- 诊断新增探索阶段、目标距离、完整/部分进展、搜索节点数/退出原因、各拒绝原因的首个失败位置及计数。Gate只增加最后查询位置记录，判定逻辑不变；HT桥、阈值、600秒历史期限、起点标签策略和全局TARE未改。

![原始无效窗口与实际可执行前缀](context_recovery.png)

## 验证与构建

Humble独立Release构建成功，4组CTest全部通过（ht_gate/ht_execution/ht_urdf_box/ht_recovery_return）。新增回归用真实ROS /exploration_finish订阅触发phase标志，检查允许零命令时仍能恢复、目标到达不重启、短窗口前缀、微小进展拒绝、上下文/缺测/障碍/低分/地图过期/里程计过期拒绝、暂停及零速度上限。已有执行/URDF包络回归继续通过。

| 冻结终点图对照 | 旧版 | 修复版 |
|---|---:|---:|
| exploration_finish | true | true |
| 接管并完成一个恢复前缀 | 否 | 是 |
| 非零控制tick数 | 0 | 123 |
| 净目标进展m | 0 | {progress(c):.6f} |
| 净位移m | 0 | {dist(c):.6f} |
| 恢复执行失效次数 | 0 | 0 |

两组原始CDR输入完全相同（fixture/FIXTURE摘要见FIXTURE.json）；URDF约0.930×0.700m、支撑半径0.581822302m、分数门限0.5、图龄期限1秒、0.1秒反应和原制动加速度一致。固定查询图龄0.4秒用于隔离静态地图执行，200Hz车体积分；**没有把这个冻结时钟用到真实导航，也没有续写旧图时间戳。** 新版在冻结时钟内约{c['elapsed_s'][-1]:.3f}秒完成这个前缀。搜索扩展预算仍20ms，记录约21ms包含额外路径和控制器校验，不是整个回调严格20ms保证。

旧版另做过诊断：临时将搜索上限放宽至2000ms仍无原0.75m结果；临时改进展目标为0.25m且关闭完成禁用则能执行约0.264m。它们仅用于区分失效链，不是保留配置。修复版保持20ms、原0.75m优先目标及finish=true；以受检短前缀解决两条件共同造成的零输出。日志原样保留，VALIDATION.json列明口径。

独立源码、两个导航可执行文件的SHA及下一轮环境顺序见RUNTIME.json。已编译安装在/home/lzz/ht_window_recovery_20261118/candidate/install；原实验安装和旧录包没有被覆盖。下一次使用时必须最后source该候选安装，不能继续误用ht_initial_labels_20261116的旧二进制。精简证据Windows副本D:/HT-Window-Recovery-20261118/results。

## 尚未验收的部分

前缀完成不等于整条返航完成。冻结地图不会产生新观测；前缀后的扫描能否补齐过期格、能否持续绕过所有HT缺口，需要新的闭环测试。没有以局部恢复成功宣称全campus覆盖通过，也没有修改全局完成判据。旧实验的非有限航点、非法JSON源以及SIGINT子进程退出问题仍未在本次修复范围内解决。

原始数据和所有旧账本继续保留。本轮没有新正式Gazebo仿真、没有重置旧20分钟账本、没有Release或实车部署。源码及精简报告推送原fix/ht-execution-20261113分支。
'''
(dest/'REPORT_zh.md').write_text(report)
for p in dest.rglob('*.json'):json.loads(p.read_text())
for p in dest.rglob('*.py'):ast.parse(p.read_text())
files=[{'file':str(p.relative_to(dest)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(dest.rglob('*')) if p.is_file() and p.name!='DELIVERY_MANIFEST.json']
(dest/'DELIVERY_MANIFEST.json').write_text(json.dumps({'files':files,'total_bytes':sum(p['bytes'] for p in files)},indent=2))
shutil.copytree(dest,work/'results',dirs_exist_ok=True)
print(json.dumps({'files':len(files),'bytes':sum(p['bytes'] for p in files),'validation':checks},indent=2))
