from pathlib import Path
import json,shutil,subprocess,hashlib
root=Path('/home/lzz/ht_campus_pcd_20261114');out=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/campus_pcd_20261114');out.mkdir(exist_ok=True)
template=Path('/mnt/d/HT-Execution-300s/setup/analyze_600s.py').read_text()
for case in ['campus_600s_02','user_pcd_600s_02']:
    if not (root/'runs'/case/'RESULT.json').exists():continue
    s=template.replace("root=Path('/home/lzz/ht_600s_20261114');run=root/'runs/execution_600s_01'",f"root=Path('{root}');run=root/'runs/{case}'")
    s=s.replace("validation/execution_600s_20261114'",f"validation/campus_pcd_20261114/{case}'")
    s=s.replace("for name in ['prepare_600s.py','run_600s.sh','analyze_600s.py']:","for name in ['prepare_campus_pcd.py','fix_campus_startup.py','run_campus_pcd_retry.sh']:")
    target=root/'setup'/f'analyze_{case}.py';target.write_text(s)
    subprocess.run(['python3',str(target)],check=True)
for name in ['run.py','simulation.launch.py','startup_collect.py','boundary.py','env.sh','BUDGET.json','recording_qos.yaml']:
    shutil.copy2(root/name,out/name)
(out/'source').mkdir(exist_ok=True)
for name in ['prepare_campus_pcd.py','fix_campus_startup.py','fix_pcd_observer.py','run_campus_pcd.sh','run_campus_pcd_retry.sh','run_pcd_retry.sh','export_campus_pcd.py','make_case_video_tools.py','pcd_prepare_base.py','pcd_boundary_base.py','inspect_bad_waypoints.py']:
    shutil.copy2(Path('/mnt/d/HT-Execution-300s/setup')/name,out/'source'/name)
for name in ['SCENE_MANIFEST.json']:
    shutil.copy2(Path('/home/lzz/pcd_test_20261110/runtime')/name,out/'source'/name)
for name in ['PCD_IDENTITY.json','RECOVERY.json']:
    shutil.copy2(Path('/home/lzz/pcd_test_20261110/source')/name,out/'source'/name)
for p in (root/'scene_assets').iterdir():
    if p.is_file():shutil.copy2(p,out/'source'/p.name)
failed=out/'failed_campus_01';failed.mkdir(exist_ok=True)
for name in ['RESULT.json','simulation.log','observer.log','model.log','mapper.log']:
    p=root/'runs/campus_600s_01'/name
    if p.exists():shutil.copy2(p,failed/name)
failed=out/'failed_pcd_01';failed.mkdir(exist_ok=True)
for name in ['RESULT.json','simulation.log','observer.log','model.log','mapper.log','NONFINITE_WAYPOINTS.json']:
    p=root/'runs/user_pcd_600s_01'/name
    if p.exists():shutil.copy2(p,failed/name)
for name in ['initial_run.py','initial_simulation.launch.py','collect_before_nonfinite.py','observer_nonfinite_test.log']:
    p=root/'setup'/name
    if p.exists():shutil.copy2(p,out/'source'/name)
(out/'.gitattributes').write_text('*.csv -text -whitespace\n*.log -text -whitespace\n')
manifest=json.loads((root/'scene_assets/CAMPUS_MANIFEST.json').read_text())
assert all(hashlib.sha256((Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus')/name).read_bytes()).hexdigest()==h for name,h in manifest['files'].items())
(out/'ASSET_CHECK.json').write_text(json.dumps({'campus_assets_match_manifest':True,'pcd_array_sha256':hashlib.sha256(Path('/home/lzz/pcd_test_20261110/source/runtime/local_map.npy').read_bytes()).hexdigest()},indent=2))
print('Exported compact campus/PCD evidence',out)
