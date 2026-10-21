#!/usr/bin/env python3
"""Publish only completed, sealed stage47 pair evidence, then verify all assets."""
import argparse
import datetime as dt
import fcntl
import json
from pathlib import Path
import subprocess

from run_scheduled_comparison import ROOT


def read(path):
    return json.loads(path.read_text())


def write(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def command(args):
    subprocess.run([str(x) for x in args],cwd=ROOT,check=True)


def commit(paths,message):
    command(['git','add','--',*paths])
    if subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT).returncode:
        command(['git','-c','user.name=Codex','-c','user.email=codex@local','commit','-m',message])
    command(['git','push','origin','HEAD:codex/ht8dir-v1'])


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    job=read(a.state);suite=Path(job['suite']);out=Path(job['archive']);tag=job['tag']
    state=read(suite/'suite.json');metrics=read(out/'comparison_metrics.json')
    for row in state['runs']:
        audit=read(out/row['scenario']/'lifecycle_exception_audit.json')
        if row['checks'].get('no_child_lifecycle_exception')!=audit['clean_shutdown']:
            raise RuntimeError('Final lifecycle audit is missing or inconsistent')
    good=state['state']=='COMPLETED' and all(r['state']=='RECORDED' for r in state['runs'])
    if subprocess.check_output(['systemctl','--user','show','ht-tare-matched-10min.service','-p','MainPID','--value'],text=True).strip()!='0':
        raise RuntimeError('Measurement still active')
    if subprocess.check_output(['git','rev-parse',tag+'^{commit}'],text=True).strip()!=job['candidate_commit']:
        raise RuntimeError('Measured tag is missing or points to different code')
    command(['git','push','origin','refs/tags/'+tag])
    report=str(out.relative_to(ROOT)/'REPORT.md')
    note=ROOT/'docs/release_notes'/(tag+'.md')
    o=metrics['original'];h=metrics['ht']
    descriptions=[]
    for label,m in [('原TARE同运动上限',o),('最新HT',h)]:
        descriptions.append(f"- {label}：600秒、{m['summary']['distance_m']:.2f}m、{m['external']['observed_free_volume_m3']:.3f}m³，末任务{m['mission']}，最长完全停车{m['external']['longest_zero_command_s']:.3f}s。")
    text='\n'.join(['# 阶段47：原TARE与最新HT同运动上限室内对照','',
        '## 改了什么','',
        f"增加独立对照设施，HT导航保持`{job['navigation_control_commit']}`，72项运行文件/二进制未改；原TARE ROS2适配代码保持`{job['upstream_commit']}`。冻结设施提交`{job['candidate_commit']}`。",'',
        '## 实现了什么功能','',
        '同一室内场景/原生起点，各实际600秒；原CMU参数和透明限幅组件对齐前进/倒车/角速度及常规加速度。保留限幅前后指令、有效参数、视频、MCAP和共同源秒观测指标。原TARE规划/TSP、地形和自身跟踪策略保留，HT导航本轮不改。','',
        '## 实验与验证','',*descriptions,'',
        f'[两组视频、共同指标曲线、轨迹、参数和实际指令审计](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/{report})。采集总体状态{state["state"]}。运动限幅四项回归、原TARE六函数SHA通过；采集/视频/冻结检查见逐组JSON。完整已录数据以stage47.json远端大小/SHA回执为准。','',
        '## 存在什么问题','',
        '- 原TARE组CMU localPlanner/pathFollower在600秒采集结束、收到SIGINT后退出异常，完整指标保留但退出检查失败；整体COMPLETED_WITH_ISSUES，发布不标全项通过。',
        '- 各系统只有一次独立运行、固定测量顺序，不代表统计显著优越，也不是HT单模块消融。',
        '- 对齐运动包络后的原TARE并非CMU默认高速控制链；两个跟踪器、地形与几何规则仍不同。',
        '- 原TARE视点网格50×50/0.6m，HT为100×100/0.3m，名义范围相同但网格数量不同；完整参数差异已记录。',
        '- 观测自由体积是源秒抽样射线体素并集近似，不是覆盖真值；不是全频原始传感器无损录制。',
        '- 本轮不代表森林/隧道问题已解决，也没有实车验证。'])+'\n'
    with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        note.write_text(text)
        versions=read(ROOT/'docs/version_history.json')
        previous=next((s for s in versions['stages'] if s['number']==47),None)
        if previous and previous['sha']!=job['candidate_commit']:
            raise RuntimeError('Stage47 already belongs to another measured candidate')
        entry=dict(id='stage-47',number=47,sha=job['candidate_commit'],tag=tag,
                   title='原TARE与最新HT同运动上限室内600秒对照',kind='同运动包络端到端配对',
                   change='新增比较设施；HT导航不改；原TARE使用原探索/TSP与显式对齐的控制包络',
                   features='独立双600秒/共同观测指标/限幅前后指令/参数与视频',
                   validation='；'.join(descriptions),
                   known_issues='原CMU采后SIGINT退出异常；单次端到端对照，网格密度不同；非HT单模块消融',evidence=[report])
        versions['stages']=[s for s in versions['stages'] if s['number']!=47]+[entry]
        versions.update(latest_recorded_trial_code=job['candidate_commit'],
                        latest_planner_code=job['navigation_control_commit'],
                        updated_at=dt.datetime.now().astimezone().isoformat(),
                        status='阶段47比较已记录，完整数据正在发布；发布状态以stage47.json为准')
        write(ROOT/'docs/version_history.json',versions)
        intro=f'# 阶段47：原TARE与最新HT同运动上限对照\n\n[室内各600秒的图表、报告和视频]({report}) · [完整已录数据](https://github.com/CQULzz/HT_Explo/releases/tag/{tag})。HT导航保持07c1abd；端到端单次比较，非单模块消融。完整备份以stage47.json为准。\n\n'
        for name in ['README.md','VERSIONS.md']:
            p=ROOT/name;old=p.read_text()
            if not old.startswith('# 阶段47'):
                p.write_text(intro+'## 前一轮记录\n\n'+old)
        command(['python3','scripts/publish_version_notes.py','--dry-run'])
        commit(['README.md','VERSIONS.md','docs/version_history.json',note.relative_to(ROOT),out.relative_to(ROOT),
                'presentations/finalize_matched_tare_comparison.py','presentations/publish_matched_tare_comparison.py',
                'presentations/render_matched_tare_comparison.py','presentations/audit_matched_tare_cleanup.py',
                'presentations/test_matched_tare_cleanup.py','docs/experiments/evidence/2026-10-21_matched_tare'],
               'Record fresh TARE versus latest HT600s with matched motion envelope and common metrics')
    receipt=ROOT/'docs/experiments/publications/stage47.json'
    arguments=['python3','scripts/publish_streamed_ht_trial.py','--suite',suite,'--archive',out,'--tag',tag,
               '--title','阶段47｜原TARE与最新HT同运动上限室内对照','--notes',note,'--receipt',receipt,'--upload-timeout-seconds','600']
    if not good:
        arguments.append('--include-failed-recordings')
    command(arguments)
    with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        versions=read(ROOT/'docs/version_history.json')
        versions['latest_verified_trial_code']=job['candidate_commit']
        versions['status']='阶段47两组600秒、代码、视频和完整已录数据均远端核验；原CMU采后退出检查失败，限制与差距见报告'
        write(ROOT/'docs/version_history.json',versions)
        write(ROOT/'docs/experiments/LAST_COMPLETED_STAGE47.json',dict(stage=47,tested_commit=job['candidate_commit'],
             navigation_control_commit=job['navigation_control_commit'],upstream_commit=job['upstream_commit'],
             raw_suite=str(suite),result_archive=str(out),release='https://github.com/CQULzz/HT_Explo/releases/tag/'+tag,
             remote_verified=True,all_recordings_validated=good,collection_state=state['state']))
        if good:
            command(['python3','scripts/prune_published_ht_raw.py','--keep','2','--apply'])
        handoff=ROOT/'HANDOFF.txt'
        retained='最近完整raw保留46/47，部分42继续保护。' if good else '本轮47因原CMU采后退出异常保护保留，不挤占既有完整45/46；部分42继续保护。'
        addition='阶段47最新补记（优先于下文阶段46快照）：原TARE与最新HT同室内、同运动上限各600秒测量/图表/视频/完整已录数据均已发布并远端核验，见docs/experiments/publications/stage47.json。设施实测'+job['candidate_commit']+'；HT导航仍为07c1abd。'+ ' '.join(descriptions)+' 报告'+report+'。原版CMU两节点在600秒后SIGINT退出异常，整体COMPLETED_WITH_ISSUES，回执按保留缺陷发布、不能称全项通过。原版经过显式运动限幅；原版50×50/0.6m、HT100×100/0.3m网格密度不同。仍是两套不同感知/控制系统的单次端到端比较；不代表单模块或统计结论。测量和发布均结束，不自动新增试验。'+retained+'\n\n'
        old=handoff.read_text()
        if addition not in old:
            handoff.write_text(old.replace('HT_Explo 项目交接文档\n','HT_Explo 项目交接文档\n'+addition,1))
        commit(['HANDOFF.txt','docs/experiments','docs/version_history.json'],
               'Verify stage47 pair data and videos remotely; retain recent complete raw suites')
    print('COMPLETE stage47 remote size/SHA verified',flush=True)


if __name__=='__main__':
    main()
