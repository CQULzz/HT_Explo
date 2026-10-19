from pathlib import Path
import json,shutil,hashlib
r=Path.cwd();out=r/'docs/results/ht_tare_waypoint_10min_2026-10-20';raw=r/Path('/tmp/ht_tare40_run_path').read_text().strip()/'garage';e=json.loads((out/'EXPERIMENT.json').read_text())
for dst in [out,raw]:shutil.copytree('/tmp/tare40_boundary_cases',dst/'boundary_counterexamples');shutil.copy2('/tmp/append_tare40_boundaries.py',dst/'append_tare40_boundaries.py')
issue='构造回归另有失败：HT删点后原BFS仍标记另一侧连通/候选，但实际最短路为空。近家rush-home也存在前视无输出时被包装层错误拦住的源条件反例；本轮没有触发返航。'
p=out/'REPORT.md';s=p.read_text();s=s.replace('XYθ搜索超时42次；','XYθ搜索时间上限42次、展开上限38次；');s=s.replace('## 仍存在什么问题\n\n','''## 仍存在什么问题

闭环录制后另做构造回归，确认了两个接口边界，下一候选修正；本轮消息检查通过不代表所有配置均正确：

1. **HT删点后连通性未同步。** 用真实ViewPointManager加载一条全方向禁行带，另一侧仍connected=1/candidate=1，但最短路poses=0；期望不允许该候选的GTest确实失败。原因是HT候选筛选发生在原BFS之后，连通性尚未看到这次删除。[失败输出](boundary_counterexamples/ht_tare40_connectivity_counterexample.log) · [构造源码](boundary_counterexamples/ht_tare_connectivity_probe.cpp)。
2. **近家返航指令优先级。** 源条件构造中，离家1.2m、原版rush-home开启，前视函数可无有效输出，但原版PublishWaypoint优先发HOME；HT包装层若先要求前视输出，会错误停车。此600秒始终EXPLORING，**这不是本轮现场停车原因**。[参数与条件](boundary_counterexamples/rush_home_source_case.json)。

''');p.write_text(s)
e['post_trial_boundary_cases']=dict(connectivity='real C++ regression failed on the recorded candidate; connected=1/candidate=1/path poses=0',rush_home='source-condition counterexample; not triggered in this trial');(out/'EXPERIMENT.json').write_text(json.dumps(e,ensure_ascii=False,indent=2)+'\n')
p=r/'docs/version_history.json';v=json.loads(p.read_text());v['stages'][-1]['known_issues']+=' '+issue;p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');shutil.copy2(p,out/'history/version_catalog.json')
for f in ['README.md','VERSIONS.md','docs/experiments/ITERATIONS.md','docs/experiments/NEXT_AUDIT.md']:
 p=r/f;s=p.read_text();pos=s.index('\n\n---');p.write_text(s[:pos]+'\n\n'+issue+s[pos:])
p=r/'docs/release_notes/ht-stage-20261020-tare-waypoint.md';s=p.read_text().replace('XYθ搜索超时42次；','XYθ搜索时间上限42次、展开上限38次；');p.write_text(s+'\n\n'+issue+'\n')
checks={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'files_sha256.json'};(out/'files_sha256.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(additional_cases=issue,geometry=e['geometry'],contract=e['tare_waypoint']),ensure_ascii=False,indent=2))
