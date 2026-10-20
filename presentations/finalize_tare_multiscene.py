#!/usr/bin/env python3
"""Audit and export a frozen native-TARE/HT multi-scene experiment, including failures."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]


def read(p):return json.loads(p.read_text())


def run_audit(trial,script,arguments):
    log=trial/(script.removesuffix('.py')+'.log')
    with log.open('w') as f:
        p=subprocess.run([sys.executable,str(ROOT/'presentations'/script),str(trial),*arguments],stdout=f,stderr=subprocess.STDOUT)
    return dict(script=script,returncode=p.returncode,log=log.name)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('suite',type=Path);ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    job=read(a.state);suite=a.suite.resolve();state=read(suite/'suite.json');out=Path(job['archive'])
    if state['git_head']!=job['candidate_commit']:raise ValueError('Measured candidate differs from frozen job')
    audits={}
    for row in state['runs']:
        scene=row['scenario'];trial=suite/scene
        if not (trial/'COMPLETED.json').exists():
            audits[scene]=dict(recording_complete=False,original_state=row);continue
        if read(trial/'summary.json')['duration_s']!=600:raise ValueError('Unexpected measurement duration')
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
                           routing=read(trial/'tare_waypoint_audit/summary.json') if (trial/'tare_waypoint_audit/summary.json').exists() else None)
    (suite/'additional_audits.json').write_text(json.dumps(audits,ensure_ascii=False,indent=2)+'\n')
    # Exporter preserves collection failures; it refuses missing/undecodable videos.
    result=subprocess.run([sys.executable,str(ROOT/'presentations/archive_ht_multiscene.py'),str(suite),'--output',str(out)])
    if result.returncode:
        (suite/'EXPORT_FAILED.json').write_text(json.dumps(dict(returncode=result.returncode,retained_source=str(suite),audits=audits),ensure_ascii=False,indent=2)+'\n')
        raise RuntimeError('Selected export failed; original diagnostics and recordings retained')
    for row in state['runs']:
        scene=row['scenario'];src=suite/scene;dst=out/scene
        for name in ['planner_parameters.yaml','follower_parameters.yaml','parameter_capture_attempts.json','terrain_topic_isolation.json',
                     'blocked_commands.json','pose_admission_audit.json','context_consistency.json','source_age_alignment.json','scan_delivery_trace.json']:
            if (src/name).exists():shutil.copy2(src/name,dst/name)
        for name in ['tare_waypoint_audit','latency_audit','prefix_admissibility_audit']:
            if (src/name).is_dir():shutil.copytree(src/name,dst/name)
    shutil.copy2(suite/'additional_audits.json',out/'additional_audits.json')
    shutil.copy2(a.state,out/'frozen_job.json')
    shutil.copy2(Path(__file__),out/Path(__file__).name)
    plot_diagnostics(suite,out,state)
    # Same-scene garage history; this is not a fresh original-TARE comparison.
    args=[]
    for label,path in [('39 HT自选目标','ht_successor_pruning_10min_2026-10-20'),('40 恢复原TARE','ht_tare_waypoint_10min_2026-10-20'),('41 接口修正','ht_tare_boundaries_10min_2026-10-20')]:
        args += ['--run',label+'='+str(ROOT/'docs/results'/path/'garage')]
    args += ['--run','42 同版本车库复测='+str(suite/'garage'),'--output',str(out/'garage_history')]
    subprocess.run([sys.executable,str(ROOT/'presentations/plot_tare_route_comparison.py'),*args],check=True)
    with (out/'REPORT.md').open('a') as f:
        f.write('\n## 本批原TARE与HT分工核验\n\n冻结运行提交：`'+state['git_head']+'`。导航运行源码/配置/二进制与阶段41的72项SHA256逐一一致；本批没有更改算法。\n\n')
        f.write('| 场景 | 原覆盖周期 | 最大访问视点数 | HT非空路线 | 航点/同分支违例 | 分工检查 |\n|---|---:|---:|---:|---:|---|\n')
        for row in state['runs']:
            scene=row['scenario'];r=audits[scene].get('routing') or {}
            f.write(f'| {scene} | {r.get("coverage_cycles","未知")} | {r.get("maximum_ordered_viewpoints","未知")} | {r.get("nonempty_executable_paths","未知")} | {len(r.get("contract_violations",[])) if r else "未知"} | {r.get("contract_passed",False)} |\n')
        f.write('\n未移动或没有路线时，分工检查可能不满足“有实际执行样本”的通过条件；不能把空样本当作通过。各场景只有一次600秒记录，统计与检查仅限本批记录。\n\n![多维度诊断](multiscene_diagnostics.png)\n\n[PDF图表](multiscene_diagnostics.pdf) · [同场景车库历史比较](garage_history/tare_architecture_comparison.png)\n\n')
        f.write('| 场景 | 附加审计非零退出项 | CMU导航地形隔离 | 实际HT探索模式 |\n|---|---|---|---|\n')
        import yaml
        for row in state['runs']:
            scene=row['scenario'];trial=suite/scene
            failed=[r['script'] for r in audits[scene].get('audits',[]) if r['returncode']]
            isolation=read(trial/'terrain_topic_isolation.json') if (trial/'terrain_topic_isolation.json').exists() else {}
            params=yaml.safe_load((trial/'planner_parameters.yaml').read_text()) if (trial/'planner_parameters.yaml').exists() else {}
            mode=(params or {}).get('/tare_planner_node',{}).get('ros__parameters',{}).get('ht_exploration_mode','未采到')
            f.write(f'| {scene} | {", ".join(failed) or "无"} | {isolation.get("navigation_cmu_terrain_isolated","未知")} | {mode} |\n')
        f.write('累计观测体积是0.5米体素的采样激光射线自由空间并集，不是真值覆盖率。每组起点/场景参数不同，跨场景体积不作为算法优劣排名；没有新增原版TARE同限制对照或实车验证。完整数据是否已上传，以本批Release远端校验回执为准。\n')
        for row in state['runs']:
            scene=row['scenario'];f.write(f'\n### {scene} 的原访问顺序与HT路线\n\n![分工审计]({scene}/tare_waypoint_audit/architecture.png)\n\n![实际规划快照]({scene}/tare_waypoint_audit/routes.png)\n')
            f.write(f'\n![末段固定分段目标与HT空间门槛]({scene}/prefix_admissibility_audit/endpoints.png)\n\n[空间门槛回放与时间对齐限制]({scene}/prefix_admissibility_audit/summary.json)；这不是XYθ全路径可达性证明。\n')
    hashes={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='files_sha256.json'}
    (out/'files_sha256.json').write_text(json.dumps(hashes,ensure_ascii=False,indent=2)+'\n')
    print('ARCHIVED',out,flush=True)


def plot_diagnostics(suite,out,state):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    names=[r['scenario'] for r in state['runs']];data=[read(suite/n/'endurance_audit.json') for n in names]
    external=[d.get('external_metrics') or {} for d in data]
    fig,axes=plt.subplots(2,3,figsize=(16,9),layout='constrained');x=np.arange(len(names))
    axes[0,0].bar(x,[d['summary']['distance_m'] for d in data]);axes[0,0].set_title('实际行驶距离 / m')
    axes[0,1].bar(x,[d.get('observed_free_volume_m3',0) for d in external]);axes[0,1].set_title('近似累计观测自由体积 / m³')
    axes[0,2].bar(x,[100*d.get('fully_stopped_fraction',0) for d in external],label='完全停车')
    axes[0,2].bar(x,[100*d.get('stationary_turn_fraction',0) for d in external],bottom=[100*d.get('fully_stopped_fraction',0) for d in external],label='原地转向');axes[0,2].set_title('运动指令组成 / %');axes[0,2].legend()
    axes[1,0].bar(x-.18,[d['sampled_map_age_s']['p95'] for d in data],.36,label='P95');axes[1,0].bar(x+.18,[d['sampled_map_age_s']['max'] for d in data],.36,label='最大');axes[1,0].axhline(3,c='r',ls='--',label='3秒门槛');axes[1,0].set_title('1Hz采样HT地图年龄 / s');axes[1,0].legend()
    axes[1,1].bar(x,[d['summary'].get('planner_runtime_p95_s') or 0 for d in data]);axes[1,1].set_title('规划周期耗时P95 / s')
    axes[1,2].bar(x,[d.get('distance_last60_m',0) for d in external]);axes[1,2].set_title('末60秒行驶距离 / m')
    for ax in axes.flat:ax.set_xticks(x,names,rotation=20);ax.grid(axis='y',alpha=.2)
    fig.suptitle('同一冻结版本的五场景验证：场景与起点不同，不作跨场景算法排名')
    fig.savefig(out/'multiscene_diagnostics.png',dpi=160);fig.savefig(out/'multiscene_diagnostics.pdf');plt.close(fig)


if __name__=='__main__':main()
