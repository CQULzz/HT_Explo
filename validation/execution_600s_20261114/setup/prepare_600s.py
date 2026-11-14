from pathlib import Path
import shutil,json
previous=Path('/home/lzz/ht_repeat_20261114');root=Path('/home/lzz/ht_600s_20261114')
root.mkdir(exist_ok=True);(root/'setup').mkdir(exist_ok=True)
for name in ['runtime','config','common_sensor','mapper_source','install_mapper','install_gate','install_cmu','install_native','venv']:
    if not (root/name).exists():(root/name).symlink_to(previous/name,target_is_directory=True)
for name in ['mapper_setup_4hz.yaml','mcap.yaml']:shutil.copy2(previous/name,root/name)
runner=(previous/'run.py').read_text().replace(str(previous),str(root)).replace('REPEAT_BUDGET.json','BUDGET.json')
runner=runner.replace("'-b','500000000'", "'--qos-profile-overrides-path',str(ROOT/'recording_qos.yaml'),'--max-cache-size','268435456','-b','500000000'")
runner=runner.replace("files += [ROOT/'install_native", "files += [ROOT/'run.py',ROOT/'simulation.launch.py',ROOT/'recording_qos.yaml']\n files += [ROOT/'install_native")
(root/'run.py').write_text(runner)
(root/'simulation.launch.py').write_text((previous/'simulation.launch.py').read_text().replace(str(previous),str(root)))
(root/'env.sh').write_text((previous/'env.sh').read_text().replace('ROS_DOMAIN_ID=215','ROS_DOMAIN_ID=216'))
(root/'recording_qos.yaml').write_text('''/ht_traversability/global_local:
  history: keep_last
  depth: 100
  reliability: reliable
  durability: volatile
''')
budget=root/'BUDGET.json'
if not budget.exists():budget.write_text(json.dumps({'maximum_formal_launch_attempts':2,'planned_successful_runs':1,'duration_s':600,'extra_attempt':'infrastructure failure retry only','attempts':[]},indent=2))
print('Prepared independent 600-second run; navigation unchanged, recorder map queue enlarged')
