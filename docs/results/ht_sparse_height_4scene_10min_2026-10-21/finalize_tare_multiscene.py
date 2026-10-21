#!/usr/bin/env python3
"""Audit/export available evidence without relabelling interrupted recordings as600s."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def read(p):return json.loads(p.read_text())
def optional(p):return read(p) if p.is_file() else {}


def active_evidence_workers(suite):
    """Match owned output paths and known writers, rather than stale saved PIDs."""
    import psutil
    writers=('run_ht_multiscene.py','run_ht_endurance.py','watch_ht_endurance.py',
             'endurance_probe.py','capture_tare_multiscene_runtime.py')
    matches=[]
    for process in psutil.process_iter(['pid','cmdline']):
        try:
            argv=process.info['cmdline'] or []
            if any(str(suite) in arg for arg in argv) and any(name in arg for name in writers for arg in argv):
                matches.append(process.pid)
        except (psutil.NoSuchProcess,psutil.AccessDenied):pass
    return matches


def collection_evidence(suite,state):
    """Derive a publication view; never repair/overwrite the original suite state."""
    runs=[]
    for row in state['runs']:
        trial=suite/row['scenario'];summary=optional(trial/'summary.json')
        checks=optional(trial/'suite_validation.json').get('checks',{})
        complete=(trial/'COMPLETED.json').is_file() and summary.get('duration_s')==state['duration_s']
        validated=complete and row.get('state')=='RECORDED' and bool(checks) and all(checks.values()) and row.get('video_ok',False)
        runs.append(dict(scenario=row['scenario'],source_state=row['state'],
                         measured_duration_s=summary.get('duration_s'),
                         last_reported_progress_s=row.get('elapsed_measurement_s'),
                         complete_requested_duration=complete,validated_recording=validated,
                         started=(trial/'manifest.json').is_file(),error=row.get('error')))
    finalized=(suite/'FINISHED.json').is_file() and state.get('state') not in ('RUNNING','PENDING')
    return dict(source_suite_state=state.get('state'),source_finalized=finalized,
                derived_state=state['state'] if finalized else 'INTERRUPTED_OR_UNFINALIZED',
                planned_duration_per_scene_s=state['duration_s'],runs=runs,
                note='Derived evidence only. Progress is not a measured duration; source suite.json is retained verbatim. No failed or missing scene is padded/restarted.')


def run_audit(trial,script,arguments):
    log=trial/(script.removesuffix('.py')+'.log')
    with log.open('w') as f:
        p=subprocess.run([sys.executable,str(ROOT/'presentations'/script),str(trial),*arguments],stdout=f,stderr=subprocess.STDOUT)
    return dict(script=script,returncode=p.returncode,log=log.name)


def export_available(suite,out,state,evidence):
    """Strict600s exporter handles validated videos; partial files remain distinct."""
    if out.exists():raise RuntimeError('Refusing to overwrite '+str(out))
    completed=[r['scenario'] for r in evidence['runs'] if r['validated_recording']]
    if completed:
        result=subprocess.run([sys.executable,str(ROOT/'presentations/archive_ht_multiscene.py'),str(suite),
                               '--output',str(out),'--completed-subset','--scenarios',*completed])
        if result.returncode:raise RuntimeError('Validated subset export failed; all raw evidence remains in '+str(suite))
    else:
        out.mkdir(parents=True)
    # Preserve both the source state and the subset exporter view, if any.
    if (out/'suite.json').exists():shutil.copy2(out/'suite.json',out/'validated_subset_suite.json')
    shutil.copy2(suite/'suite.json',out/'suite.json')
    for name in ('FINISHED.json','REPORT.md'):
        if (suite/name).exists():shutil.copy2(suite/name,out/('source_'+name))
    (out/'collection_status.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2)+'\n')
    names=['FAILURE.json','COMPLETED.json','ANALYSIS_COMPLETED.json','manifest.json','live_status.json',
           'summary.json','suite_validation.json','video_validation.json','health.csv','resources.csv',
           'probe_summary.json','planner_parameters.yaml','follower_parameters.yaml',
           'parameter_capture_attempts.json','terrain_topic_isolation.json','endurance_audit.json',
           'blocked_commands.json','pose_admission_audit.json','context_consistency.json',
           'source_age_alignment.json','scan_delivery_trace.json']
    for row in state['runs']:
        scene=row['scenario'];src=suite/scene;dst=out/scene;dst.mkdir(exist_ok=True)
        for name in names:
            if (src/name).is_file():shutil.copy2(src/name,dst/name)
        for name in ['tare_waypoint_audit','latency_audit','prefix_admissibility_audit']:
            if (src/name).is_dir():shutil.copytree(src/name,dst/name,dirs_exist_ok=True)
        # An incomplete/unvalidated video is never promoted to a validated clip.
        # Full failed videos/MCAP/snapshots are included in the raw Release archive.
        (dst/'recording_status.json').write_text(json.dumps(next(r for r in evidence['runs'] if r['scenario']==scene),ensure_ascii=False,indent=2)+'\n')
        for kind in ('runner','watcher'):
            log=suite/f'{scene}.{kind}.log'
            if log.exists():shutil.copy2(log,dst/log.name)


def write_report(out,state,evidence,audits,history=False):
    lines=['# 原TARE＋HT多场景：计划与实际采集结果','',
           f'冻结运行提交：`{state["git_head"]}`。每场景计划{state["duration_s"]}秒；实际完成情况逐组列出。',
           f'原批次状态：`{evidence["source_suite_state"]}`；原批次终态记录存在：`{evidence["source_finalized"]}`；派生发布状态：`{evidence["derived_state"]}`。',
           '原suite.json原样保存；中断和未启动场景不补拼、不冒充600秒。进度字段仅为最后一次状态抽样，不是最终实测时长。','',
           '| 场景 | 原状态 | 实测时长(s) | 最后进度(s) | 完整采集检查 | 视频 |',
           '|---|---|---:|---:|---|---|']
    for row in evidence['runs']:
        s=row['scenario'];video=f'[已验证视频]({s}/camera_h264.mp4)' if (out/s/'camera_h264.mp4').exists() and row['validated_recording'] else '未生成或未验证；原文件保留于完整录包'
        lines.append(f'| {s} | {row["source_state"]} | {row["measured_duration_s"] if row["measured_duration_s"] is not None else "未知"} | {row["last_reported_progress_s"] if row["last_reported_progress_s"] is not None else "未采到"} | {row["validated_recording"]} | {video} |')
    lines+=['','## 原TARE与HT分工核验','',
            '本批原TARE决定访问顺序，HT负责指定航点XYθ路线；附加审计的未执行或空样本不计作通过。','',
            '| 场景 | 原覆盖周期 | 最大访问视点数 | HT非空路线 | 航点/同分支违例 | 分工检查 | 附加审计 |',
            '|---|---:|---:|---:|---:|---|---|']
    for row in state['runs']:
        s=row['scenario'];entry=audits[s];r=entry.get('routing') or {}
        failed=[a['script'] for a in entry.get('audits',[]) if a['returncode']]
        audit_status=', '.join(failed) if failed else ('未执行：记录不完整' if not entry['recording_complete'] else '已执行，退出码见additional_audits.json')
        lines.append(f'| {s} | {r.get("coverage_cycles","未知")} | {r.get("maximum_ordered_viewpoints","未知")} | {r.get("nonempty_executable_paths","未知")} | {len(r.get("contract_violations",[])) if r else "未知"} | {r.get("contract_passed","未审计")} | {audit_status} |')
    lines+=['','![多维度诊断](multiscene_diagnostics.png)','',
            '[PDF图表](multiscene_diagnostics.pdf)。缺失值留空并标“未采到”，不填成零。']
    if history:lines+=['','[同场景车库历史比较](garage_history/tare_architecture_comparison.png)；只包含实际具有完整指标的记录。']
    for row in state['runs']:
        s=row['scenario']
        for name,label in [('tare_waypoint_audit/architecture.png','TARE与HT分工'),('tare_waypoint_audit/routes.png','实际规划快照'),('prefix_admissibility_audit/endpoints.png','末段分段目标空间门槛')]:
            if (out/s/name).is_file():lines+=['',f'![{s} {label}]({s}/{name})']
    lines+=['','累计观测体积是0.5米体素的采样激光射线自由空间并集，不是真值覆盖率。不同场景/起点不可作算法排名；没有新增同限制原版TARE配对或实车验证。前缀终点允许不等于完整XYθ路径可达。',
            '精选目录仅包含可用报告及已验证视频；失败视频、MCAP、快照等全部已录文件由完整原始Release分卷保存，远端发布是否完成以发布校验回执为准。采集完成不等于探索成功。']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('suite',type=Path);ap.add_argument('--state',type=Path,required=True)
    ap.add_argument('--allow-interrupted',action='store_true',help='Export a stopped/unfinalized suite without modifying its source state; caller must ensure measurements have stopped')
    a=ap.parse_args();job=read(a.state);suite=a.suite.resolve();state=read(suite/'suite.json');out=Path(job['archive'])
    if state['git_head']!=job['candidate_commit']:raise ValueError('Measured candidate differs from frozen job')
    active=active_evidence_workers(suite)
    if active:raise ValueError('Owned evidence writers are still active: '+str(active))
    evidence=collection_evidence(suite,state)
    if not evidence['source_finalized'] and not a.allow_interrupted:
        raise ValueError('Unfinalized suite: confirm owned measurements have stopped, then use --allow-interrupted; never finalize an active suite')
    if out.exists():raise RuntimeError('Refusing to overwrite '+str(out))
    audits={}
    for row,proof in zip(state['runs'],evidence['runs']):
        scene=row['scenario'];trial=suite/scene
        if not proof['complete_requested_duration']:
            audits[scene]=dict(recording_complete=False,original_state=row);continue
        commands=[('audit_tare_waypoint.py',['--output',str(trial/'tare_waypoint_audit')]),
                  ('audit_tare_prefix_admissibility.py',['--output',str(trial/'prefix_admissibility_audit')]),
                  ('audit_cupy_latency.py',['--output',str(trial/'latency_audit')]),
                  ('audit_blocked_commands.py',['--output',str(trial/'blocked_commands.json')]),
                  ('audit_pose_admissibility_changes.py',['--output',str(trial/'pose_admission_audit.json'),'--capture-final',str(trial/'final_pose_snapshot.npz')]),
                  ('audit_ht_context_dumps.py',['--verify-model','--record-damaged-contexts','--output',str(trial/'context_consistency.json')]),
                  ('audit_ht_source_age_alignment.py',['--output',str(trial/'source_age_alignment.json')]),
                  ('audit_ht_scan_delivery_trace.py',['--output',str(trial/'scan_delivery_trace.json')])]
        results=[run_audit(trial,s,args) for s,args in commands]
        audits[scene]=dict(recording_complete=True,checks=row.get('checks'),audits=results,
                           routing=optional(trial/'tare_waypoint_audit/summary.json') or None)
    (suite/'additional_audits.json').write_text(json.dumps(audits,ensure_ascii=False,indent=2)+'\n')
    export_available(suite,out,state,evidence)
    shutil.copy2(suite/'additional_audits.json',out/'additional_audits.json')
    shutil.copy2(a.state,out/'frozen_job.json');shutil.copy2(Path(__file__),out/Path(__file__).name)
    plot_diagnostics(suite,out,state)
    # Include every complete same-scene record; never silently truncate a color zip.
    specs=[]
    history_runs=[('39 HT自选目标',ROOT/'docs/results/ht_successor_pruning_10min_2026-10-20/garage'),
                       ('40 恢复原TARE',ROOT/'docs/results/ht_tare_waypoint_10min_2026-10-20/garage'),
                       ('41 接口修正',ROOT/'docs/results/ht_tare_boundaries_10min_2026-10-20/garage')]
    if job.get('stage',42)>42:
        history_runs.append(('42 同版本车库复测',ROOT/'docs/results/ht_tare_native_5scene_10min_2026-10-20/garage'))
    if job.get('stage',42)>43:
        history_runs.append(('43 短前缀补搜',ROOT/'docs/results/ht_tare_short_prefix_10min_2026-10-21/garage'))
    history_runs.append((job.get('comparison_label','42 同版本车库复测'),suite/'garage'))
    for label,path in history_runs:
        if all((path/n).exists() for n in ['summary.json','endurance_audit.json']) and ((path/'timeseries.csv').exists() or (path/'current/timeseries.csv').exists()) and ((path/'observation_volume.csv').exists() or (path/'current/observation_volume.csv').exists()):specs+=['--run',label+'='+str(path)]
    history=False
    if specs:
        result=subprocess.run([sys.executable,str(ROOT/'presentations/plot_tare_route_comparison.py'),*specs,'--output',str(out/'garage_history')])
        history=result.returncode==0
    write_report(out,state,evidence,audits,history)
    hashes={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='files_sha256.json'}
    (out/'files_sha256.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
    print('ARCHIVED',out,flush=True)


def plot_diagnostics(suite,out,state):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    names=[r['scenario'] for r in state['runs']];data=[optional(suite/n/'endurance_audit.json') for n in names]
    external=[d.get('external_metrics') or {} for d in data]
    def number(value):return float(value) if value is not None else np.nan
    def bars(ax,values,**kwargs):
        values=np.asarray([number(v) for v in values]);ax.bar(x,values,**kwargs)
        for i,v in enumerate(values):
            if not np.isfinite(v):ax.annotate('未采到',(i,0),xytext=(0,4),textcoords='offset points',ha='center',fontsize=8,rotation=90)
    fig,axes=plt.subplots(2,3,figsize=(16,9),layout='constrained');x=np.arange(len(names))
    bars(axes[0,0],[d.get('summary',{}).get('distance_m') for d in data]);axes[0,0].set_title('实际行驶距离 / m')
    bars(axes[0,1],[d.get('observed_free_volume_m3') for d in external]);axes[0,1].set_title('近似累计观测自由体积 / m³')
    stopped=[number(d.get('fully_stopped_fraction'))*100 for d in external]
    bars(axes[0,2],stopped,label='完全停车');bars(axes[0,2],[number(d.get('stationary_turn_fraction'))*100 for d in external],bottom=stopped,label='原地转向');axes[0,2].set_title('运动指令组成 / %');axes[0,2].legend()
    axes[1,0].bar(x-.18,[number(d.get('sampled_map_age_s',{}).get('p95')) for d in data],.36,label='P95');axes[1,0].bar(x+.18,[number(d.get('sampled_map_age_s',{}).get('max')) for d in data],.36,label='最大');axes[1,0].axhline(3,c='r',ls='--',label='3秒门槛');axes[1,0].set_title('1Hz采样HT地图年龄 / s');axes[1,0].legend()
    bars(axes[1,1],[d.get('summary',{}).get('planner_runtime_p95_s') for d in data]);axes[1,1].set_title('规划周期耗时P95 / s')
    bars(axes[1,2],[d.get('distance_last60_m') for d in external]);axes[1,2].set_title('各自已记录末60秒行驶距离 / m')
    labels=[r['scenario']+'\n'+r['state'] for r in state['runs']]
    for ax in axes.flat:ax.set_xticks(x,labels,rotation=20);ax.grid(axis='y',alpha=.2)
    fig.suptitle('同一冻结版本多场景：失败/未启动保留，缺失值不补零；场景不同不作算法排名')
    fig.savefig(out/'multiscene_diagnostics.png',dpi=160);fig.savefig(out/'multiscene_diagnostics.pdf');plt.close(fig)


if __name__=='__main__':main()
