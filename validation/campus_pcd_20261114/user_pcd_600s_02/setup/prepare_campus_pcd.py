from pathlib import Path
import json,hashlib,tarfile,zipfile,shutil,subprocess,xml.etree.ElementTree as E
import numpy as np
root=Path('/home/lzz/ht_campus_pcd_20261114');root.mkdir(exist_ok=True);(root/'setup').mkdir(exist_ok=True);(root/'scene_assets').mkdir(exist_ok=True)
pcd=Path('/home/lzz/pcd_test_20261110');source=pcd/'source';source.mkdir(parents=True,exist_ok=True)
wanted={'runtime/local_map.npy','runtime/scene.sdf','runtime/scene_meshes.npz','model_assets/environment/ground.dae','model_assets/environment/obstacles.dae'}
with tarfile.open('/mnt/d/HT-Execution-300s/setup/legacy_map_assets.tar') as t:
    assert {m.name for m in t.getmembers()}==wanted
    t.extractall(source)
inventory=json.loads(Path('/mnt/d/HT-Resume/publication/navigation-fix-files.json').read_text(encoding='utf-8-sig'));entries={e['path']:e for e in inventory['files']};receipt=[]
for name in sorted(wanted):
    p=source/name;digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==entries[name]['sha256'],name
    receipt.append({'path':name,'sha256':digest,'bytes':p.stat().st_size})
(source/'RECOVERY.json').write_text(json.dumps({'release':'https://github.com/CQULzz/HT_Explo/releases/tag/ht-scout-pcd-fix-20261105-v1','method':'Read-only copy from preserved WSL 24.04 runtime, verified against historical published inventory','files':receipt},indent=2))
raw=np.load(source/'runtime/local_map.npy');assert hashlib.sha256((source/'runtime/local_map.npy').read_bytes()).hexdigest()=='a30eb5576c23ae2c0a688299611e4defbc266761f277befe4ff8d9dd3acf647d'
data=Path('/mnt/d/HT-Execution-300s/setup/recorded_local_map.pcd').read_bytes();end=data.index(b'DATA binary\n')+len(b'DATA binary\n');header=data[:end].decode();print(header)
fields=next(l.split()[1:] for l in header.splitlines() if l.startswith('FIELDS '));arr=np.frombuffer(data[end:],dtype='<f4').reshape(-1,len(fields));xyz=arr[:,[fields.index(k) for k in ['x','y','z']]]
assert np.array_equal(raw,xyz);shutil.copy2('/mnt/d/HT-Execution-300s/setup/recorded_local_map.pcd',source/'recorded_local_map.pcd')
(source/'PCD_IDENTITY.json').write_text(json.dumps({'points':len(xyz),'npy_equal_pcd':True,'pcd_header':header,'pcd_sha256':hashlib.sha256(data).hexdigest(),'note':'Historical recorded-map export preserved by the project; not claimed to be the lost independent original PCD.'},indent=2))
if not (pcd/'runtime').exists():subprocess.run(['python3','/mnt/d/HT-Execution-300s/setup/pcd_prepare_base.py'],check=True,stdout=(root/'setup/prepare_pcd.log').open('w'))
with zipfile.ZipFile('/mnt/d/HT-Execution-300s/setup/scene_response') as z:
    names=[n for n in z.namelist() if n.startswith('campus/')]
    for n in names:
        assert '..' not in Path(n).parts;z.extract(n,'/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh')
world=E.parse('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/world/campus.world')
for parent in world.iter():
    for child in list(parent):
        if child.tag=='plugin' and child.get('filename')=='librotors_gazebo_ros_interface_plugin.so':parent.remove(child)
world.write(root/'scene_assets/campus.world',encoding='unicode')
campus=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus')
(root/'scene_assets/CAMPUS_MANIFEST.json').write_text(json.dumps({'cmu_commit':'158e67b31b644ed1e8b06eb1d7f70e183cc62591','scene':'Official CMU AEDE campus','files':{str(p.relative_to(campus)):hashlib.sha256(p.read_bytes()).hexdigest() for p in campus.rglob('*') if p.is_file()}},indent=2))
old=Path('/home/lzz/ht_600s_20261114')
for name in ['config','common_sensor','mapper_source','install_mapper','install_gate','install_cmu','install_native','venv']:
    if not (root/name).exists():(root/name).symlink_to(old/name,target_is_directory=True)
(root/'runtime').mkdir(exist_ok=True)
for name in ['indoor','user_pcd']:shutil.copy2(old/'runtime'/f'{name}_local_planner.launch.xml',root/'runtime'/f'{name}_local_planner.launch.xml')
shutil.copy2(old/'runtime/indoor_local_planner.launch.xml',root/'runtime/campus_local_planner.launch.xml')
for name in ['mapper_setup_4hz.yaml','mcap.yaml','recording_qos.yaml']:shutil.copy2(old/name,root/name)
(root/'boundary.py').write_text(Path('/mnt/d/HT-Execution-300s/setup/pcd_boundary_base.py').read_text(encoding='utf-8-sig'))
(root/'env.sh').write_text((old/'env.sh').read_text().replace('ROS_DOMAIN_ID=216','ROS_DOMAIN_ID=218'))
runner=(old/'run.py').read_text().replace(str(old),str(root))
runner=runner.replace("PROJECT/'tools/user_pcd/boundary.py'", "ROOT/'boundary.py'")
runner=runner.replace("choices=['user_pcd','indoor']", "choices=['user_pcd','indoor','campus']")
runner=runner.replace("files += [ROOT/'run.py',ROOT/'simulation.launch.py',ROOT/'recording_qos.yaml']", "files += [ROOT/'run.py',ROOT/'simulation.launch.py',ROOT/'recording_qos.yaml',ROOT/'boundary.py',Path('/home/lzz/pcd_test_20261110/runtime/SCENE_MANIFEST.json')]\n files += [p for p in (ROOT/'scene_assets').rglob('*') if p.is_file()]\n files += [p for p in Path('/home/lzz/pcd_test_20261110/runtime').rglob('*') if p.is_file()]")
runner=runner.replace("{'scene':'official CMU indoor'}", "({'scene':'official CMU campus','manifest':json.loads((ROOT/'scene_assets/CAMPUS_MANIFEST.json').read_text())} if scene=='campus' else {'scene':'official CMU indoor'})")
(root/'run.py').write_text(runner)
launch=(old/'simulation.launch.py').read_text().replace(str(old),str(root)).replace("['user_pcd','indoor']", "['user_pcd','indoor','campus']")
launch=launch.replace("context.launch_configurations.update(world_name=scene", "context.launch_configurations.update(world_name=('indoor' if scene=='user_pcd' else scene)")
launch=launch.replace(" if scene=='user_pcd':\n  config=", " if scene=='campus':context.launch_configurations.update(world=str(ROOT/'scene_assets/campus.world'))\n if scene=='user_pcd':\n  config=")
launch=launch.replace("/'indoor.yaml'", "/('campus.yaml' if scene=='campus' else 'indoor.yaml')")
(root/'simulation.launch.py').write_text(launch)
budget=root/'BUDGET.json'
if not budget.exists():budget.write_text(json.dumps({'maximum_formal_launch_attempts':4,'planned_runs':[{'scene':'campus','duration_s':600},{'scene':'user_pcd','duration_s':600}],'extra_attempts':'infrastructure failure retries only','attempts':[]},indent=2))
print('Prepared campus and verified recorded-PCD scenes')
