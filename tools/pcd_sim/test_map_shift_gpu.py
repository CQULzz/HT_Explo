"""Compare complete rolling-map state before/after copying XY integers once."""
from pathlib import Path
import importlib.util,hashlib,json,time
import cupy as cp,numpy as np
from scipy.spatial.transform import Rotation
R=Path('/home/w_lzz/ht-iterations-20261105');W=Path('/home/lzz/my test/ht_cupy_gpu_ws_20261028');newpath=W/'src/elevation_mapping_cupy_2204/elevation_mapping_cupy/script/elevation_mapping_cupy/elevation_mapping.py'
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=module('old_map',R/'setup/pre-r03-elevation_mapping.py');new=module('new_map',newpath);wrapper=module('wrapper',R/'runtime/mapper_strict.py');cfg={**wrapper._load_yaml(R/'runtime/mapper_core.yaml'),**wrapper._load_yaml(R/'runtime/mapper_setup.yaml')}
maps=[]
for mod in [old,new]:
 p=wrapper.Parameter();wrapper._set_parameter_fields(p,cfg);p.subscriber_cfg=cfg['subscribers'];p.update();maps.append(mod.ElevationMap(p))
rng=np.random.default_rng(83910);n=p.cell_n
for field in ['elevation_map','observation_stamps','normal_map','new_map','traversability_input']:
 src=rng.normal(size=getattr(maps[0],field).shape).astype(getattr(maps[0],field).dtype)
 if field=='observation_stamps':src.flat[::13]=np.nan
 for m in maps:setattr(m,field,cp.asarray(src.copy()))
def state(m):
 fields={k:cp.asnumpy(getattr(m,k)).tobytes() for k in ['center','base_rotation','elevation_map','observation_stamps','normal_map','new_map','traversability_input']}
 fields.update({'semantic_'+k:cp.asnumpy(getattr(m.semantic_map,k)).tobytes() for k in ['semantic_map','new_map']})
 return fields
positions=[[0,0,0],[.0199999,0,.1],[.02,0,.1],[.0200001,0,.1],[-.02,-.02,-.1],[1.,2.,.3],[1.,2.,.3],[-4.,3.,0],[40.,-40.,1.],[-40.,40.,-1.]]
positions += rng.uniform([-3,-3,-.2],[3,3,.2],(20,3)).tolist();cases=[]
for i,pos in enumerate(positions):
 rot=Rotation.from_euler('xyz',[.03*np.sin(i),.02*np.cos(i),.1*i]).as_matrix();times=[]
 for m in maps:
  cp.cuda.runtime.deviceSynchronize();start=time.perf_counter();m.move_to(np.array(pos,np.float64),rot);cp.cuda.runtime.deviceSynchronize();times.append(time.perf_counter()-start)
 assert state(maps[0])==state(maps[1]),f'Map state byte mismatch {i}'
 cases.append({'case':i,'position':pos,'all_state_bytes_equal':True,'service_s':times});print('PARITY',i,'exact',flush=True)
b=np.array([x['service_s'] for x in cases[2:]]);result={'all_exact':True,'cases':cases,'scope':'Offline sequential map-move byte parity, including all map/age/center/rotation/semantic state; no closed-loop acceptance','service_s':{'baseline_p50':float(np.median(b[:,0])),'candidate_p50':float(np.median(b[:,1]))},'before_sha256':hashlib.sha256((R/'setup/pre-r03-elevation_mapping.py').read_bytes()).hexdigest(),'after_sha256':hashlib.sha256(newpath.read_bytes()).hexdigest()};(R/'setup/r03-map-shift-parity.json').write_text(json.dumps(result,indent=2));print(json.dumps(result['service_s'],indent=2))
