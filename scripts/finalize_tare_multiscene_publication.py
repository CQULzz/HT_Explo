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


def publication_overview(suite,state):
    """Use measured summaries, not planned duration or last progress as completed time."""
    rows=[];issues=[];complete=[]
    for r in state['runs']:
        scene=r['scenario'];metrics=r.get('metrics',{});trial=suite/scene
        summary=read(trial/'summary.json') if (trial/'summary.json').exists() else {}
        checks=read(trial/'suite_validation.json').get('checks',{}) if (trial/'suite_validation.json').exists() else {}
        good=(trial/'COMPLETED.json').exists() and summary.get('duration_s')==state['duration_s'] and r['state']=='RECORDED' and bool(checks) and all(checks.values())
        complete.append(good)
        audit=read(trial/'endurance_audit.json') if (trial/'endurance_audit.json').exists() else {}
        external=audit.get('external_metrics') or {};route=read(trial/'tare_waypoint_audit/summary.json') if (trial/'tare_waypoint_audit/summary.json').exists() else {}
        duration=summary.get('duration_s','未知');progress=r.get('elapsed_measurement_s','未采到')
        rows.append(f'| {scene} | {r["state"]} | {duration} | {progress} | {metrics.get("distance_m","未知")} | {metrics.get("observed_free_volume_m3","未知")} | {metrics.get("mission","未知")} | {external.get("longest_zero_command_s","未知")} | {route.get("contract_passed","未审计")} |')
        if not good:issues.append(scene+':未获得完整且通过检查的记录')
        if not route.get('contract_passed'):issues.append(scene+':分工未通过或缺少执行样本，见审计')
        if external.get('longest_zero_command_s',0)>10 and metrics.get('mission')!='COMPLETED':issues.append(scene+':存在超过10秒完全停车，见状态和地形诊断')
    fully_complete=state['state']=='COMPLETED' and bool(complete) and all(complete)
    overview=f'计划{len(state["runs"])}场景、每组{state["duration_s"]}秒；已获得{sum(complete)}组完整且通过检查的记录，其余{len(complete)-sum(complete)}组未完成、检查不通过或未启动。'
    return rows,issues,overview,fully_complete


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
    rows,issues,overview,fully_complete=publication_overview(suite,state)
    notes=ROOT/'docs/release_notes'/(tag+'.md');report=str(archive.relative_to(ROOT)/'REPORT.md')
    body=f'''# 阶段42：原TARE＋HT冻结版本五场景验证

## 改了什么

本轮没有修改导航算法、HT模型、建图融合或运动限制。冻结运行提交`{candidate}`；72项运行文件/配置/二进制与阶段41导航代码`{control}`一致。新增五场景采集、参数与话题隔离检查、路由分工审计、视频、图表和完整数据发布工具。

## 实现了什么功能

沿用原TARE覆盖决策/全局与局部TSP/waypoint，HT在XYθ空间给指定航点找可执行路线；原六函数与ROS2适配参照b6760ad一致。计划场景为车库、校园、室内、森林和隧道，独立起点与高程历史；实际已录场景及中断情况见下表。

## 实验与验证

{overview} 原批次状态为`{state["state"]}`。实测时长缺失时标未知；最后进度不是最终实测时长。定时采集完成不等于探索成功。

| 场景 | 采集状态 | 实测时长s | 最后进度s | 里程m | 近似观测体积m³ | 末尾任务 | 最长完全停车s | TARE→HT分工检查 |
|---|---|---:|---:|---:|---:|---|---:|---|
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
        entry=dict(id='stage-42',number=42,sha=candidate,tag=tag,title='原TARE＋HT五场景计划与实际采集（含中断/失败）' if not fully_complete else '原TARE＋HT冻结版本五场景600秒验证',kind='多环境验证（导航未改）',change='计划使用同阶段41导航逻辑在五场景独立录制；实际完成及中断见逐组记录，增加参数/话题/分工/视频及数据核验',features='原TARE确定访问顺序，HT负责指定航点XYθ路由；本轮不改算法',validation='五场景实际结果见报告；采集状态：'+', '.join(r['scenario']+'='+r['state'] for r in state['runs']),known_issues='；'.join(issues+['没有同限制原版新配对、实车与全局SE2可达性保证']),evidence=[report],control_commit=control,ht_bridge_commit='42966cb22b0f719df035391f3850b9a654f161e1')
        prior=next((s for s in v['stages'] if s['number']==42),None)
        if prior and prior['sha']!=candidate:raise ValueError('Stage42 already describes another candidate')
        v['stages']=[s for s in v['stages'] if s['number']!=42]+[entry];v['latest_recorded_trial_code']=candidate;v['status']='阶段42已录数据正在发布；'+overview+'状态及缺陷见逐场景报告';v['updated_at']=datetime.datetime.now().astimezone().isoformat();write(p,v)
        intro=f'# 阶段42：原TARE＋HT五场景验证\n\n同阶段41导航版本。{overview} 失败及未启动场景照实保留。[报告、可用视频和图表]({report}) · [完整数据Release](https://github.com/CQULzz/HT_Explo/releases/tag/{tag})。完整数据发布状态以stage42.json回执为准。\n\n'
        for filename in ['README.md','VERSIONS.md']:
            path=ROOT/filename;text=path.read_text()
            if text.startswith('# 阶段42'):
                marker='## 前一轮结果\n\n'
                if marker not in text:raise ValueError('Cannot safely replace existing stage42 introduction')
                text=text.split(marker,1)[1]
            path.write_text(intro+'## 前一轮结果\n\n'+text)
        command(['python3','scripts/publish_version_notes.py','--dry-run'])
        paths=['README.md','VERSIONS.md','docs/version_history.json',str(notes.relative_to(ROOT)),str(archive.relative_to(ROOT)),'scripts/publish_streamed_ht_trial.py','scripts/finalize_tare_multiscene_publication.py','scripts/wait_and_publish_tare_multiscene.py','scripts/finalize_legacy_ht_archive.sh','presentations/finalize_tare_multiscene.py','presentations/audit_tare_prefix_admissibility.py','presentations/run_ht_multiscene.py','presentations/plot_tare_route_comparison.py','presentations/test_multiscene_interruption.py','scripts/prune_published_ht_raw.py']
        commit(paths,'Archive frozen native TARE and HT five-scene results with explicit failures')
    while subprocess.run(['gh','api','user','--silent'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
        print('WAITING_FOR_GITHUB_KEYRING; local reports/videos are ready',flush=True);time.sleep(30)
    receipt=ROOT/'docs/experiments/publications/stage42.json'
    args=['python3','scripts/publish_streamed_ht_trial.py','--suite',str(suite),'--archive',str(archive),'--tag',tag,'--title','阶段42｜原TARE＋HT五场景冻结版本验证','--notes',str(notes),'--receipt',str(receipt)]
    if not fully_complete:args.append('--include-failed-recordings')
    command(args)
    with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        v=read(ROOT/'docs/version_history.json');v['status']='阶段42全部已录数据已发布并核验；'+overview+'缺陷见报告';write(ROOT/'docs/version_history.json',v)
        result=dict(stage=42,tested_commit=candidate,navigation_control_commit=control,release=f'https://github.com/CQULzz/HT_Explo/releases/tag/{tag}',remote_verified=True,result_archive=str(archive),raw_suite=str(suite),collection_state=state['state'],collection_complete=fully_complete,retention_action='verify_then_prune_old_complete' if fully_complete else 'keep_all_partial_and_recent_complete')
        write(ROOT/'docs/experiments/LAST_COMPLETED_STAGE42.json',result)
        # An interrupted suite must not evict one of the latest two complete raw suites.
        if fully_complete:command(['python3','scripts/prune_published_ht_raw.py','--keep','2','--apply'])
        commit(['docs/experiments','docs/version_history.json'],'Verify stage42 publication; preserve partial data and recent complete raw suites')
    print('PUBLISHED_AND_VERIFIED: all actually recorded files; '+overview,flush=True)


if __name__=='__main__':main()
