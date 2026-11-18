from pathlib import Path
import json,hashlib,shutil
old=Path('/home/lzz/ht_campus_1200s_20261118');root=Path('/home/lzz/ht_campus_repeat_1200s_20261118');root.mkdir(exist_ok=False)
freeze=json.loads((old/'runs/explicit_labels_campus_1200s_03/FREEZE.json').read_text());bad=[]
for name,digest in freeze.items():
 p=Path(name)
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:bad.append(name)
assert not bad,bad
assert shutil.disk_usage(root).free>40*1024**3
for p in old.iterdir():
 if p.is_symlink():(root/p.name).symlink_to(p.resolve(),target_is_directory=p.is_dir())
for n in ['env.sh','simulation.launch.py','recording_qos.yaml','mcap.yaml','initial_support_prior.yaml','boundary.py','startup_collect.py','mapper_setup_4hz.yaml','run.py']:
 s=(old/n).read_text().replace(str(old),str(root));(root/n).write_text(s)
p=root/'env.sh';p.write_text(p.read_text()+'\nexport ROS_DOMAIN_ID=219\n')
p=root/'run.py';s=p.read_text().replace("DISPLAY=':105'","DISPLAY=':106'").replace('str(11549)','str(11559)');p.write_text(s)
(root/'setup').mkdir();(root/'runs').mkdir();(root/'analysis').mkdir()
for p in (old/'setup').iterdir():
 if p.is_file() and p.suffix in ['.json','.urdf']:shutil.copy2(p,root/'setup'/p.name)
for n in ['CAMPUS_REFERENCE_05M.npz','CAMPUS_REFERENCE.json','REFERENCE_GROUND_PROXY.npz','REFERENCE_GROUND_PROXY.json']:shutil.copy2(old/'analysis'/n,root/'analysis'/n)
(root/'BUDGET.json').write_text(json.dumps({'maximum_formal_launch_attempts':2,'planned_successful_runs':1,'extra_attempt':'Infrastructure failure retry only; no navigation changes','duration_s':1200,'attempts':[],'status':'active','authorization':'2026-11-18 user requested another campus run after reviewing failure and repeated backtracking'},indent=2))
(root/'PLAN.json').write_text(json.dumps({'purpose':'Repeat current navigation for1200s, emphasize backtracking/target switches and recurrence of HT_CONTEXT_INVALID','tested_navigation_commit':'11dd46d5561a0b426ebc800e192d9f42d0d8b00d','repository_documentation_commit':'e46bf8a00dbc00e86473a3e14f9b4e48394c373e','baseline_run':str(old/'runs/explicit_labels_campus_1200s_03'),'original_freeze_files_verified_unchanged':len(freeze),'duration_basis':'1200s wall clock after inputs ready, even after finish/parking; sim advancement reported separately','domain':219,'gazebo_port':11559,'display':':106','navigation_changes':False,'collector':'Reuse previous tested malformed-diagnostic preservation fix','random_seed':'No common explicit seed established; stochastic/scheduling differences retained and disclosed','preflight_other_simulators':'None detected at preflight; do not interrupt unrelated workloads if any appear','raw_upload':False,'coverage':'Repeat same independent campus surface/ground-connectivity proxy; not ground-truth completeness percentage'},indent=2))
(root/'run_1200s.sh').write_text('''set -e
R=/home/lzz/ht_campus_repeat_1200s_20261118
source "$R/env.sh"
export HT_ENVELOPE_CASE=helios32_crop_box_explicit_labels
Xvfb :106 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
"$R/venv/bin/python" "$R/run.py" --duration 1200 --name explicit_labels_campus_repeat_1200s_01 --scene campus > "$R/setup/run.log" 2>&1
''')
s=Path('/mnt/d/HT-Campus-1200s-20261118/monitor.py').read_text().replace(str(old),str(root)).replace('explicit_labels_campus_1200s_03','explicit_labels_campus_repeat_1200s_01');Path('/mnt/d/HT-Campus-Repeat-1200s-20261118/monitor.py').write_text(s)
print('Ready',root,'baseline freeze verified',len(freeze))
