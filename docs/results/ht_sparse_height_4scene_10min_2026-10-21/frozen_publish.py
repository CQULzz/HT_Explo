"""Publish stage44 after sealed measurement and all extra analyses; immutable tag."""
from pathlib import Path
import datetime,fcntl,json,subprocess
ROOT=Path.cwd();runtime=ROOT/'.git/indoor-input-runtime'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def command(args):subprocess.run(args,cwd=ROOT,check=True)
def commit(paths,message):
 command(['git','add','--',*paths])
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
  command(['git','-c','user.name=Codex','-c','user.email=codex@local','commit','-m',message])
 command(['git','push','origin','HEAD:codex/ht8dir-v1'])
job=read(runtime/'job.json');suite=Path(job['suite']);out=Path(job['archive']);tag=job['tag'];candidate=job['candidate_commit'];stage=job['stage']
assert stage==44 and (out/'remaining_issues.json').exists() and (suite/'FINISHED.json').exists()
if subprocess.check_output(['systemctl','--user','show','ht-sparse-height-4scene.service','-p','MainPID','--value'],text=True).strip()!='0':raise RuntimeError('Measurements still active')
state=read(suite/'suite.json');assert state['git_head']==candidate
issues=read(out/'remaining_issues.json')['issues'];receipt=ROOT/'docs/experiments/publications/stage44.json';notes=ROOT/'docs/release_notes'/(tag+'.md');report=str(out.relative_to(ROOT)/'REPORT.md')
rows=[];good=True
for row in state['runs']:
 scene=row['scenario'];trial=suite/scene;metrics=row.get('metrics',{});summary=read(trial/'summary.json') if (trial/'summary.json').exists() else {};checks=read(trial/'suite_validation.json')['checks'] if (trial/'suite_validation.json').exists() else {}
 valid=summary.get('duration_s')==600 and (trial/'COMPLETED.json').exists() and row['state']=='RECORDED' and bool(checks) and all(checks.values());good &= valid
 rows.append(f"| {scene} | {row['state']} | {summary.get('duration_s','未知')} | {metrics.get('distance_m','未知')} | {metrics.get('observed_free_volume_m3','未知')} | {metrics.get('mission','未知')} |")
local=subprocess.run(['git','rev-parse','--verify','refs/tags/'+tag],capture_output=True,text=True)
if local.returncode:command(['git','tag',tag,candidate])
elif subprocess.check_output(['git','rev-parse',tag+'^{commit}'],text=True).strip()!=candidate:raise RuntimeError('Refuse moving measured tag')
command(['git','push','origin','refs/tags/'+tag])
notes_body='\n'.join(['# 阶段44：稀疏高程纹理修正与四场景600秒验证','',
'## 改了什么','',
'允许至少两对对称真实观测邻居有限去噪，保护连贯小台阶/窄柱，保留方差权重、最多2cm调整与原未知/障碍门槛。启动及首次TARE运行各45s逐帧保留推理与前端输入以捕获早停；原TARE六函数/TSP、HT权重/归一化/0.5阈值、速度和导航C++未改。','',
'## 实现了什么功能','','原TARE决定访问顺序，HT为指定航点提供硬门禁下的XYθ路线；多环境记录与输入诊断可追溯。','','## 实验与验证','',f'实测冻结提交`{candidate}`。69项桥接回归与源数据录制检查、六函数SHA、10项中断/归档回归通过；同一个后续输入重放部分平地分数提高，精确旧触发帧未保存，离线分数变化不等于车辆可达。',
'','| 场景 | 采集 | 实测s | 里程m | 近似观测体积m³ | 末任务 |','|---|---|---:|---:|---:|---|',*rows,'',
f'[报告、图、视频和审计](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/{report})。室内旧中断记录只比较实际569.501s，车库保留历次完整600s对照，不补齐缺失或把跨场景体积排名。完整MCAP/上下文等以本Release附件及stage44.json大小/SHA校验为准；非全频原始传感器无损录制。','',
'## 存在什么问题','',*['- '+v for v in (issues or ['本轮未复现不证明绝对无缺陷。'])],'',
'粗视点地形可行性不等于完整SE2可达性；未知训练噪声分布与低置信厘米孤立物辨识仍有限制。单次轨迹不隔离所有随机因素；无新增同限制原版TARE配对、完整动力学或实车验证。'])+'\n'
with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:raise RuntimeError('Unrelated staged changes')
 notes.write_text(notes_body);v=read(ROOT/'docs/version_history.json')
 prior=next((s for s in v['stages'] if s['number']==44),None)
 if prior and prior['sha']!=candidate:raise RuntimeError('Stage44 refers to another measured candidate')
 entry=dict(id='stage-44',number=44,sha=candidate,tag=tag,title='稀疏高程纹理修正与四场景600秒实测',kind='高程输入修正及多环境验证',change='对称已观测邻域有限滤波与小特征保护；扩充准确输入诊断，不改模型或原TSP',features='多帧高程供HT；原TARE访问顺序、XYθ路由和硬门禁保持',validation='; '.join(r['scenario']+'='+r['state']+':'+str(r.get('metrics',{})) for r in state['runs']),known_issues='；'.join(issues+['无新原版同限制配对/训练分布未知/粗图不保证完整SE2/无实车']),evidence=[report])
 v['stages']=[s for s in v['stages'] if s['number']!=44]+[entry];v['latest_recorded_trial_code']=candidate;v['latest_ht_bridge_code']=candidate;v['status']='阶段44四场景实际结果已记录，完整数据正在上传；问题见逐组报告';v['updated_at']=datetime.datetime.now().astimezone().isoformat();write(ROOT/'docs/version_history.json',v)
 intro=f'# 阶段44：稀疏高程修正与四场景测试\n\n[结果、比较图和视频]({report}) · [完整数据](https://github.com/CQULzz/HT_Explo/releases/tag/{tag})。采集成功不等于探索成功，剩余阻塞见报告；完整发布以stage44.json回执为准。\n\n'
 for filename in ['README.md','VERSIONS.md']:
  p=ROOT/filename;text=p.read_text()
  if not text.startswith('# 阶段44'):p.write_text(intro+'## 前一轮记录\n\n'+text)
 h=ROOT/'HANDOFF.txt';head='2026-10-21阶段44实测补记：冻结'+candidate+'；四场景采集已结束、结果见'+report+'。完整数据正在发布，stage44.json核验后才称备份完成；剩余问题：'+'；'.join(issues)+'。\n\n';previous=h.read_text()
 if head not in previous:h.write_text(previous.replace('HT_Explo 项目交接文档\n','HT_Explo 项目交接文档\n'+head,1))
 command(['python3','scripts/publish_version_notes.py','--dry-run'])
 commit(['README.md','VERSIONS.md','HANDOFF.txt','docs/version_history.json','presentations/plot_tare_route_comparison.py',str(notes.relative_to(ROOT)),str(out.relative_to(ROOT))],'Record sparse-height four-scene results with preserved blocking failures and comparisons')
args=['python3','scripts/publish_streamed_ht_trial.py','--suite',str(suite),'--archive',str(out),'--tag',tag,'--title','阶段44｜稀疏高程修正与四场景600秒验证','--notes',str(notes),'--receipt',str(receipt)]
if not good or state['state']!='COMPLETED':args.append('--include-failed-recordings')
command(args)
with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 v=read(ROOT/'docs/version_history.json');v['status']='阶段44全部已录数据已发布并核验；探索阻塞等剩余问题见报告';v['latest_verified_trial_code']=candidate;write(ROOT/'docs/version_history.json',v)
 write(ROOT/'docs/experiments/LAST_COMPLETED_STAGE44.json',dict(stage=44,tested_commit=candidate,release='https://github.com/CQULzz/HT_Explo/releases/tag/'+tag,remote_verified=True,raw_suite=str(suite),result_archive=str(out),collection_state=state['state'],all_recordings_validated=good))
 if good and state['state']=='COMPLETED':command(['python3','scripts/prune_published_ht_raw.py','--keep','2','--apply'])
 h=ROOT/'HANDOFF.txt';h.write_text(h.read_text().replace('HT_Explo 项目交接文档\n','HT_Explo 项目交接文档\n阶段44完整远端发布已核验，见docs/experiments/publications/stage44.json；测量/分析均结束，剩余问题照实保留，不自动改下一候选。\n\n',1))
 commit(['docs/experiments','docs/version_history.json','HANDOFF.txt'],'Verify all stage44 recorded data and video assets; retain partial captures')
print('COMPLETE stage44 remote size and SHA verified',flush=True)
