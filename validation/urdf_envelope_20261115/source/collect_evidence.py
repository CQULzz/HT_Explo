from pathlib import Path
import shutil,json,hashlib,re
root=Path('/home/lzz/ht_urdf_compare_20261115');out=Path('/mnt/d/HT-URDF-Compare-20261115/analysis');out.mkdir(exist_ok=True)
workspace=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');dest=workspace/'validation/urdf_envelope_20261115';dest.mkdir(parents=True,exist_ok=True)
for variant in ['baseline','urdf']:
    run=root/'runs'/f'{variant}_campus_600s_01';target=out/variant;target.mkdir(exist_ok=True)
    shutil.copy2(run/'COMMAND_AUDIT.json',target/'COMMAND_AUDIT.json')
    exits=[]
    for line in (run/'simulation.log').read_text(errors='replace').splitlines():
        if 'process has died' in line:
            exits.append(line.split(', cmd ',1)[0])
    (target/'SHUTDOWN_CHILD_EXITS.log').write_text('\n'.join(exits)+'\n')
    for name in ['START.json']:
        shutil.copy2(run/'observations'/name,target/name)
for name in ['URDF_ENVELOPE.json','scout_expanded.urdf','ctest.log','build.log','recovery_regression.log']:
    if (root/'setup'/name).exists():shutil.copy2(root/'setup'/name,out/name)
for name in ['EXPERIMENT_SCOPE.json','BUDGET.json']:
    shutil.copy2(root/name,out/name)
source=Path('/mnt/d/HT-URDF-Compare-20261115/setup/eletranskit_scout/src/ele_scout_kit/urdf/scout_sensor_rack.urdf.xacro');shutil.copy2(source,out/'scout_sensor_rack.urdf.xacro')
checked=[]
for p in (workspace/'src/cmu_local_planner_ht').rglob('*'):
    if p.is_file():
        compiled=root/'project/src/cmu_local_planner_ht'/p.relative_to(workspace/'src/cmu_local_planner_ht')
        assert p.read_bytes()==compiled.read_bytes(),str(p)
        checked.append({'file':str(p.relative_to(workspace)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(out/'WORKSPACE_TESTED_SOURCE_CHECK.json').write_text(json.dumps({'passed':True,'files':checked},indent=2))
for p in out.iterdir():
    if p.is_file():shutil.copy2(p,dest/p.name)
    elif p.is_dir():shutil.copytree(p,dest/p.name,dirs_exist_ok=True)
recipe=dest/'source';recipe.mkdir(exist_ok=True)
setup=Path('/mnt/d/HT-URDF-Compare-20261115/setup')
for p in setup.glob('*'):
    if p.is_file() and p.suffix in ['.py','.sh']:shutil.copy2(p,recipe/p.name)
video_tools=Path('/mnt/d/HT-URDF-Compare-20261115/video_tools')
shutil.copytree(video_tools,recipe/'video_tools',dirs_exist_ok=True)
# Include the complete small active harness, not large runtime snapshots/MCAP.
for name in ['run.py','simulation.launch.py','startup_collect.py','env.sh','mcap.yaml','recording_qos.yaml']:
    shutil.copy2(root/name,recipe/name)
shutil.copytree(root/'runtime',recipe/'runtime',dirs_exist_ok=True)
print('Compact evidence collected at',dest)
