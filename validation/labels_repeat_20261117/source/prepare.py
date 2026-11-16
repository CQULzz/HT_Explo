from pathlib import Path
import shutil,json,hashlib
old=Path('/home/lzz/ht_labels_300s_20261116');root=Path('/home/lzz/ht_labels_repeat_20261117');root.mkdir(exist_ok=False)
freeze=json.loads((old/'runs/explicit_labels_campus_300s_01/FREEZE.json').read_text());different=[]
for name,digest in freeze.items():
 p=Path(name)
 if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:different.append(name)
assert not different,different
for p in old.iterdir():
 if p.is_symlink(): (root/p.name).symlink_to(p.resolve(),target_is_directory=p.is_dir())
for name in ['env.sh','simulation.launch.py','recording_qos.yaml','mcap.yaml','initial_support_prior.yaml','boundary.py','startup_collect.py','mapper_setup_4hz.yaml','run.py']:
 text=(old/name).read_text();text=text.replace(str(old),str(root));(root/name).write_text(text)
(root/'env.sh').write_text((root/'env.sh').read_text()+'\nexport ROS_DOMAIN_ID=223\n')
# Distinct communication/display ports only; navigation and simulation settings unchanged.
p=root/'run.py';text=p.read_text().replace("DISPLAY=':101'","DISPLAY=':103'").replace('str(11529)','str(11539)');p.write_text(text)
(root/'setup').mkdir();(root/'runs').mkdir()
for p in (old/'setup').iterdir():
 if p.is_file() and p.suffix in ['.json','.urdf']:shutil.copy2(p,root/'setup'/p.name)
(root/'BUDGET.json').write_text(json.dumps({'maximum_formal_launch_attempts':2,'planned_successful_runs':1,'extra_attempt':'Infrastructure failure retry only, no navigation changes','duration_s':300,'attempts':[],'status':'active','authorization':'2026-11-17 user: 你再探索一次试试'},indent=2,ensure_ascii=False))
(root/'PLAN.json').write_text(json.dumps({'purpose':'Repeat same campus configuration; test recurrence of early completion, no navigation changes','tested_code_commit':'11dd46d5561a0b426ebc800e192d9f42d0d8b00d','repository_documentation_commit':'951eb7af9298cee0553be922866ede04c6d9dce7','duration_basis':'300s wall after inputs ready','original_runtime_freeze_files_verified_unchanged':len(freeze),'old_run':str(old/'runs/explicit_labels_campus_300s_01'),'root':str(root),'domain':223,'gazebo_port':11539,'display':':103','raw_upload':False,'same_explicit_random_seed':'not established; runtime scheduling may vary'},indent=2))
(root/'run_300s.sh').write_text('''set -e
R=/home/lzz/ht_labels_repeat_20261117
source "$R/env.sh"
export HT_ENVELOPE_CASE=helios32_crop_box_explicit_labels
Xvfb :103 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
"$R/venv/bin/python" "$R/run.py" --duration 300 --name explicit_labels_campus_repeat_01 --scene campus > "$R/setup/run.log" 2>&1
''')
print('Ready',root,'verified old freeze files',len(freeze))
