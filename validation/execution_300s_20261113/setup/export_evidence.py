from pathlib import Path
import shutil,json,hashlib,subprocess
r=Path('/home/lzz/ht_execution_300s_20261113');out=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/execution_300s_20261113')
(out/'setup').mkdir(exist_ok=True)
for p in Path('/mnt/d/HT-Execution-300s/setup').glob('*'):
    if p.suffix in ['.py','.sh']:shutil.copy2(p,out/'setup'/p.name)
for p in (r/'setup').glob('*'):
    if p.is_file() and p.suffix in ['.log','.txt','.json']:shutil.copy2(p,out/'setup'/p.name)
shutil.copy2(r/'env.sh',out/'setup/env.sh')
shutil.copy2(r/'run.py',out/'setup/run.py')
shutil.copy2(r/'simulation.launch.py',out/'setup/simulation.launch.py')
for name in ['config','runtime','common_sensor']:
    shutil.copytree(r/name,out/'setup'/name,dirs_exist_ok=True)
(out/'failed_attempt_01').mkdir(exist_ok=True)
for name in ['RESULT.json','simulation.log','mapper.log','model.log','observer.log']:
    shutil.copy2(r/'runs/execution_300s_01'/name,out/'failed_attempt_01'/name)
old=out/'PREFLIGHT.json'
if old.exists() and not (out/'PREFLIGHT_INITIAL.json').exists():shutil.copy2(old,out/'PREFLIGHT_INITIAL.json')
old.write_text(json.dumps({'status':'environment_rebuilt_and_300s_collected','available_ros':['humble'],'default_wsl':'Ubuntu-22.04','jazzy_packages_removed':334,'formal_attempts_started':2,'successful_collection_duration_s':300.0037106,'navigation_acceptance':'not_passed_early_tare_completion_recovery_not_completed','raw_data':str(r)},indent=2))
files={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='EVIDENCE_SHA256.json'}
(out/'EVIDENCE_SHA256.json').write_text(json.dumps(files,indent=2))
print('Exported evidence:',len(files),'files')
