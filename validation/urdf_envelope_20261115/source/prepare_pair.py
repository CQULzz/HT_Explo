from pathlib import Path
import json,shutil,os
root=Path('/home/lzz/ht_urdf_compare_20261115');old=Path('/home/lzz/ht_campus_pcd_20261114')
project=Path('/home/lzz/HT_Explo_execution_20261113');newproj=root/'project'
for name in ['config','common_sensor','mapper_source','install_mapper','install_cmu','install_native','venv','scene_assets']:
    if not (root/name).exists():(root/name).symlink_to(old/name,target_is_directory=True)
(root/'runtime').mkdir(exist_ok=True)
envelope=json.loads((root/'setup/URDF_ENVELOPE.json').read_text())
for variant in ['baseline','urdf']:
    text=(old/'runtime/campus_local_planner.launch.xml').read_text()
    if variant=='urdf':
        length,width,height=envelope['size_xyz'];radius=envelope['required_support_radius']
        text=text.replace('name="vehicleLength" value="0.6"',f'name="vehicleLength" value="{length:.12f}"').replace('name="vehicleWidth" value="0.6"',f'name="vehicleWidth" value="{width:.12f}"')
        text=text.replace('name="ht_validity_radius" value="0.45"',f'name="ht_validity_radius" value="{radius:.12f}"')
        flag='<param name="ht_use_urdf_envelope" value="true"/>\n'
        flag+=f'<param name="ht_body_min_xyz" value="{json.dumps(envelope["min_xyz"])}"/>\n'
        flag+=f'<param name="ht_body_max_xyz" value="{json.dumps(envelope["max_xyz"])}"/>\n'
        text=text.replace('<param name="ht_enabled"',flag+'<param name="ht_enabled"')
    (root/'runtime'/f'campus_{variant}_local_planner.launch.xml').write_text(text)
for name in ['mapper_setup_4hz.yaml','mcap.yaml','recording_qos.yaml','startup_collect.py','boundary.py']:
    shutil.copy2(old/name,root/name)
env=(old/'env.sh').read_text().replace('ROS_DOMAIN_ID=218','ROS_DOMAIN_ID=226')
env+='\nsource '+str(root/'install_gate/setup.bash')+'\nexport ROS_LOG_DIR='+str(root/'ros_logs')+'\n'
(root/'env.sh').write_text(env)
launch=(old/'simulation.launch.py').read_text().replace(str(old),str(root))
launch=launch.replace("scene=LaunchConfiguration('scene').perform(context)","scene=LaunchConfiguration('scene').perform(context)\n envelope=LaunchConfiguration('envelope').perform(context)\n if envelope not in ('baseline','urdf'):raise ValueError(envelope)")
launch=launch.replace("f'{scene}_local_planner.launch.xml'","f'{scene}_{envelope}_local_planner.launch.xml'")
launch=launch.replace("DeclareLaunchArgument('scene',default_value='user_pcd')","DeclareLaunchArgument('scene',default_value='campus'),DeclareLaunchArgument('envelope',default_value='baseline')")
(root/'simulation.launch.py').write_text(launch)
runner=(old/'run.py').read_text().replace(str(old),str(root))
# Keep all live HT maps, raw registered scans, odometry, commands, exploration
# and recovery diagnostics. Omit duplicate sensor/terrain/mapper input products.
runner=runner.replace("def freeze():", "TOPICS=[t for t in TOPICS if t not in ['/sensor_scan','/terrain_map','/terrain_map_ext','/elevation_mapping/elevation_map_raw','/free_paths']]\n\ndef freeze():")
runner=runner.replace("files += [ROOT/'run.py'", "files += [p for p in (ROOT/'project').rglob('*') if p.is_file() and '__pycache__' not in p.parts]\n files += [ROOT/'setup/URDF_ENVELOPE.json',ROOT/'setup/scout_expanded.urdf']\n files += [ROOT/'run.py'")
runner=runner.replace("if __import__('shutil').disk_usage(ROOT).free<12*1024**3:","if __import__('shutil').disk_usage(ROOT).free<7*1024**3:")
runner=runner.replace("'ROS_DOMAIN_ID','ROS_LOCALHOST_ONLY'","'HT_ENVELOPE_CASE','ROS_DOMAIN_ID','ROS_LOCALHOST_ONLY'")
runner=runner.replace("DISPLAY=':88'","DISPLAY=':93'").replace('str(11516)','str(11517)')
runner=runner.replace("'scene:='+scene]","'scene:='+scene,'envelope:='+os.environ['HT_ENVELOPE_CASE']]")
runner=runner.replace("'project_commit':'7957e72f8e8b921912d6064cfb02eac22c1d9ec3',","'baseline_commit':'d368516305d4b8c55f9039a6d96900aa1c5823b3','envelope_case':os.environ['HT_ENVELOPE_CASE'], 'change':'opt-in pinned URDF body box; unchanged TARE/HT scores/controller; conservative circle support radius covers full body',")
(root/'run.py').write_text(runner)
budget=root/'BUDGET.json'
if not budget.exists():budget.write_text(json.dumps({'maximum_formal_launch_attempts':3,'planned_runs':[{'envelope':'baseline','scene':'campus','duration_s':600},{'envelope':'urdf','scene':'campus','duration_s':600}],'extra_attempt':'infrastructure failure retry only; no new navigation candidates','attempts':[]},indent=2))
(root/'EXPERIMENT_SCOPE.json').write_text(json.dumps({'scene':'AEDE campus','same_world_spawn_sensor_tare_weights_controller':True,'urdf_repository':'CQULzz/eletranskit_scout','urdf_commit':'cf0b73d7d01b4b6a2718c7ff3124f4b7a3368c36','occupancy':'2D conservative XY projection of full URDF box; no vertical clearance relaxation','body_frame_alignment':'URDF base_link XY attached to CMU vehicle reference; existing simulated sensor and its height unchanged; not full Scout hardware/physics','support_radius_change':[.45,envelope['required_support_radius']],'support_rationale':'larger body requires a larger known-ground and boundary support circle; no probability/TTL/unknown threshold relaxation','omitted_bag_topics':['/sensor_scan','/terrain_map','/terrain_map_ext','/elevation_mapping/elevation_map_raw','/free_paths'],'sampling_randomness':'same configuration and origin; native TARE and ROS scheduling are not deterministic; single pair cannot prove causal efficiency improvement'},indent=2))
print('Prepared frozen-pair harness')
