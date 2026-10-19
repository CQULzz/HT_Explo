from pathlib import Path
import argparse,json,time,hashlib
import numpy as np
import cupy as cp
from elevation_mapping_cupy import ElevationMap,Parameter
from elevation_mapping_cupy.elevation_mapping_ros import _set_parameter_fields,_resolve_package_paths,_load_yaml
from ament_index_python.packages import get_package_share_directory
from scipy.spatial.transform import Rotation

p=argparse.ArgumentParser();p.add_argument('--allocator',choices=['managed','device'],required=True);p.add_argument('--fixture',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
if args.output.exists():raise FileExistsError(args.output)
pool=cp.cuda.MemoryPool(cp.cuda.malloc_managed) if args.allocator=='managed' else cp.cuda.MemoryPool()
cp.cuda.set_allocator(pool.malloc)
root=Path('/home/lzz/my test/elevation_mapping_cupy_ws');share=get_package_share_directory('elevation_mapping_cupy')
config=_resolve_package_paths({**_load_yaml(root/'config/trial_core.yaml'),**_load_yaml(root/'config/trial_setup.yaml')},share)
param=Parameter();_set_parameter_fields(param,config);param.subscriber_cfg=config['subscribers'];param.update();core=ElevationMap(param)
fixture=np.load(args.fixture,allow_pickle=False);poses=fixture['poses'];stamps=fixture['stamps'];rows=[];states={}
cp.cuda.Stream.null.synchronize()
for cycle in range(6):
 for i,pose in enumerate(poses):
  stamp=float(stamps[i]+cycle*60);position=pose[:3];rotation=Rotation.from_quat(pose[3:]).as_matrix();points=(fixture[f'cloud_{i}']-position)@rotation
  for op in ['pose','scan','publish']:
   cp.cuda.Stream.null.synchronize();begin=time.perf_counter()
   if op=='pose':core.move_to(position,rotation)
   elif op=='scan':core.input_pointcloud(points,['x','y','z'],rotation,position.copy(),0,0,observation_stamp=stamp)
   else:
    for layer in ['elevation','variance']:
     data=np.empty((param.cell_n-2,param.cell_n-2),np.float32);core.get_map_with_name_ref(layer,data)
    core.get_observation_age_ref(stamp,data)
   cp.cuda.Stream.null.synchronize();rows.append(dict(cycle=cycle,index=i,operation=op,elapsed_s=time.perf_counter()-begin))
  if cycle in [0,5]:
   for name,array in [('elevation_map',core.elevation_map),('observation_stamps',core.observation_stamps),('normal_map',core.normal_map),('center',core.center)]:states[f'{cycle}_{i}_{name}']=array.get()
args.output.mkdir(parents=True);np.savez_compressed(args.output/'states.npz',**states)
def stats(r):
 v=[x['elapsed_s'] for x in rows if x['operation']==r and x['cycle']>0]
 return dict(count=len(v),p50=float(np.median(v)),p95=float(np.quantile(v,.95)),max=max(v),total=sum(v))
result=dict(allocator=args.allocator,fixture_sha256=hashlib.sha256(args.fixture.read_bytes()).hexdigest(),operations={r:stats(r) for r in ['pose','scan','publish']},rows=rows,scope='Serial fixed recorded-cloud workload, synchronized per operation; excludes live contention, ROS queues and simulator. Same mathematical map operations; output comparison required.')
(args.output/'timing.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
