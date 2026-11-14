from pathlib import Path
import json,csv,math,hashlib,shutil
root=Path('/home/lzz/ht_campus_pcd_20261114');out=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/campus_pcd_20261114')
results={};binaries=[]
for case in ['campus_600s_02','user_pcd_600s_02']:
    r=root/'runs'/case;rows=list(csv.DictReader((r/'observations/metrics.csv').open()))
    columns=['elapsed_s','time','x','y','z','yaw','distance_m','cmd_linear','cmd_angular']
    invalid=[(i,k) for i,row in enumerate(rows) for k in columns if not math.isfinite(float(row[k]))]
    assert not invalid
    result=json.loads((r/'RESULT.json').read_text());audit=json.loads((r/'COMMAND_AUDIT.json').read_text())
    assert result['collection_complete'] and result['freeze_unchanged'] and audit['passed']
    freeze=json.loads((r/'FREEZE.json').read_text());nav={k:v for k,v in freeze.items() if '/install_native/tare_planner/lib/' in k or '/install_gate/cmu_local_planner_ht/lib/' in k or k.endswith('student_best_epoch_weights.pth')};binaries.append(nav)
    results[case]={'finite_motion_metrics':True,'metric_rows':len(rows),'collection_complete':True,'freeze_unchanged':True,'allowed_command_audit_passed':True}
assert binaries[0]==binaries[1]
results['same_navigation_binaries_and_weights']=True
(out/'DATA_QUALITY.json').write_text(json.dumps(results,indent=2))
for name in ['observer_nonfinite_test.log','campus_sdf_check.log']:
    p=root/'setup'/name
    if p.exists():shutil.copy2(p,out/'source'/name)
for name in ['finalize_case_videos.py','verify_case_data.py']:
    shutil.copy2(Path('/mnt/d/HT-Execution-300s/setup')/name,out/'source'/name)
print(json.dumps(results,indent=2))
