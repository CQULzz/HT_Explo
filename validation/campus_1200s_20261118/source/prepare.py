from pathlib import Path
import shutil,json,hashlib,subprocess,os
old=Path('/home/lzz/ht_labels_repeat_20261117');root=Path('/home/lzz/ht_campus_1200s_20261118');root.mkdir(exist_ok=False)
freeze=json.loads((old/'runs/explicit_labels_campus_repeat_01/FREEZE.json').read_text());bad=[]
for name,digest in freeze.items():
 p=Path(name)
 if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:bad.append(name)
assert not bad,bad
assert shutil.disk_usage(root).free>40*1024**3
for p in old.iterdir():
 if p.is_symlink():(root/p.name).symlink_to(p.resolve(),target_is_directory=p.is_dir())
for name in ['env.sh','simulation.launch.py','recording_qos.yaml','mcap.yaml','initial_support_prior.yaml','boundary.py','startup_collect.py','mapper_setup_4hz.yaml','run.py']:
 text=(old/name).read_text().replace(str(old),str(root));(root/name).write_text(text)
p=root/'run.py';text=p.read_text().replace("DISPLAY=':103'","DISPLAY=':105'").replace('str(11539)','str(11549)').replace('free<7*1024**3','free<40*1024**3');p.write_text(text)
(root/'env.sh').write_text((root/'env.sh').read_text()+'\nexport ROS_DOMAIN_ID=221\n')
(root/'setup').mkdir();(root/'runs').mkdir()
for p in (old/'setup').iterdir():
 if p.is_file() and p.suffix in ['.json','.urdf']:shutil.copy2(p,root/'setup'/p.name)
(root/'BUDGET.json').write_text(json.dumps({'maximum_formal_launch_attempts':2,'planned_successful_runs':1,'extra_attempt':'Infrastructure failure retry only; no candidate changes','duration_s':1200,'attempts':[],'status':'active','authorization':'2026-11-18 user requested one 20min campus exploration and assessment of complete exploration'},indent=2))
(root/'PLAN.json').write_text(json.dumps({'goal':'Assess whether current frozen configuration can fully explore campus in one 1200s wall-clock run; no navigation changes','tested_code_commit':'11dd46d5561a0b426ebc800e192d9f42d0d8b00d','repository_documentation_commit':'369d2dd75bea72f7eb96f6370b2067ccbe4e1519','scene':'official CMU campus','duration_basis':'1200s wall-clock after >=5 scans and >=5 HT maps; sim advancement reported separately','original_runtime_freeze_verified_unchanged':len(freeze),'domain':221,'gazebo_port':11549,'display':':105','other_workload':'Independent AEDE ariadne benchmark observed running at preflight; left untouched; CPU/GPU overlap is a confounder','complete_exploration_acceptance':['Full 1200s evidence even after early finish/parking','Inspect phase-wise actual motion and observed-area growth','Report finish/return and frontier/global task status independently','Assess observations against independent scene reference; software zero counters alone cannot establish full campus coverage; unsupported complete-coverage claims prohibited'],'video_end_policy':'Label end of actual acquisition explicitly; no unlabeled artificial pause presented as vehicle stopping','raw_upload':False,'random_seed':'No same explicit seed established in previous runs; retain current policy, do not attribute trajectory differences to code changes'},indent=2))
(root/'run_1200s.sh').write_text('''set -e
R=/home/lzz/ht_campus_1200s_20261118
source "$R/env.sh"
export HT_ENVELOPE_CASE=helios32_crop_box_explicit_labels
Xvfb :105 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
"$R/venv/bin/python" "$R/run.py" --duration 1200 --name explicit_labels_campus_1200s_01 --scene campus > "$R/setup/run.log" 2>&1
''')
print('Prepared',root,'original frozen files verified',len(freeze),flush=True)
