from pathlib import Path
import json,csv,collections,shutil,hashlib,subprocess
r=Path('/home/lzz/ht_repeat_20261114')
out=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/repeats_20261114');out.mkdir(exist_ok=True)
summaries=[]
for run in sorted((r/'runs').iterdir()):
    if not (run/'RESULT.json').exists():continue
    dst=out/run.name;dst.mkdir(exist_ok=True)
    result=json.loads((run/'RESULT.json').read_text());row={'case':run.name,'result':result}
    if (run/'observations/SUMMARY.json').exists():
        rows=list(csv.DictReader((run/'observations/metrics.csv').open()));last=rows[-1];cut=min(rows,key=lambda x:abs(float(x['elapsed_s'])-270))
        row['last_30s_distance_m']=float(last['distance_m'])-float(cut['distance_m'])
        recovery=[];finish=[]
        for line in (run/'observations/events.jsonl').open():
            e=json.loads(line)
            if e['kind']=='/ht_minimal/recovery':recovery.append(e)
            if e['kind']=='finish_transition':finish.append(e)
        row['recovery_events']=recovery;row['finish_transitions']=finish
        for name in ['SUMMARY.json','START.json','metrics.csv']:shutil.copy2(run/'observations'/name,dst/name)
    (dst/'ANALYSIS.json').write_text(json.dumps(row,indent=2));summaries.append(row)
    for name in ['RESULT.json','COMMAND_AUDIT.json','FREEZE.json','ENVIRONMENT.json','COMMANDS.json','pathFollower.yaml','localPlanner.yaml','tare_planner_node.yaml','cupy_to_ht_bridge.yaml','simulation.log','mapper.log','model.log','observer.log']:
        if (run/name).exists():shutil.copy2(run/name,dst/name)
for name in ['env.sh','run.py','simulation.launch.py','REPEAT_BUDGET.json']:shutil.copy2(r/name,out/name)
(out/'setup').mkdir(exist_ok=True)
for name in ['prepare_repeats.py','run_repeats.sh','summarize_repeats.py']:
    shutil.copy2(Path('/mnt/d/HT-Execution-300s/setup')/name,out/'setup'/name)
src=Path('/home/lzz/tare_native_20261110/src/tare_planner/src')
patch=''
for p in sorted((r/'original_tare_source').rglob('*.cpp')):
    rel=p.relative_to(r/'original_tare_source');q=src/rel
    patch+=subprocess.run(['diff','-u','--label','a/src/tare_planner/src/'+str(rel),'--label','b/src/tare_planner/src/'+str(rel),str(p),str(q)],capture_output=True,text=True).stdout
(out/'diagnostic_only.patch').write_text(patch)
(out/'SUMMARY_ALL.json').write_text(json.dumps(summaries,indent=2))
(out/'.gitattributes').write_text('*.csv -text -whitespace\n*.log -text -whitespace\n')
for row in summaries:
    summary=row['result'].get('summary',{})
    print(row['case'],summary.get('elapsed_s'),summary.get('distance_m'),summary.get('sampled_free_volume_m3'),summary.get('finish'),'last30',row.get('last_30s_distance_m'),'finish_events',row.get('finish_transitions'))
