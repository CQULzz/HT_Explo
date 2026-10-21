#!/usr/bin/env python3
"""Keep measurement completion separate from child-node cleanup exceptions."""
import argparse
import datetime as dt
import json
from pathlib import Path
import re
import shutil

from finalize_matched_tare_comparison import read, write, sha

PATTERN=re.compile(r'terminate called|Traceback \(most recent call last\)|The following exception was never retrieved|exit code -(?:6|11)\b')


def classify(lines, measurement_end):
    hits=[dict(line=i,text=line) for i,line in enumerate(lines) if PATTERN.search(line)]
    stop=next((i for i,line in enumerate(lines) if 'user interrupted with ctrl-c (SIGINT)' in line),None)
    signals=[float(m[1]) for line in lines if 'signal_handler(SIGINT/SIGTERM)' in line
             and (m:=re.search(r'\[(\d+\.\d+)\]',line))]
    after=bool(hits) and stop is not None and all(h['line']>stop for h in hits) and bool(signals) and min(signals)>=measurement_end
    return dict(exceptions=hits,clean_shutdown=not hits,exceptions_confirmed_after_measurement_and_stop=after,
                no_in_measurement_exception_detected=not hits or after,
                first_signal_wall_time=min(signals) if signals else None)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    job=read(a.state);suite=Path(job['suite']);out=Path(job['archive']);state=read(suite/'suite.json')
    metrics=read(suite/'comparison_metrics.json')
    snapshot=suite/'suite_before_final_lifecycle_audit.json'
    if not snapshot.exists():
        write(snapshot,state)
    for row in state['runs']:
        name=row['scenario'];folder=suite/name;origin=read(folder/'current/measurement_started.json')['wall_time']
        audits={p.name:classify(p.read_text(errors='replace').splitlines(),origin+600)
                for p in (folder/'current').glob('*.log')}
        errors={k:v for k,v in audits.items() if v['exceptions']}
        clean=not errors;during_ok=all(v['no_in_measurement_exception_detected'] for v in audits.values())
        result=dict(measurement_origin_wall_time=origin,measurement_end_wall_time=origin+600,
                    actual600s=read(folder/'summary.json')['duration_s']==600,
                    clean_shutdown=clean,no_in_measurement_exception_detected=during_ok,files_with_exceptions=errors,
                    scope='Sequential log ordering and recorded signal-handler timestamps; exceptions are retained, never waived to claim clean shutdown.')
        for target in [folder,out/name]:
            write(target/'lifecycle_exception_audit.json',result)
            d=read(target/'suite_validation.json')
            d['checks'].update(no_child_lifecycle_exception=clean,no_in_measurement_exception_detected=during_ok)
            write(target/'suite_validation.json',d)
        row['checks'].update(no_child_lifecycle_exception=clean,no_in_measurement_exception_detected=during_ok)
        row['state']='RECORDED' if all(row['checks'].values()) else 'VALIDATION_FAILED'
        metrics[name]['checks']=row['checks']
        row['cleanup_scope']='CLEAN' if clean else 'POST_MEASUREMENT_SIGINT_EXCEPTION' if during_ok else 'UNRESOLVED_EXCEPTION'
    paired=read(suite/'paired_validation.json')
    paired_ok=all(paired['parameter_checks'].values()) and paired['start_position_pass'] and paired['start_yaw_pass']
    state['state']='COMPLETED' if all(r['state']=='RECORDED' for r in state['runs']) and paired_ok else 'COMPLETED_WITH_ISSUES'
    state['final_lifecycle_audit_at']=dt.datetime.now().astimezone().isoformat()
    lines=['## 子进程退出检查','']
    for row in state['runs']:
        name=row['scenario'];audit=read(suite/name/'lifecycle_exception_audit.json')
        if audit['clean_shutdown']:
            lines.append(f'- {name}：未检出匹配的子进程退出异常；仍需结合逐项采集检查判断总体状态。')
        else:
            scope='已确认位于测量结束及停止信号之后' if audit['no_in_measurement_exception_detected'] else '有异常未能确认全部位于测量之后'
            signals=[x['first_signal_wall_time'] for x in audit['files_with_exceptions'].values() if x['first_signal_wall_time'] is not None]
            first=min(signals) if signals else None
            lines.append(f'- {name}：{scope}；测量结束wall={audit["measurement_end_wall_time"]:.9f}，异常日志中最早信号wall={first}；文件：'+', '.join(audit['files_with_exceptions'])+'。')
    lines+=['',f'本轮最终状态{state["state"]}。采集与退出异常分开记录，不删除失败、不把完整计时等同于所有稳定性检查通过。详见逐组lifecycle_exception_audit.json和原始日志。','']
    paragraph='\n'.join(lines)+'\n'
    for target in [suite,out]:
        write(target/'suite.json',state);write(target/'FINISHED.json',state);write(target/'comparison_metrics.json',metrics)
        report=target/'REPORT.md';body=report.read_text().replace('总体状态：COMPLETED。','总体状态：'+state['state']+'。')
        if '## 子进程退出检查' not in body:
            body=body.replace('## 口径与限制\n',paragraph+'## 口径与限制\n',1)
        report.write_text(body)
    shutil.copy2(snapshot,out/snapshot.name)
    shutil.copy2(Path(__file__),out/Path(__file__).name)
    write(out/'files_sha256.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                                  if p.is_file() and p.name!='files_sha256.json'})
    print(json.dumps(dict(state=state['state'],trials=[dict(name=r['scenario'],state=r['state'],scope=r['cleanup_scope']) for r in state['runs']]),indent=2))


if __name__=='__main__':
    main()
