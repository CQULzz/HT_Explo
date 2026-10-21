#!/usr/bin/env python3
"""Publish stage48 campus evidence without changing stage47 or navigation."""
import argparse
import datetime as dt
import fcntl
import json
from pathlib import Path
import shutil
import subprocess

from publish_matched_tare_comparison import ROOT, read, write, command, commit
from finalize_matched_tare_comparison import sha


def github_release(tag):
    """The tag endpoint embeds at most30 assets; full raw data may exceed it."""
    value=json.loads(subprocess.check_output(['gh','api',f'repos/CQULzz/HT_Explo/releases/tags/{tag}'],text=True))
    if len(value['assets'])>=30:
        pages=json.loads(subprocess.check_output(['gh','api','--paginate','--slurp',
            f'repos/CQULzz/HT_Explo/releases/{value["id"]}/assets?per_page=100'],text=True))
        value['assets']=[asset for page in pages for asset in page]
    return value


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True)
    ap.add_argument('--prepare-only',action='store_true',help='Push reports first; do not claim full data publication.')
    a=ap.parse_args()
    job=read(a.state);suite=Path(job['suite']);out=Path(job['archive']);tag=job['tag']
    if job['stage']!=48 or job['scene']!='campus':
        raise RuntimeError('This publisher is only for the independent campus pair')
    state=read(suite/'suite.json');metrics=read(out/'comparison_metrics.json')
    if state['state'] not in ('COMPLETED','COMPLETED_WITH_ISSUES'):
        raise RuntimeError('Preserve incomplete measurements; do not publish as finished')
    for row in state['runs']:
        name=row['scenario'];audit=read(out/name/'lifecycle_exception_audit.json')
        if not audit['actual600s'] or row['checks'].get('no_child_lifecycle_exception')!=audit['clean_shutdown']:
            raise RuntimeError('Missing600s/final lifecycle evidence')
    good=state['state']=='COMPLETED' and all(r['state']=='RECORDED' for r in state['runs'])
    if subprocess.check_output(['git','rev-parse',tag+'^{commit}'],text=True).strip()!=job['candidate_commit']:
        raise RuntimeError('Measured tag points to a different candidate')
    command(['git','push','origin','refs/tags/'+tag])
    report=str(out.relative_to(ROOT)/'REPORT.md')
    grid=read(out/'effective_parameter_comparison.json')['viewpoint_grids']
    descriptions=[]
    for name,label in [('original','原TARE同运动上限'),('ht','当前HT＋原TARE决策')]:
        m=metrics[name]
        descriptions.append(f"- {label}：600秒、{m['summary']['distance_m']:.2f}m、{m['external']['observed_free_volume_m3']:.3f}m³，末任务{m['mission']}，最长零运动指令区间{m['external']['longest_zero_command_s']:.3f}s。")
    failed={r['scenario']:[k for k,v in r['checks'].items() if not v] for r in state['runs']}
    note=ROOT/'docs/release_notes'/(tag+'.md')
    note.write_text('\n'.join(['# 阶段48：Campus原TARE与HT各600秒','','## 改了什么','',
        f"冻结设施`{job['candidate_commit']}`；HT导航/二进制保持`{job['navigation_control_commit']}`，原TARE适配基线`{job['upstream_commit']}`。只扩展实验入口支持campus，没有修导航或调优。",'',
        '## 实现了什么功能','',
        '同一campus原生起点、先原版后HT、各完整600秒；运动上限前进0.5m/s、倒车0.25m/s、角速度0.8rad/s，常规加速度0.5m/s²、1.2rad/s²，明确零运动保持例外。保留原版限幅前后指令、参数、MCAP、相机与实际RViz回放。','',
        '## 实验与验证','',
        *descriptions,'',f'采集总体状态：{state["state"]}；失败检查：{failed}。',
        f'运行时视点网格：{grid}。没有沿用室内的网格差异说明。','',
        f'[多角度曲线、轨迹、参数、视频和限制](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/{report})。','',
        '## 存在什么问题','',
        '原TARE两CMU节点采后SIGINT退出异常；HT有一次常规角加速度差分审计超限，未修改导航/控制来规避检查。原始日志和相邻控制指令均保留。',
        '单次顺序端到端对照，地形、几何与跟踪器不同；体积为统一源秒射线采样近似，不是真值覆盖率，也不能归因于HT单模块。离线RViz回放不证明原运行实时性。',
        '失败与采后异常照实保留。完整已录数据以docs/experiments/publications/stage48.json的远端大小/SHA回执为准。'])+'\n')
    for name in ('publish_campus_comparison.py','process_campus_comparison.py','render_matched_tare_comparison.py','audit_matched_tare_cleanup.py','rviz_recorded_comparison.py'):
        shutil.copy2(Path(__file__).with_name(name),out/name)
    write(out/'files_sha256.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                                 if p.is_file() and p.name!='files_sha256.json'})
    with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        versions=read(ROOT/'docs/version_history.json')
        previous=next((r for r in versions['stages'] if r['number']==48),None)
        if previous and previous['sha']!=job['candidate_commit']:
            raise RuntimeError('Stage48 already refers to another measured candidate')
        entry=dict(id='stage-48',number=48,sha=job['candidate_commit'],tag=tag,
            title='Campus原TARE与当前HT同运动上限各600秒',kind='校园场景端到端配对',
            change='仅实验入口增加campus；HT导航仍07c1abd，原TARE/TSP及控制配置保持',
            features='各600秒、共同体积指标、运行参数、路线、真实相机与RViz回放',
            validation='；'.join(descriptions),known_issues=f'单次对照；失败检查{failed}；详见报告',evidence=[report])
        versions['stages']=[r for r in versions['stages'] if r['number']!=48]+[entry]
        versions.update(latest_recorded_trial_code=job['candidate_commit'],latest_planner_code=job['navigation_control_commit'],
                        updated_at=dt.datetime.now().astimezone().isoformat(),status='阶段48校园两组已记录，完整附件待核验')
        write(ROOT/'docs/version_history.json',versions)
        intro=f'# 阶段48：Campus原TARE与HT对照\n\n[各600秒的图表、视频和实际参数]({report}) · [完整已录数据](https://github.com/CQULzz/HT_Explo/releases/tag/{tag})。导航仍07c1abd，单次端到端比较；备份状态以stage48.json为准。\n\n'
        for name in ('README.md','VERSIONS.md'):
            p=ROOT/name;old=p.read_text()
            if not old.startswith('# 阶段48'):
                p.write_text(intro+'## 前一轮记录\n\n'+old)
        command(['python3','scripts/publish_version_notes.py','--dry-run'])
        commit(['README.md','VERSIONS.md','docs/version_history.json',note.relative_to(ROOT),out.relative_to(ROOT),
                'presentations/finalize_matched_tare_comparison.py','presentations/render_matched_tare_comparison.py',
                'presentations/audit_matched_tare_cleanup.py','presentations/publish_campus_comparison.py',
                'presentations/rviz_recorded_comparison.py','presentations/process_campus_comparison.py','.gitignore'],
               'Record campus matched TARE versus HT600s and actual RViz replays')
    if a.prepare_only:
        print('REPORTS_PREPARED; complete data publication still pending',flush=True)
        return
    receipt=ROOT/'docs/experiments/publications/stage48.json'
    args=['python3','scripts/publish_streamed_ht_trial.py','--suite',suite,'--archive',out,'--tag',tag,
          '--title','阶段48｜Campus原TARE与HT同运动上限600秒对照','--notes',note,'--receipt',receipt,'--upload-timeout-seconds','600']
    if not good:
        args.append('--include-failed-recordings')
    command(args)
    # Keep comparison/RViz videos directly downloadable as well as included
    # in the already verified complete results archive. Never clobber assets.
    extras=[];temp=a.state.resolve().parent/'video_upload';temp.mkdir(exist_ok=True)
    for relative,name in [('comparison.mp4','stage48-campus-camera-comparison.mp4'),
                          ('rviz/rviz_comparison_4x.mp4','stage48-campus-rviz-comparison-4x.mp4'),
                          ('rviz/detail/rviz_detail_4x.mp4','stage48-campus-rviz-xytheta-4x.mp4')]:
        video=out/relative;dest=temp/name
        if not dest.exists():dest.hardlink_to(video)
        if sha(dest)!=sha(video):raise RuntimeError('Video upload source differs')
        release=github_release(tag)
        found=next((x for x in release['assets'] if x['name']==name),None)
        if found is None:
            command(['gh','release','upload',tag,dest,'--repo','CQULzz/HT_Explo'])
            release=github_release(tag)
            found=next(x for x in release['assets'] if x['name']==name)
        if found['state']!='uploaded' or found['size']!=video.stat().st_size or found['digest']!='sha256:'+sha(video):
            raise RuntimeError('Extra video failed remote size/SHA verification: '+name)
        extras.append(dict(name=name,bytes=found['size'],sha256=sha(video),url=found['browser_download_url']))
    addendum=ROOT/'docs/experiments/publication_addenda/stage48_videos.json';addendum.parent.mkdir(parents=True,exist_ok=True)
    write(addendum,dict(tag=tag,assets=extras,verified_at=dt.datetime.now().astimezone().isoformat(),
                       scope='Extra standalone camera comparison/RViz assets; same bytes already in full results archive.'))
    with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        versions=read(ROOT/'docs/version_history.json')
        versions.update(latest_verified_trial_code=job['candidate_commit'],status='阶段48校园两组600秒、图表、视频和全部已录数据远端大小/SHA核验完成；限制见报告')
        write(ROOT/'docs/version_history.json',versions)
        write(ROOT/'docs/experiments/LAST_COMPLETED_STAGE48.json',dict(stage=48,tested_commit=job['candidate_commit'],
              navigation_control_commit=job['navigation_control_commit'],upstream_commit=job['upstream_commit'],
              raw_suite=str(suite),result_archive=str(out),release=f'https://github.com/CQULzz/HT_Explo/releases/tag/{tag}',
              remote_verified=True,all_recordings_validated=good,collection_state=state['state']))
        if good:
            command(['python3','scripts/prune_published_ht_raw.py','--keep','2','--apply'])
        handoff=ROOT/'HANDOFF.txt';old=handoff.read_text()
        addition=f"阶段48校园配对完成：原TARE/HT各完整600秒，源代码设施{job['candidate_commit']}，HT导航仍07c1abd；状态{state['state']}，失败检查{failed}。"+' '.join(descriptions)+f' 图表、真实相机、实际RViz回放、参数与完整数据均发布，见{report}及docs/experiments/publications/stage48.json。仅此组campus，不自动修导航或开新候选。\n\n'
        addition+='校园录包容量处理：旧ht_repeat_publish_2026-10-15的7个远端附件及307个本机普通文件重新核验后，仅清理MCAP/NPZ约1.877GiB，报告/视频保留；docs/experiments/legacy_archive/local_pruning_2026-10-21_campus.json记录逐文件SHA。该旧目录为精简本机副本，完整恢复用旧Release，不要将精简副本再次冒充完整原始归档。\n\n'
        if addition not in old:
            handoff.write_text(old.replace('HT_Explo 项目交接文档\n','HT_Explo 项目交接文档\n'+addition,1))
        commit(['HANDOFF.txt','docs/experiments','docs/version_history.json'],
               'Verify campus comparison data and videos remotely')
    print('COMPLETE stage48 remote size/SHA verified',flush=True)


if __name__=='__main__':
    main()
