from pathlib import Path
import importlib.util,json,sys,hashlib,math
ROOT=Path('/home/lzz/ht_only_20261111/analysis/scout_probes');ROOT.mkdir(exist_ok=False)
source=Path('/home/lzz/pcd_physics_20261110/test_physics.py');spec=importlib.util.spec_from_file_location('archived_physics',source);mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);mod.ROOT=ROOT
pose=json.loads(Path('/home/lzz/ht_only_20261111/analysis/live_a_stop/TRUTH.json').read_text())['pose']
case={'id':'a_new_stop','xy':pose[:2],'heading_deg':math.degrees(pose[5]),'ht_score':None,'classification':'All eight center neural scores >.96; inflated HT occupied veto.'}
manifest={'scope':'Supplementary archived Scout dynamics, not the CMU vehicle. Same original mesh, same fixed dynamics/control/friction as previous physics study; no ROS navigation or teleported trajectory. 1 flat control + 3 center checks + 6 straight crossings. No traversal claim for paths outside these probes.','case':case,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'source':str(source),'assets':{str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in mod.ASSET.iterdir() if p.suffix in ['.obj','.urdf']}}
(ROOT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2));(ROOT/'test_physics_frozen.py').write_bytes(source.read_bytes());mod.p.connect(mod.p.DIRECT);results=[]
results.append(mod.trial({'id':'flat','xy':[0,0],'heading_deg':0},1,'historical_like','flat',True))
for friction in ['historical_like','isotropic_0.4','isotropic_0.8']:
 results.append(mod.trial(case,1,friction,friction+'_center',center_only=True))
 for gear in [1,-1]:
  r=mod.trial(case,gear,friction,friction+('_fwd' if gear==1 else '_rev'));results.append(r);print(friction,gear,r['status'],r.get('clean_pass'),r.get('max_chassis_penetration_m'),flush=True)
mod.p.disconnect();(ROOT/'RESULTS.json').write_text(json.dumps(results,indent=2));print('saved',len(results),'trials')
