#!/usr/bin/env python3
"""Publish measured five-scene evidence; source/collection failures stay explicit."""
import argparse
import datetime
import fcntl
import json
from pathlib import Path
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]


def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def command(args):subprocess.run(args,cwd=ROOT,check=True)


def commit(paths,message):
    command(['git','add','--',*paths])
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
        command(['git','-c','user.name=Codex','-c','user.email=codex@local','commit','-m',message])
    command(['git','push','origin','HEAD:codex/ht8dir-v1'])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    job=read(a.state);suite=Path(job['suite']);archive=Path(job['archive']);state=read(suite/'suite.json')
    if not (archive/'files_sha256.json').exists():raise ValueError('Post-analysis archive is not complete')
    if state['git_head']!=job['candidate_commit']:raise ValueError('Frozen candidate mismatch')
    tag=job['tag'];candidate=job['candidate_commit'];control=job['navigation_control_commit']
    local=subprocess.run(['git','rev-parse','--verify','refs/tags/'+tag],cwd=ROOT,capture_output=True,text=True)
    if local.returncode:command(['git','tag',tag,candidate])
    elif subprocess.check_output(['git','rev-parse',tag+'^{commit}'],cwd=ROOT,text=True).strip()!=candidate:raise ValueError('Never move an existing measured tag')
    command(['git','push','origin','refs/tags/'+tag])
    rows=[];issues=[]
    for r in state['runs']:
        scene=r['scenario'];metrics=r.get('metrics',{});trial=suite/scene
        audit=read(trial/'endurance_audit.json') if (trial/'endurance_audit.json').exists() else {}
        external=audit.get('external_metrics') or {};route=read(trial/'tare_waypoint_audit/summary.json') if (trial/'tare_waypoint_audit/summary.json').exists() else {}
        rows.append(f'| {scene} | {r["state"]} | {metrics.get("distance_m","未知")} | {metrics.get("observed_free_volume_m3","未知")} | {metrics.get("mission","未知")} | {external.get("longest_zero_command_s","未知")} | {route.get("contract_passed",False)} |')
        if r['state']!='RECORDED':issues.append(scene+':采集检查存在问题')
        if not route.get('contract_passed'):issues.append(scene+':分工未通过或缺少执行样本，见审计')
        if external.get('longest_zero_command_s',0)>10 and metrics.get('mission')!='COMPLETED':issues.append(scene+':存在超过10秒完全停车，见状态和地形诊断')
    notes=ROOT/'docs/release_notes'/(tag+'.md');report=str(archive.relative_to(ROOT)/'REPORT.md')
    body=f'''# 阶段42：原TARE＋HT冻结版本五场景验证

## 改了什么

本轮没有修改导航算法、HT模型、建图融合或运动限制。冻结运行提交`{candidate}`；72项运行文件/配置/二进制与阶段41导航代码`{control}`一致。新增五场景采集、参数与话题隔离检查、路由分工审计、视频、图表和完整数据发布工具。

## 实现了什么功能

沿用原TARE覆盖决策/全局与局部TSP/waypoint，HT在XYθ空间给指定航点找可执行路线；原六函数与ROS2适配参照b6760ad一致。场景为车库、校园、室内、森林和隧道，独立起点与高程历史。

## 实验与验证

每组计划并检查600秒；定时采集完成不等于探索成功。实际结果如下，不把失败数据改为通过。

| 场景 | 采集状态 | 里程m | 近似观测体积m³ | 末尾任务 | 最长完全停车s | TARE→HT分工检查 |
|---|---|---:|---:|---|---:|---|
'''+ '\n'.join(rows)+f'''

[报告、视频与对比图](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/{report})。原始MCAP和全部已录文件放本Release分卷附件，逐文件清单、资产SHA256和仓库发布回执共同核验；发布是否完成以stage42.json为准。激光按源秒采样，不是全频原始传感器无损录制。

## 存在什么问题

'''+ ('；'.join(issues) if issues else '具体搜索退出、停车、转向和时延仍见逐组报告，未把一次未复现问题视为没有缺陷。')+'''

没有新增同控制约束的原版TARE配对，跨场景体积不可用于算法排名。粗视点图不保证完整SE2可达性；未验证完整轮胎动力学或实车。地图/模型/几何门槛没有为追求体积而放宽。
'''
    with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:raise ValueError('Unrelated staged changes must be preserved')
        notes.write_text(body)
        p=ROOT/'docs/version_history.json';v=read(p)
        entry=dict(id='stage-42',number=42,sha=candidate,tag=tag,title='原TARE＋HT冻结版本五场景600秒验证',kind='多环境验证（导航未改）',change='同阶段41导航逻辑在五场景独立录制，增加参数/话题/分工/视频及数据核验',features='原TARE确定访问顺序，HT负责指定航点XYθ路由；本轮不改算法',validation='五场景实际结果见报告；采集状态：'+', '.join(r['scenario']+'='+r['state'] for r in state['runs']),known_issues='；'.join(issues+['没有同限制原版新配对、实车与全局SE2可达性保证']),evidence=[report],control_commit=control,ht_bridge_commit='42966cb22b0f719df035391f3850b9a654f161e1')
        prior=next((s for s in v['stages'] if s['number']==42),None)
        if prior and prior['sha']!=candidate:raise ValueError('Stage42 already describes another candidate')
        v['stages']=[s for s in v['stages'] if s['number']!=42]+[entry];v['latest_recorded_trial_code']=candidate;v['status']='阶段42五场景已记录，完整数据正在发布；状态及缺陷见逐场景报告';v['updated_at']=datetime.datetime.now().astimezone().isoformat();write(p,v)
        intro=f'# 阶段42：原TARE＋HT五场景验证\n\n同阶段41导航版本在车库、校园、室内、森林、隧道各记录600秒，采集与导航结果分别解释。[报告、五组视频和图表]({report}) · [完整数据Release](https://github.com/CQULzz/HT_Explo/releases/tag/{tag})。完整数据发布状态以stage42.json回执为准。\n\n'
        for filename in ['README.md','VERSIONS.md']:
            path=ROOT/filename;text=path.read_text()
            if not text.startswith('# 阶段42'):
                path.write_text(intro+'## 前一轮结果\n\n'+text)
        command(['python3','scripts/publish_version_notes.py','--dry-run'])
        paths=['README.md','VERSIONS.md','docs/version_history.json',str(notes.relative_to(ROOT)),str(archive.relative_to(ROOT)),'scripts/publish_streamed_ht_trial.py','scripts/finalize_tare_multiscene_publication.py','scripts/wait_and_publish_tare_multiscene.py','scripts/finalize_legacy_ht_archive.sh','presentations/finalize_tare_multiscene.py','presentations/audit_tare_prefix_admissibility.py']
        commit(paths,'Archive frozen native TARE and HT five-scene results with explicit failures')
    while subprocess.run(['gh','api','user','--silent'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        print('WAITING_FOR_GITHUB_KEYRING; local reports/videos are ready',flush=True);time.sleep(30)
    receipt=ROOT/'docs/experiments/publications/stage42.json'
    args=['python3','scripts/publish_streamed_ht_trial.py','--suite',str(suite),'--archive',str(archive),'--tag',tag,'--title','阶段42｜原TARE＋HT五场景冻结版本验证','--notes',str(notes),'--receipt',str(receipt)]
    if state['state']!='COMPLETED' or any(r['state']!='RECORDED' for r in state['runs']):args.append('--include-failed-recordings')
    command(args)
    with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        v=read(ROOT/'docs/version_history.json');v['status']='阶段42五场景结果及全部已录数据已发布并核验，缺陷见报告';write(ROOT/'docs/version_history.json',v)
        result=dict(stage=42,tested_commit=candidate,navigation_control_commit=control,release=f'https://github.com/CQULzz/HT_Explo/releases/tag/{tag}',remote_verified=True,result_archive=str(archive),raw_suite=str(suite),collection_state=state['state'])
        write(ROOT/'docs/experiments/LAST_COMPLETED_STAGE42.json',result)
        command(['python3','scripts/prune_published_ht_raw.py','--keep','2','--apply'])
        commit(['docs/experiments','docs/version_history.json'],'Verify complete stage42 publication and retain latest two raw suites')
    print('COMPLETE: five-scene measured results and all recorded data published and verified',flush=True)


if __name__=='__main__':main()
