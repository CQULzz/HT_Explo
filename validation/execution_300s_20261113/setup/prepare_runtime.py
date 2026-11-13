from pathlib import Path
import hashlib,json,shutil,zipfile,subprocess
root=Path('/home/lzz/ht_execution_300s_20261113')
old=root/'previous_complete/ht_quality_20261111'
manifest=json.loads((old/'DATA_FILES_SHA256.json').read_text())
for r in manifest:
    p=old.parent/r['path'];data=p.read_bytes()
    assert len(data)==r['bytes'] and hashlib.sha256(data).hexdigest()==r['sha256'],str(p)
print('Previous evidence verified:',len(manifest),'files')
for name in ['mapper_source','config','runtime']:
    shutil.copytree(old/name,root/name,dirs_exist_ok=True)
for name in ['mapper_setup_4hz.yaml','mcap.yaml']:
    shutil.copy2(old/name,root/name)
core=root/'config/trial_core.yaml'
core.write_text(core.read_text().replace('/home/lzz/ht_quality_20261111',str(root)))
project=Path('/home/lzz/HT_Explo_execution_20261113')
mapper=root/'mapper_source/elevation_mapping_cupy_2204'
for name in ['elevation_mapping.py','deterministic_fusion.py']:
    assert (mapper/'elevation_mapping_cupy/script/elevation_mapping_cupy'/name).read_bytes()==(project/'tools/ht_height_quality/mapper_patch'/name).read_bytes(),name
with zipfile.ZipFile('/mnt/d/HT-Execution-300s/setup/scene_response') as z:
    names=[n for n in z.namelist() if n.startswith('indoor/')]
    for name in names:
        assert '..' not in Path(name).parts
        z.extract(name,'/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh')
print('Indoor scene extracted with ZIP CRC checks:',len(names),'entries')
target=Path('/home/lzz/tare_native_20261110')
patch=project/'tools/cmu_minimal/upstream_frontier_parameter.patch'
if subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=target,capture_output=True).returncode:
    subprocess.run(['git','apply','--check',str(patch)],cwd=target,check=True)
    subprocess.run(['git','apply',str(patch)],cwd=target,check=True)
(root/'BUDGET.json').write_text(json.dumps({'maximum_formal_launch_attempts':2,'planned_successful_runs':1,'duration_s':300,'extra_attempt':'only infrastructure failure retry','attempts':[]},indent=2))
(root/'setup/RESTORE.json').write_text(json.dumps({'previous_evidence_files_verified':len(manifest),'mapper_matches_reviewed_quality_patch':True,'scene_crc_verified':True,'candidate_commit':'7957e72f8e8b921912d6064cfb02eac22c1d9ec3'},indent=2))
