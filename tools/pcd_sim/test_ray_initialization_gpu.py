"""Exact GPU event/map parity and service timings for coalesced initialization."""
from pathlib import Path
import importlib.util,time,json,hashlib,argparse
import numpy as np,cupy as cp
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path('/home/w_lzz/ht-iterations-20261105'));a=ap.parse_args();R=a.root
W=Path('/home/lzz/my test/ht_cupy_gpu_ws_20261028');new_path=W/'src/elevation_mapping_cupy_2204/elevation_mapping_cupy/script/elevation_mapping_cupy/deterministic_fusion.py'
def module(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
old=module('old_fusion',R/'setup/pre-r02-deterministic_fusion.py');new=module('new_fusion',new_path);wrapper=module('mapper_wrapper',R/'runtime/mapper_strict.py')
cfg={**wrapper._load_yaml(R/'runtime/mapper_core.yaml'),**wrapper._load_yaml(R/'runtime/mapper_setup.yaml')};p=wrapper.Parameter();wrapper._set_parameter_fields(p,cfg);p.subscriber_cfg=cfg['subscribers'];p.update()
cores=[old.DeterministicFusion(p),new.DeterministicFusion(p)];rng=np.random.default_rng(24519);records=[];n=p.cell_n;m=n*n
def bits(x):return cp.asnumpy(x).tobytes()
for case,count in enumerate([0,1,127,128,129,1000,4096,26000,26000,26000,30000,30000]):
 height=rng.normal(-.8,.02,(n,n)).astype(np.float32);variance=rng.uniform(.001,.05,(n,n)).astype(np.float32);valid=(rng.random((n,n))>.15).astype(np.float32);age=rng.choice([0.,.49,.5,.99,1.,10.],(n,n)).astype(np.float32)
 prior=np.stack([height,variance,valid,np.ones((n,n),np.float32),age,height.copy(),np.zeros((n,n),np.float32)]);normals=np.zeros((3,n,n),np.float32);normals[2]=1
 pts=rng.uniform([-4,-4,-1.3],[4,4,.8],(count,3)).astype(np.float32)
 if case%3==0 and count:pts[::11]=np.nan
 rot=np.eye(3,dtype=np.float32);trans=np.array([.17,0,-.05],np.float32);outputs=[];events=[];service=[]
 for core in cores:
  elev=cp.asarray(prior);normal=cp.asarray(normals);points=cp.asarray(pts);newmap=cp.zeros_like(elev);captured=[];launch=core._launch
  def capture(name,num,args):
   launch(name,num,args)
   if name=='emit_rays':captured.extend(bits(x) for x in args[-4:])
  core._launch=capture
  cp.cuda.runtime.deviceSynchronize();start=time.perf_counter();stats=core.fuse(elev,normal,points,cp.asarray(rot),cp.asarray(trans),newmap,.2 if case%2 else 0.,.2 if case%2 else 0.);cp.cuda.runtime.deviceSynchronize();service.append(time.perf_counter()-start)
  core._launch=launch;outputs.append([bits(x) for x in [elev,newmap,points,stats]]);events.append(captured)
 assert outputs[0]==outputs[1],f'Map/stat/metadata byte mismatch case {case}'
 assert events[0]==events[1],f'Event byte mismatch case {case}'
 records.append({'case':case,'points':count,'map_newmap_metadata_stats_bitwise_equal':True,'all_event_buffers_bitwise_equal':True,'event_buffers':len(events[0]),'timing_with_capture_s':service})
 print('PARITY',case,count,'exact',flush=True)
# Paired warmed timings exclude result capture; restore each initial state.
bench=[];points0=rng.uniform([-4,-4,-1.3],[4,4,.8],(26000,3)).astype(np.float32)
for rep in range(12):
 pair=[]
 for core in cores:
  elev=cp.asarray(prior);normal=cp.asarray(normals);points=cp.asarray(points0);newmap=cp.zeros_like(elev);rot_gpu=cp.asarray(rot);trans_gpu=cp.asarray(trans)
  cp.cuda.runtime.deviceSynchronize();start=time.perf_counter();core.fuse(elev,normal,points,rot_gpu,trans_gpu,newmap,0.,0.);cp.cuda.runtime.deviceSynchronize();pair.append(time.perf_counter()-start)
 bench.append(pair)
b=np.array(bench[2:]);result={'scope':'Offline paired exact GPU regression; synthetic valid/missing/boundary-age/invalid-point fixtures, not navigation success or universal proof','cases':records,'warm_fusion_service_s':{'baseline_p50':float(np.median(b[:,0])),'candidate_p50':float(np.median(b[:,1])),'baseline_p95':float(np.percentile(b[:,0],95)),'candidate_p95':float(np.percentile(b[:,1],95))},'all_exact':True,'baseline_sha256':hashlib.sha256((R/'setup/pre-r02-deterministic_fusion.py').read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(new_path.read_bytes()).hexdigest()};(R/'setup/r02-gpu-parity.json').write_text(json.dumps(result,indent=2));print(json.dumps(result['warm_fusion_service_s'],indent=2))
