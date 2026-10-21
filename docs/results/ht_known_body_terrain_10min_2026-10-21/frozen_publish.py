"""Publish only sealed stage45 evidence; tags and raw sources remain immutable."""
from pathlib import Path
import datetime,fcntl,json,subprocess
ROOT=Path.cwd();runtime=ROOT/'.git/terrain-gate-runtime'
def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def command(a):subprocess.run(a,cwd=ROOT,check=True)
def commit(paths,message):
 command(['git','add','--',*paths])
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:command(['git','-c','user.name=Codex','-c','user.email=codex@local','commit','-m',message])
 command(['git','push','origin','HEAD:codex/ht8dir-v1'])
job=read(runtime/'job.json');suite=Path(job['suite']);out=Path(job['archive']);candidate=job['candidate_commit'];tag=job['tag']
if subprocess.check_output(['systemctl','--user','show','ht-terrain-gate-10min.service','-p','MainPID','--value'],text=True).strip()!='0':raise RuntimeError('Measurement active')
assert (out/'files_sha256.json').exists() and (out/'remaining_issues.json').exists()
state=read(suite/'suite.json');assert state['git_head']==candidate
if subprocess.check_output(['git','rev-parse',tag+'^{commit}'],text=True).strip()!=candidate:raise RuntimeError('Wrong measured tag')
command(['git','push','origin','refs/tags/'+tag])
issues=read(out/'remaining_issues.json')['issues'];notes=ROOT/'docs/release_notes'/(tag+'.md');report=str(out.relative_to(ROOT)/'REPORT.md');row=state['runs'][0];metrics=row.get('metrics',{})
summary=read(suite/'indoor/summary.json') if (suite/'indoor/summary.json').exists() else {};checks=read(suite/'indoor/suite_validation.json')['checks'] if (suite/'indoor/suite_validation.json').exists() else {}
good=state['state']=='COMPLETED' and row['state']=='RECORDED' and summary.get('duration_s')==600 and bool(checks) and all(checks.values())
comparison=read(out/'comparison_metrics.json')
body='\n'.join(['# 阶段45：已知障碍足迹反馈与室内复测','',
'## 改了什么','',
'把既有车体已知障碍门禁反馈给原TARE地形聚合与精确位置查询，修复暂缺HT预测时旧可行历史未失效的问题。保留未知探索引导与严格路径执行，原TSP/访问顺序、模型/滤波/0.5阈值、车体尺寸、搜索预算和速度不变。','',
'## 实现了什么功能','',
'原TARE地形提示避免选择已知车体足迹碰到墙的中心；HT仍在XYθ空间为其指定航点找完整可执行路线。不把未知引导当行驶许可，不证明全局SE2连通。','',
'## 实验与验证','',
f"实测冻结`{candidate}`，室内采集状态{row['state']}，实测{summary.get('duration_s','未知')}s，{metrics.get('distance_m','未知')}m / {metrics.get('observed_free_volume_m3','未知')}m³，末任务{metrics.get('mission','未知')}。四CTest50.65s、六函数SHA通过；旧代码失败反例和中途缺测历史反例均保留。",'',
f'[同室内阶段44→45比较图、报告和视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/{report})。每版本单次闭环，采样自由体积并集不是实际覆盖真值。完整已录数据以stage45.json远端大小与SHA回执为准，非全频原始传感器无损录制。','',
'## 存在什么问题','',*['- '+x for x in issues]])+'\n'
with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:raise RuntimeError('Unrelated staged changes')
 notes.write_text(body);v=read(ROOT/'docs/version_history.json');prior=next((s for s in v['stages'] if s['number']==45),None)
 if prior and prior['sha']!=candidate:raise RuntimeError('Stage45 already refers to another candidate')
 entry=dict(id='stage-45',number=45,sha=candidate,tag=tag,title='已知障碍足迹与原TARE地形提示统一',kind='地形执行接口修复',change='原地形提示遗漏已知车体障碍；增加精确查询、历史缓存更新，保留未知引导',features='保持原TARE TSP与HT严格执行约束；同室内600s独立对比',validation=str(row['state'])+' '+str(metrics)+'; fourCTest50.65s/sixSHA',known_issues='；'.join(issues),evidence=[report])
 v['stages']=[s for s in v['stages'] if s['number']!=45]+[entry];v['latest_recorded_trial_code']=candidate;v['latest_planner_code']=candidate;v['updated_at']=datetime.datetime.now().astimezone().isoformat();v['status']='阶段45室内实际结果已记录，完整数据正在发布；剩余问题见报告';write(ROOT/'docs/version_history.json',v)
 intro=f'# 阶段45：已知障碍足迹反馈与室内复测\n\n[同场景对比、报告与视频]({report}) · [完整已录数据](https://github.com/CQULzz/HT_Explo/releases/tag/{tag})。采集状态{row["state"]}，末任务{metrics.get("mission","未知")}；森林/隧道问题未据此宣称解决。完整远端备份以stage45.json为准。\n\n'
 for filename in ['README.md','VERSIONS.md']:
  p=ROOT/filename;text=p.read_text()
  if not text.startswith('# 阶段45'):p.write_text(intro+'## 前一轮记录\n\n'+text)
 h=ROOT/'HANDOFF.txt';line='阶段45室内测量与分析已结束：实测'+candidate+'；'+str(metrics)+'。结果'+report+'；全量数据正在发布。森林/隧道本轮未复测，不能称已全面修好。\n\n'
 if line not in h.read_text():h.write_text(h.read_text().replace('HT_Explo 项目交接文档\n','HT_Explo 项目交接文档\n'+line,1))
 command(['python3','scripts/publish_version_notes.py','--dry-run'])
 commit(['README.md','VERSIONS.md','HANDOFF.txt','docs/version_history.json',str(notes.relative_to(ROOT)),str(out.relative_to(ROOT))],'Record known-body terrain feedback600s with same-scene comparisons and remaining issues')
receipt=ROOT/'docs/experiments/publications/stage45.json'
args=['python3','scripts/publish_streamed_ht_trial.py','--suite',str(suite),'--archive',str(out),'--tag',tag,'--title','阶段45｜已知障碍足迹反馈与室内600秒','--notes',str(notes),'--receipt',str(receipt),'--upload-timeout-seconds','600']
if not good:args.append('--include-failed-recordings')
command(args)
with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 v=read(ROOT/'docs/version_history.json');v['latest_verified_trial_code']=candidate;v['status']='阶段45代码、结果和完整已录数据均已远端核验；未复测和剩余问题见报告';write(ROOT/'docs/version_history.json',v)
 write(ROOT/'docs/experiments/LAST_COMPLETED_STAGE45.json',dict(stage=45,tested_commit=candidate,release='https://github.com/CQULzz/HT_Explo/releases/tag/'+tag,remote_verified=True,result_archive=str(out),raw_suite=str(suite),collection_state=state['state'],all_recordings_validated=good))
 if good:command(['python3','scripts/prune_published_ht_raw.py','--keep','2','--apply'])
 h=ROOT/'HANDOFF.txt';h.write_text(h.read_text().replace('HT_Explo 项目交接文档\n','HT_Explo 项目交接文档\n阶段45全量发布已核验：docs/experiments/publications/stage45.json。最新完整轮保留策略已执行，原中断轮继续保护。当前没有新的测量；结果和未解决问题见最新报告。\n\n',1))
 commit(['docs/experiments','docs/version_history.json','HANDOFF.txt'],'Verify stage45 full data and video publication; retain recent complete and partial suites')
print('COMPLETE stage45 remote size/SHA verified',flush=True)
