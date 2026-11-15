from pathlib import Path
import shutil,json,hashlib,py_compile,xml.etree.ElementTree as ET
root=Path('/home/lzz/ht_helios_collision_20261115');repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');setup=Path('/mnt/d/HT-Helios-Collision-20261115/setup');analysis=setup.parent/'analysis';dest=repo/'validation/helios_collision_20261115'
def copy(source,target):
 target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
for p in (repo/'tools/helios32_sim').glob('*.py'):py_compile.compile(str(p),cfile='/tmp/helios_'+p.stem+'.pyc',doraise=True)
assets=root/'common_sensor_optical';manifest=json.loads((assets/'MANIFEST.json').read_text());tree=ET.parse(assets/'robot.sdf')
assert len(tree.findall('.//collision'))==18
assert abs(manifest['lidar_height_above_ground_m']-.84849)<1e-10
assert abs(manifest['base_link_to_lidar_xyz'][2]-.6137)<1e-10
for p in assets.glob('*.sdf'):ET.parse(p)
checks={'python_syntax':True,'sdf_xml':True,'opaque_collisions':18,'optical_height_m':manifest['lidar_height_above_ground_m'],'source_profile_sha256':hashlib.sha256((repo/'tools/helios32_sim/helios_5515.json').read_bytes()).hexdigest(),'navigation_acceptance_final_model':False,'shutdown_cleanup_passed':False}
source=[]
for p in (repo/'src/helios32_sim').rglob('*'):
 if p.is_file():
  compiled=root/'project/src/helios32_sim'/p.relative_to(repo/'src/helios32_sim')
  assert p.read_bytes()==compiled.read_bytes()
  source.append({'file':str(p.relative_to(repo)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(analysis/'COMPILED_SOURCE_CHECK.json').write_text(json.dumps({'passed':True,'files':source},indent=2))
(analysis/'FINAL_CHECKS.json').write_text(json.dumps(checks,indent=2))
for p in analysis.iterdir():
 if p.is_file():copy(p,dest/p.name)
for src,target in [('static_probes_optical','static_optical'),('rotation_probe_optical','rotation_optical')]:
 for p in (root/src).iterdir():
  if p.is_file() and p.suffix in ['.json','.npz','.world','.log']:copy(p,dest/target/p.name)
(dest/'rotation_optical/CLEANUP.json').write_text(json.dumps({'clean':False,'exact_exit_codes':'not recorded by the executed probe version','evidence':'carrier.log reports Failed to delete datawriter and Segmentation fault after SIGINT','registration_pass_scope':'running scan registration only'},indent=2))
(dest/'rotation_optical/PASSED.json').write_text(json.dumps({'passed':True,'scope':'Scan registration only; shutdown cleanup failed, see CLEANUP.json.'},indent=2))
for p in assets.glob('*'):
 if p.is_file():copy(p,dest/'assets'/p.name)
for name in ['mesh_ray_probe.json','BUDGET.json']:copy(root/name,dest/name)
for name in ['plugin_build.log','vehicle_build.log','vehicle_final_build.log','sdf_validation.log','static_optical.log','rotation_optical.log','rotation_probe.log','static_optical_before_unique_names.log','rotation_optical_before_unique_names.log']:
 if (root/'setup'/name).exists():copy(root/'setup'/name,dest/'logs'/name)
for run in (root/'runs').iterdir():
 target=dest/'development_runs'/run.name
 for name in ['RESULT.json','COMMANDS.json','FREEZE.json','ENVIRONMENT.json','localPlanner.yaml','pathFollower.yaml','vehicleSimulator.yaml','tare_planner_node.yaml','cupy_to_ht_bridge.yaml']:
  if (run/name).exists():copy(run/name,target/name)
 for name in ['SUMMARY.json','START.json','metrics.csv']:copy(run/'observations'/name,target/name)
 copy(run/'bag/metadata.yaml',target/'metadata.yaml')
for p in setup.iterdir():
 if p.is_file() and p.suffix in ['.py','.sh']:copy(p,dest/'source'/p.name)
# The root runtime preserves the earlier development model; keep it explicitly
# labelled rather than claiming it contains the final optical-datum source.
for name in ['run.py','simulation.launch.py','env.sh','startup_collect.py','mcap.yaml','recording_qos.yaml']:
 copy(root/name,dest/'source/development_mount_origin'/name)
for p in (root/'runtime').iterdir():
 if p.is_file():copy(p,dest/'source/development_mount_origin/runtime'/p.name)
for p in (root/'common_sensor').iterdir():
 if p.is_file():copy(p,dest/'source/development_mount_origin/assets'/p.name)
for p in dest.rglob('*.yaml'):
 # Formatting only for published text copies; raw runtime dumps stay untouched.
 p.write_text(p.read_text().rstrip()+'\n')
print('COMPACT_EVIDENCE_READY',dest)
