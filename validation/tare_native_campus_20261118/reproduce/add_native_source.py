from pathlib import Path
import shutil,hashlib,json,ast
base=Path('/home/lzz/tare_native_campus_20261118');out=Path('/mnt/d/TARE-Native-Campus-20261118/results');src=base/'project/src';dest=out/'reproduce/native_source';index=[]
for pkg in ['tare_planner','local_planner','terrain_analysis','terrain_analysis_ext','sensor_scan_generation','vehicle_simulator']:
 for p in (src/pkg).rglob('*'):
  rel=p.relative_to(src)
  if not p.is_file() or any(s in ['or-tools','data','rviz','meshes','paths'] for s in rel.parts):continue
  if p.suffix not in ['.h','.hpp','.cpp','.yaml','.xml','.py','.xacro'] and p.name!='CMakeLists.txt':continue
  q=dest/rel;q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);index.append({'file':str(q.relative_to(out)),'bytes':q.stat().st_size,'sha256':hashlib.sha256(q.read_bytes()).hexdigest()})
(out/'NATIVE_SOURCE_INDEX.json').write_text(json.dumps({'files':index,'scope':'Pinned upstream native src/include/config/launch/build descriptions; excludes mesh/path tables and OR-tools binaries/headers. Full frozen runtime stays in WSL.'},indent=2))
p=base/'BUDGET.json';j=json.loads(p.read_text());j['extra_attempt']='Original infrastructure-only restriction superseded for the second slot by the documented identical-configuration recurrence test; total remains two.';p.write_text(json.dumps(j,indent=2));shutil.copy2(p,out/p.name)
for p in out.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
print('Native source subset',len(index),sum(e['bytes'] for e in index))
