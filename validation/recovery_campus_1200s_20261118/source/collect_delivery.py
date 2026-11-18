from pathlib import Path
import ast, hashlib, json, shutil
root=Path('/home/lzz/ht_recovery_campus_1200s_20261118')
run=root/'runs/recovery_campus_1200s_01'
repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes')
work=Path('/mnt/d/HT-Recovery-Campus-1200s-20261118')
dest=repo/'validation/recovery_campus_1200s_20261118'
assert json.loads((run/'RESULT.json').read_text())['collection_complete']
dest.mkdir(exist_ok=False)
for n in ['data','logs','source','reference','contexts']:(dest/n).mkdir()
(dest/'.gitattributes').write_text('* -text\n*.log -whitespace\n*.csv -whitespace\n*.yaml -whitespace\n')
for n in ['RESULT.json','ANALYSIS.json','PHASES.json','COMMAND_AUDIT.json','RECORDING_VALIDATION.json','FREEZE.json','CLEANUP.json','COMMANDS.json','ACTUAL_NAVIGATION.json','STOP_DIAGNOSIS.json','PLANNING_CHAIN_DIAGNOSIS.json','RECOVERY_ANALYSIS.json','END_MOTION_CHECK.json','BACKTRACKING.json','backtracking_segments.csv','comparison.png','backtracking.png','end_motion.png','tare_planner_node.yaml','localPlanner.yaml','pathFollower.yaml','cupy_to_ht_bridge.yaml','vehicleSimulator.yaml']:shutil.copy2(run/n,dest/n)
for n in ['PLAN.json','BUDGET.json']:shutil.copy2(root/n,dest/n)
for n in ['metrics.csv','SUMMARY.json','START.json']:shutil.copy2(run/'observations'/n,dest/'data'/n)
for n in ['simulation.log','mapper.log','model.log','observer.log','bag.log']:shutil.copy2(run/n,dest/'logs'/n)
for n in ['CAMPUS_REFERENCE.json','REFERENCE_GROUND_PROXY.json','COVERAGE_ASSESSMENT.json','campus_reference_coverage.png']:shutil.copy2(root/'analysis'/n,dest/'reference'/n)
for n in ['run.py','env.sh','run_1200s.sh','simulation.launch.py','startup_collect.py','recording_qos.yaml']:(dest/'source'/n).write_text((root/n).read_text().rstrip()+'\n')
for p in work.iterdir():
 if p.is_file() and p.suffix in ['.py','.sh']:(dest/'source'/p.name).write_text(p.read_text(encoding='utf-8-sig').rstrip()+'\n')
contexts=sorted((run/'contexts').glob('*.npz'))
chosen=[contexts[0],contexts[-1]] if len(contexts)>1 else contexts
for p in chosen:shutil.copy2(p,dest/'contexts'/p.name)
(dest/'contexts/INDEX.json').write_text(json.dumps({'all_context_files_retained_locally':len(contexts),'compact_files':[p.name for p in chosen],'schedule':'first source frame then every60s, warmup0','scope':'Actual inference inputs, not reconstructed observations','raw_directory':str(run/'contexts')},indent=2))
with (dest/'data/diagnostic_samples.jsonl').open('w') as out:
 for line in (run/'observations/events.jsonl').open():
  e=json.loads(line)
  if e['kind']=='malformed_diagnostic' or e.get('nonfinite_fields') or e['kind']=='/ht_minimal/recovery':out.write(line.rstrip()+'\n')
shutil.copy2(repo/'validation/window_recovery_20261118/RUNTIME.json',dest/'NAVIGATION_RUNTIME.json')
for p in dest.rglob('*.json'):json.loads(p.read_text())
for p in dest.rglob('*.py'):ast.parse(p.read_text())
print('Collected compact delivery',dest,'context inputs',len(contexts))
