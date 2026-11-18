from pathlib import Path
import ast, hashlib, json, shutil
old=Path('/home/lzz/ht_recovery_campus_1200s_20261118')
root=Path('/home/lzz/ht_campus_to_finish_20261118')
work=Path('/mnt/d/HT-Campus-To-Finish-20261118')
freeze=json.loads((old/'runs/recovery_campus_1200s_01/FREEZE.json').read_text())
assert all(Path(n).is_file() and hashlib.sha256(Path(n).read_bytes()).hexdigest()==h for n,h in freeze.items()),'Previous runtime changed'
assert shutil.disk_usage(old).free>80*1024**3
root.mkdir(exist_ok=False)
for p in old.iterdir():
 if p.is_symlink():(root/p.name).symlink_to(p.resolve(),target_is_directory=p.is_dir())
for n in ['setup','runs','analysis']:(root/n).mkdir()
for p in (old/'setup').iterdir():
 if p.is_file() and p.suffix in ['.json','.urdf']:shutil.copy2(p,root/'setup'/p.name)
for n in ['CAMPUS_REFERENCE_05M.npz','CAMPUS_REFERENCE.json','REFERENCE_GROUND_PROXY.npz','REFERENCE_GROUND_PROXY.json']:shutil.copy2(old/'analysis'/n,root/'analysis'/n)
for n in ['env.sh','simulation.launch.py','recording_qos.yaml','mcap.yaml','initial_support_prior.yaml','boundary.py','startup_collect.py','mapper_setup_4hz.yaml','run.py']:(root/n).write_text((old/n).read_text().replace(str(old),str(root)))
(root/'mission_stop.py').write_text((work/'mission_stop.py').read_text())
p=root/'env.sh';p.write_text(p.read_text()+f'\nexport ROS_DOMAIN_ID=207\nexport ROS_LOG_DIR={root}/ros_logs\n')
p=root/'startup_collect.py';s=p.read_text().replace('import rclpy\n','import rclpy\nfrom mission_stop import MissionStopRule\n')
s=s.replace("def command(self,m):self.cmd=(m.twist.linear.x,m.twist.angular.z);self.count['commands']+=1", "def command(self,m):self.cmd=(m.twist.linear.x,m.twist.angular.z);self.last['command']=self.get_clock().now().nanoseconds/1e9;self.count['commands']+=1")
s=s.replace("if not a.attach:n.start_pub.publish(Bool(data=True))", "base=lambda:(n.position[0]-.1725*math.cos(n.yaw),n.position[1]-.1725*math.sin(n.yaw))\n rule=MissionStopRule(base());missing_since=None\n if not a.attach:n.start_pub.publish(Bool(data=True))")
s=s.replace("while time.monotonic()-n.start<a.duration:", "while a.duration<=0 or time.monotonic()-n.start<a.duration:")
s=s.replace("if time.monotonic()-last>=.5:n.row();last=time.monotonic()", '''if time.monotonic()-last>=.5:
    n.row();last=time.monotonic()
    if a.duration<=0:
     now=n.get_clock().now().nanoseconds/1e9;elapsed=last-n.start
     fresh=(n.last_ht is not None and 0<=now-n.last_ht<=1. and 0<=now-n.last.get('odom',0)<=.2 and 0<=now-n.last.get('scan',0)<=2. and 0<=now-n.last.get('command',0)<=.25)
     outcome=rule.update(elapsed,base(),n.cmd,n.finish,fresh,len(n.free)*.125)
     status=rule.status(elapsed,base());status.update(distance_m=n.distance,finish=n.finish,command=list(n.cmd),inputs_fresh=fresh,sampled_free_volume_m3=len(n.free)*.125)
     (a.output/'RUN_STATUS.json').write_text(json.dumps(status,indent=2))
     if outcome!='RUNNING':break
     missing_since=None if fresh else (elapsed if missing_since is None else missing_since)
     if missing_since is not None and elapsed-missing_since>=30:
      rule.outcome='INPUTS_STALE';raise RuntimeError('Required live inputs stale for30s')''')
s=s.replace("summary={'elapsed_s':", "summary={'mission_outcome':rule.outcome,'mission_complete':rule.outcome=='RETURNED_AND_STOPPED','terminal_status':rule.status(time.monotonic()-n.start,base()),'elapsed_s':")
p.write_text(s);ast.parse(s)
p=root/'run.py';s=p.read_text().replace("DISPLAY=':107'","DISPLAY=':108'").replace('str(11569)','str(11579)').replace('ROS_DOMAIN_ID=209','ROS_DOMAIN_ID=207')
s=s.replace("files += [ROOT/'initial_support_prior.yaml',ROOT/'startup_collect.py']", "files += [ROOT/'initial_support_prior.yaml',ROOT/'startup_collect.py',ROOT/'mission_stop.py']")
s=s.replace("'requested_duration_s':duration", "'requested_duration_s':None,'termination_mode':'task_outcome'" )
s=s.replace("'repository_commit':'6ea8d76f66f299f1c06dbf84c5330a4ebb837352'", "'repository_commit':'87133ad5819a9d021d69a7b84bd1ff40197bd77a'")
s=s.replace("if time.monotonic()-started>duration+420:raise RuntimeError('Observer deadline exceeded')", "if not (out/'observations/START.json').exists() and time.monotonic()-started>420:raise RuntimeError('Startup deadline exceeded')\n   if __import__('shutil').disk_usage(ROOT).free<40*1024**3:raise RuntimeError('Raw evidence reserve below40GiB')")
s=s.replace("result['collection_complete']=result['summary']['elapsed_s']>=duration", "result['collection_complete']=result['summary']['mission_outcome'] in ['RETURNED_AND_STOPPED','PERSISTENT_BLOCKED'];result['mission_complete']=result['summary']['mission_complete'];result['mission_outcome']=result['summary']['mission_outcome']")
p.write_text(s);ast.parse(s)
plan={'purpose':'Run unchanged repaired campus navigation until exploration finishes and returns, rather than fixed20min','navigation_code_commit':'5ba8bb5','repository_commit':'87133ad5819a9d021d69a7b84bd1ff40197bd77a','resumption':'Fresh start; previous simulation terminated and no full planner checkpoint exists','old_frozen_files_verified':len(freeze),'runtime_limit_s':None,'success_rule':'finish=true, base within0.5m initial, fresh inputs, zero commands and <=0.05m movement continuously20s','failure_rule':'Persistent XY pocket<=0.15m for300s with fresh inputs, unchanged finish phase, and <=50m3 observation proxy increase; classify blocked, never completed. Child/input/disk failure separately retained.','domain':207,'gazebo_port':11579,'display':':108','navigation_changes':False,'observer_changes':'Read-only outcome termination plus existing start signal;7 stop-rule regression tests pass','parameters':'Unchanged safety/HT/history/model/TARE/vehicle parameters; original context inputs every60s','random_seed':'No common explicit seed established','raw_upload':False}
(root/'PLAN.json').write_text(json.dumps(plan,indent=2));(root/'BUDGET.json').write_text(json.dumps({'maximum_formal_launch_attempts':2,'planned_successful_runs':1,'extra_attempt':'Infrastructure failure retry only; no new navigation candidate','termination':'task_outcome','duration_s':None,'attempts':[],'status':'active','authorization':'2026-11-18 user asked to run the task to completion'},indent=2))
(root/'run_to_finish.sh').write_text(f'''set -e
R={root}
source "$R/env.sh"
export HT_ENVELOPE_CASE=helios32_crop_box_explicit_labels_to_finish
Xvfb :108 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
"$R/venv/bin/python" "$R/run.py" --duration 0 --name campus_to_finish_01 --scene campus > "$R/setup/run.log" 2>&1
''')
monitor=Path('/mnt/d/HT-Recovery-Campus-1200s-20261118/monitor_live.py').read_text().replace(str(old),str(root)).replace('recovery_campus_1200s_01','campus_to_finish_01')
monitor += "\np=r/'observations/RUN_STATUS.json'\nif p.exists():print('TASK_STATUS',p.read_text())\n"
(work/'monitor.py').write_text(monitor)
print('Prepared',root,'original frozen files verified',len(freeze))
