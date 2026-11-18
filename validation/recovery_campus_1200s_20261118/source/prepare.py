from pathlib import Path
import ast, hashlib, json, shutil, subprocess
old=Path('/home/lzz/ht_campus_repeat_1200s_20261118')
root=Path('/home/lzz/ht_recovery_campus_1200s_20261118')
candidate=Path('/home/lzz/ht_window_recovery_20261118/candidate')
repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes')
work=Path('/mnt/d/HT-Recovery-Campus-1200s-20261118')
freeze=json.loads((old/'runs/explicit_labels_campus_repeat_1200s_01/FREEZE.json').read_text())
bad=[n for n,h in freeze.items() if not Path(n).is_file() or hashlib.sha256(Path(n).read_bytes()).hexdigest()!=h]
assert not bad,bad
runtime=json.loads((repo/'validation/window_recovery_20261118/RUNTIME.json').read_text())
for k,h in runtime['frozen'].items():
 p=candidate/'src/cmu_local_planner_ht'/k[7:] if k.startswith('source/') else candidate/'install/cmu_local_planner_ht/lib/cmu_local_planner_ht'/k[7:]
 assert hashlib.sha256(p.read_bytes()).hexdigest()==h,str(p)
assert shutil.disk_usage(old).free>40*1024**3
root.mkdir(exist_ok=False)
for p in old.iterdir():
 if p.is_symlink():
  target=candidate/'install' if p.name=='install_gate' else p.resolve()
  (root/p.name).symlink_to(target,target_is_directory=p.is_dir())
for n in ['setup','runs','analysis']:(root/n).mkdir()
for n in ['env.sh','simulation.launch.py','recording_qos.yaml','mcap.yaml','initial_support_prior.yaml','boundary.py','startup_collect.py','mapper_setup_4hz.yaml','run.py']:
 (root/n).write_text((old/n).read_text().replace(str(old),str(root)))
p=root/'env.sh';p.write_text(p.read_text()+f'\nsource {candidate}/install/setup.bash\nexport ROS_DOMAIN_ID=209\nexport ROS_LOG_DIR={root}/ros_logs\n')
for p in (old/'setup').iterdir():
 if p.is_file() and p.suffix in ['.json','.urdf']:shutil.copy2(p,root/'setup'/p.name)
for n in ['CAMPUS_REFERENCE_05M.npz','CAMPUS_REFERENCE.json','REFERENCE_GROUND_PROXY.npz','REFERENCE_GROUND_PROXY.json']:shutil.copy2(old/'analysis'/n,root/'analysis'/n)
p=root/'run.py';s=p.read_text().replace("DISPLAY=':106'","DISPLAY=':107'").replace('str(11559)','str(11569)')
s=s.replace("files += [ROOT/'initial_support_prior.yaml',ROOT/'startup_collect.py']",f"files += [p for p in Path('{candidate}/src/cmu_local_planner_ht').rglob('*') if p.is_file()]\n files += [ROOT/'setup/NAVIGATION_EXPECTED.json']\n files += [ROOT/'initial_support_prior.yaml',ROOT/'startup_collect.py']")
s=s.replace("subprocess.run([str(PY),'-c',preflight],check=True)","subprocess.run([str(PY),'-c',preflight],check=True)\n prefix=subprocess.check_output(['ros2','pkg','prefix','cmu_local_planner_ht'],text=True).strip()\n assert Path(prefix).resolve()==Path('/home/lzz/ht_window_recovery_20261118/candidate/install/cmu_local_planner_ht').resolve(),prefix")
s=s.replace("HT_HISTORY_DUMP=str(out/'ht_history.npz'))","HT_HISTORY_DUMP=str(out/'ht_history.npz'),HT_CONTEXT_DUMP=str(out/'contexts'),HT_CONTEXT_WARMUP_S='0',HT_CONTEXT_INTERVAL_S='60')")
s=s.replace("'baseline_commit':'11dd46d5561a0b426ebc800e192d9f42d0d8b00d'","'baseline_commit':'5ba8bb5','repository_commit':'6ea8d76f66f299f1c06dbf84c5330a4ebb837352'")
s=s.replace("'change':'Nominal 32", "'change':'Return recovery remains enabled after exploration finish; validated partial prefixes at HT context frontier; unchanged threshold/TTL/TARE. Nominal 32")
needle="if not dumped and (out/'observations/START.json').exists():"
replacement=needle+'''
    actual=[]
    for proc in Path('/proc').iterdir():
     if not proc.name.isdigit():continue
     try:
      exe=(proc/'exe').resolve();name=exe.name
      if name not in ['localPlanner','pathFollower']:continue
      if b'ROS_DOMAIN_ID=209' not in (proc/'environ').read_bytes().split(b'\\0'):continue
      expected=Path('/home/lzz/ht_window_recovery_20261118/candidate/install/cmu_local_planner_ht/lib/cmu_local_planner_ht')/name
      assert exe==expected.resolve(),str(exe)
      actual.append({'pid':int(proc.name),'executable':str(exe),'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()})
     except (FileNotFoundError,ProcessLookupError,PermissionError):continue
    assert {p['executable'].split('/')[-1] for p in actual}=={'localPlanner','pathFollower'},actual
    (out/'ACTUAL_NAVIGATION.json').write_text(json.dumps(actual,indent=2))'''
assert needle in s;s=s.replace(needle,replacement);p.write_text(s);ast.parse(s)
(root/'setup/NAVIGATION_EXPECTED.json').write_text(json.dumps(runtime,indent=2))
plan={'purpose':'1200s campus closed loop of HT-window/return recovery fixes','navigation_code_commit':'5ba8bb5','repository_commit':'6ea8d76f66f299f1c06dbf84c5330a4ebb837352','baseline_run':str(old/'runs/explicit_labels_campus_repeat_1200s_01'),'original_frozen_files_unchanged':len(freeze),'candidate_runtime':runtime,'duration_s':1200,'duration_basis':'Wall-clock after input readiness, continue after finish/parking; simulation advance separately reported','domain':209,'gazebo_port':11569,'display':':107','context_capture':'Original inference inputs every60s, no warmup burst; diagnostic serialization is additional host I/O and not new terrain evidence','random_seed':'No common explicit seed; trajectories are not a controlled performance attribution','raw_upload':False}
(root/'PLAN.json').write_text(json.dumps(plan,indent=2))
(root/'BUDGET.json').write_text(json.dumps({'maximum_formal_launch_attempts':2,'planned_successful_runs':1,'extra_attempt':'Infrastructure retry only; no extra navigation candidate','duration_s':1200,'attempts':[],'status':'active','authorization':'2026-11-18 user requested another test after HT window/recovery fixes'},indent=2))
(root/'run_1200s.sh').write_text(f'''set -e
R={root}
source "$R/env.sh"
export HT_ENVELOPE_CASE=helios32_crop_box_explicit_labels_recovery_fix
Xvfb :107 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
"$R/venv/bin/python" "$R/run.py" --duration 1200 --name recovery_campus_1200s_01 --scene campus > "$R/setup/run.log" 2>&1
''')
s=Path('/mnt/d/HT-Campus-Repeat-1200s-20261118/monitor.py').read_text().replace(str(old),str(root)).replace('explicit_labels_campus_repeat_1200s_01','recovery_campus_1200s_01')
(work/'monitor.py').write_text(s)
print(json.dumps({'prepared':str(root),'original_freeze_verified':len(freeze),'candidate_binary_hashes':{k:v for k,v in runtime['frozen'].items() if k.startswith('binary/')}},indent=2))
