from pathlib import Path
import json,shutil,xml.etree.ElementTree as ET
root=Path('/home/lzz/ht_helios_collision_20261115');old=Path('/home/lzz/ht_urdf_compare_20261115');workspace=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');assets=root/'common_sensor'
tree=ET.parse(assets/'lidar.urdf');robot=tree.getroot()
if robot.find("link[@name='base_link']") is None:
    ET.SubElement(robot,'link',name='base_link');j=ET.SubElement(robot,'joint',name='sensor_to_scout_base',type='fixed');ET.SubElement(j,'parent',link='sensor');ET.SubElement(j,'child',link='base_link');ET.SubElement(j,'origin',xyz='-0.1725 0 -0.5502',rpy='0 0 0');tree.write(assets/'lidar.urdf',encoding='unicode')
for name in ['config','mapper_source','install_mapper','install_cmu','install_native','venv','install_gate']:
    if not (root/name).exists():(root/name).symlink_to(old/name,target_is_directory=True)
(root/'scene_assets').mkdir(exist_ok=True)
for name,source in [('campus.world',old/'scene_assets/campus.world'),('CAMPUS_MANIFEST.json',old/'scene_assets/CAMPUS_MANIFEST.json'),('indoor.world',old/'common_sensor/indoor.world')]:shutil.copy2(source,root/'scene_assets'/name)
(root/'runtime').mkdir(exist_ok=True)
for scene in ['campus','indoor']:shutil.copy2(old/'runtime/campus_urdf_local_planner.launch.xml',root/'runtime'/f'{scene}_local_planner.launch.xml')
for name in ['mapper_setup_4hz.yaml','recording_qos.yaml','mcap.yaml','startup_collect.py','boundary.py']:shutil.copy2(old/name,root/name)
shutil.copy2(workspace/'tools/helios32_sim/simulation.launch.py',root/'simulation.launch.py')
env=(old/'env.sh').read_text().replace('ROS_DOMAIN_ID=226','ROS_DOMAIN_ID=230');env+='\nsource '+str(root/'install/setup.bash')+'\nexport HT_HELIOS_ROOT='+str(root)+'\nexport ROS_LOG_DIR='+str(root/'ros_logs')+'\nexport GAZEBO_PLUGIN_PATH='+str(root/'install/helios32_sim/lib')+':$GAZEBO_PLUGIN_PATH\n';(root/'env.sh').write_text(env)
runner=(old/'run.py').read_text().replace(str(old),str(root));runner=runner.replace("'envelope:='+os.environ['HT_ENVELOPE_CASE']", "'scene:='+scene");runner=runner.replace("DISPLAY=':93'","DISPLAY=':96'").replace('str(11517)','str(11519)');runner=runner.replace("'surface_sensor_ground_offset_m:=0.75'","'surface_sensor_ground_offset_m:=0.78499'")
runner=runner.replace("files += [ROOT/'setup/URDF_ENVELOPE.json',ROOT/'setup/scout_expanded.urdf']", "files += [p for p in (ROOT/'install/helios32_sim').rglob('*') if p.is_file()]\n files += [ROOT/'setup/URDF_ENVELOPE.json',ROOT/'setup/scout_expanded.urdf']")
runner=runner.replace("'change':'opt-in pinned URDF body box; unchanged TARE/HT scores/controller; conservative circle support radius covers full body'", "'change':'Nominal 32 nonuniform Helios rays, opaque pinned Scout meshes, matching body/lidar extrinsics and yaw registration; unchanged HT safety thresholds and TARE policy'")
runner=runner.replace("def freeze():", "TOPICS += ['/rslidar_points','/helios_sim/scan_status']\n\ndef freeze():");(root/'run.py').write_text(runner)
runner=runner.replace("'scene:='+scene,'scene:='+scene","'scene:='+scene")
runner=runner.replace("'baseline_commit':'d368516305d4b8c55f9039a6d96900aa1c5823b3'","'baseline_commit':'309cd3b60630c9f934477c76adaa7fe518242a98'")
runner=runner.replace("files += [ROOT/'startup_collect.py']","files += [p for p in Path('/home/lzz/ht_urdf_compare_20261115/project/src/cmu_local_planner_ht').rglob('*') if p.is_file()]\n files += [ROOT/'startup_collect.py']")
runner=runner.replace("'/pathFollower','/cupy_to_ht_bridge'","'/pathFollower','/cupy_to_ht_bridge','/vehicleSimulator'")
(root/'run.py').write_text(runner)
for name in ['URDF_ENVELOPE.json','scout_expanded.urdf']:
    if not (root/'setup'/name).exists():shutil.copy2(old/'setup'/name,root/'setup'/name)
budget=root/'BUDGET.json'
if not budget.exists():budget.write_text(json.dumps({'maximum_formal_launch_attempts':2,'planned_runs':[{'scene':'campus','duration_s':600}],'extra_attempt':'infrastructure failure retry only','static_probes_done':['transparent','opaque','blind'],'attempts':[]},indent=2))
print('Prepared isolated corrected sensor chain')
