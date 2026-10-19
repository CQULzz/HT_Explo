from pathlib import Path
import argparse,json,time,threading
import numpy as np
import cupy as cp
import rclpy
from rclpy.node import Node
from rclpy.executors import SingleThreadedExecutor,MultiThreadedExecutor
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup,ReentrantCallbackGroup
from elevation_mapping_cupy import ElevationMap,Parameter
from elevation_mapping_cupy.elevation_mapping_ros import _set_parameter_fields,_resolve_package_paths,_load_yaml
from ament_index_python.packages import get_package_share_directory
from scipy.spatial.transform import Rotation
from tf2_ros import Buffer,TransformListener
from elevation_mapping_cupy.elevation_mapping_ros import _stop_executor
p=argparse.ArgumentParser();p.add_argument('--mode',choices=['single','multi'],required=True);p.add_argument('--seconds',type=float,default=25);p.add_argument('--output',type=Path,required=True);p.add_argument('--tf',action='store_true');a=p.parse_args()
configroot=Path('/home/lzz/my test/elevation_mapping_cupy_ws');share=get_package_share_directory('elevation_mapping_cupy');config=_resolve_package_paths({**_load_yaml(configroot/'config/trial_core.yaml'),**_load_yaml(configroot/'config/trial_setup.yaml')},share)
param=Parameter();_set_parameter_fields(param,config);param.subscriber_cfg=config['subscribers'];param.update();core=ElevationMap(param);data=np.load('/tmp/ht_allocator_fixture.npz');pose=data['poses'][0];rot=Rotation.from_quat(pose[3:]).as_matrix();points=(data['cloud_0']-pose[:3])@rot;core.move_to(pose[:3],rot);core.input_pointcloud(points,['x','y','z'],rot,pose[:3].copy(),0,0,observation_stamp=100.);cp.cuda.Stream.null.synchronize()
rows=[];lock=threading.RLock();rclpy.init()
class TestNode(Node):
 def __init__(self):
  super().__init__('map_executor_benchmark');self.buffer=Buffer();self.listener=TransformListener(self.buffer,self) if a.tf else None;self.scan=MutuallyExclusiveCallbackGroup();self.timer=MutuallyExclusiveCallbackGroup();self.pub=MutuallyExclusiveCallbackGroup();self.tf=ReentrantCallbackGroup()
  for seconds,name,group in [(.2,'scan',self.scan),(.1,'pose',self.timer),(.2,'variance',self.timer),(.1,'time',self.timer),(.5,'publish',self.pub),(.005,'tf_tick',self.tf)]:self.create_timer(seconds,lambda n=name:self.call(n),callback_group=group)
 def call(self,name):
  if name=='tf_tick':return
  start=time.perf_counter();cpu=time.thread_time()
  with lock:
   acquired=time.perf_counter()
   if name=='pose':core.move_to(pose[:3],rot)
   elif name=='scan':core.input_pointcloud(points,['x','y','z'],rot,pose[:3].copy(),0,0,observation_stamp=100.)
   elif name=='variance':core.update_variance()
   elif name=='time':core.update_time()
   else:
    output=np.empty((param.cell_n-2,param.cell_n-2),np.float32)
    core.get_map_with_name_ref('elevation',output);core.get_map_with_name_ref('variance',output);core.get_observation_age_ref(100.,output)
  rows.append(dict(operation=name,elapsed=time.perf_counter()-start,hold=time.perf_counter()-acquired,wait=acquired-start,cpu=time.thread_time()-cpu))
node=TestNode();executor=SingleThreadedExecutor() if a.mode=='single' else MultiThreadedExecutor(num_threads=4);executor.add_node(node);started=time.monotonic();cpu=time.process_time()
while time.monotonic()-started<a.seconds:executor.spin_once(timeout_sec=.1)
_stop_executor(executor);node.destroy_node();rclpy.shutdown();elapsed=time.monotonic()-started;cpu=time.process_time()-cpu
summary={}
for name in ['scan','pose','publish','variance','time']:
 sub=[r for r in rows if r['operation']==name];summary[name]={k:dict(p50=float(np.median([r[k] for r in sub])),p95=float(np.quantile([r[k] for r in sub],.95)),max=max(r[k] for r in sub)) for k in ['elapsed','hold','wait','cpu']};summary[name]['count']=len(sub)
result=dict(mode=a.mode,duration_s=elapsed,process_cpu_s=cpu,summary=summary,rows=rows,scope='Fixed cloud/pose timer workload plus200Hz no-op callback; no live simulator/TF/DDS. Measures executor interaction, not full closed-loop safety or exact map equivalence.')
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
