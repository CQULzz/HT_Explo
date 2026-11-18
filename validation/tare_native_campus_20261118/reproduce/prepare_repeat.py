from pathlib import Path
import json,shutil,ast
old=Path('/home/lzz/tare_native_campus_20261118');root=Path('/home/lzz/tare_native_campus_repeat_20261118');root.mkdir(exist_ok=False)
for name in ['setup','runs','analysis']:(root/name).mkdir()
(root/'project').symlink_to(old/'project',target_is_directory=True);(root/'BUDGET.json').symlink_to(old/'BUDGET.json')
for name in ['env.sh','simulation.launch.py','run.py','observer.py','mission_stop.py','campus.world','recording_qos.yaml','mcap.yaml']:
 s=(old/name).read_text().replace(str(old),str(root));s=s.replace("CASE='native_campus_01'","CASE='native_campus_02'").replace('ROS_DOMAIN_ID=205','ROS_DOMAIN_ID=203').replace('11589','11599').replace("DISPLAY=':109'","DISPLAY=':110'");(root/name).write_text(s)
 if name.endswith('.py'):ast.parse(s)
for name in ['CAMPUS_REFERENCE_05M.npz','CAMPUS_REFERENCE.json','REFERENCE_GROUND_PROXY.npz','REFERENCE_GROUND_PROXY.json']:shutil.copy2(old/'analysis'/name,root/'analysis'/name)
plan=json.loads((old/'PLAN.json').read_text());plan.update(repeat_of=str(old/'runs/native_campus_01'),repeat_purpose='Same-configuration recurrence check after local geometry persistent blockage; no parameter tuning',isolation={'domain':203,'gazebo_port':11599,'display':':110'});(root/'PLAN.json').write_text(json.dumps(plan,indent=2))
(root/'run_native.sh').write_text('set -e\nR=/home/lzz/tare_native_campus_repeat_20261118\nsource "$R/env.sh"\nXvfb :110 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &\nxvfb_pid=$!\ntrap \'kill "$xvfb_pid" 2>/dev/null || true\' EXIT\npython3 "$R/run.py" > "$R/setup/run.log" 2>&1\n')
w=Path('/mnt/d/TARE-Native-Campus-20261118');s=(w/'monitor.py').read_text().replace(str(old),str(root)).replace('native_campus_01','native_campus_02');(w/'monitor_repeat.py').write_text(s)
for name in ['postprocess_native.py','assess_coverage.py','end_motion.py','analyze_backtracking.py']:
 s=(w/name).read_text().replace(str(old),str(root)).replace('native_campus_01','native_campus_02').replace('ROS_DOMAIN_ID=205','ROS_DOMAIN_ID=203').replace('DISPLAY=:109','DISPLAY=:110');(w/('repeat_'+name)).write_text(s);ast.parse(s)
for tag,script in [('postprocess','repeat_postprocess_native.py'),('coverage','repeat_assess_coverage.py')]:
 (w/('repeat_'+tag+'.sh')).write_text('set -e\nsource '+str(root)+'/env.sh\n/usr/bin/python3 /mnt/d/TARE-Native-Campus-20261118/'+script+' > '+str(root)+'/setup/'+tag+'.log 2>&1\n')
print('Prepared exact native parameter repeat, shared ledger still records first case')
