from pathlib import Path
import importlib.util,time,json,collections
import numpy as np,cupy as cp
from scipy.spatial.transform import Rotation
from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
from sensor_msgs_py import point_cloud2
R=Path('/home/w_lzz/ht-iterations-20261105');spec=importlib.util.spec_from_file_location('wrapper',R/'runtime/mapper_strict.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
cfg={**m._load_yaml(R/'runtime/mapper_core.yaml'),**m._load_yaml(R/'runtime/mapper_setup.yaml')};p=m.Parameter();m._set_parameter_fields(p,cfg);p.subscriber_cfg=cfg['subscribers'];p.update()
print('CONFIG',json.dumps({'requested_builtin':cfg['enable_builtin_traversability'],'core_supports_builtin_switch':hasattr(p,'enable_builtin_traversability')}),flush=True)
scans=[];poses=[];classes={}
with next((R/'d3d12_120_r01/bag').glob('*.mcap')).open('rb') as f:
 for schema,ch,msg in make_reader(f).iter_messages():
  if ch.topic not in ['/sim/ground_truth','/sim_evidence/scan']:continue
  classes.setdefault(schema.name,get_message(schema.name));x=deserialize_message(msg.data,classes[schema.name]);stamp=x.header.stamp.sec+x.header.stamp.nanosec/1e9
  if ch.topic=='/sim/ground_truth':poses.append((stamp,x.pose.pose))
  else:scans.append((stamp,x))
  if len(scans)>=7:break
emap=m.ElevationMap(p);times=collections.defaultdict(list);order_sizes=[]
def measured(name,fn):
 def call(*a,**kw):
  cp.cuda.runtime.deviceSynchronize();s=time.perf_counter();result=fn(*a,**kw);cp.cuda.runtime.deviceSynchronize();times[name].append(time.perf_counter()-s);return result
 return call
emap.deterministic_fusion.fuse=measured('fusion',emap.deterministic_fusion.fuse)
emap.deterministic_fusion.kernels={name:measured('kernel_'+name,kernel) for name,kernel in emap.deterministic_fusion.kernels.items()}
emap.traversability_filter=measured('builtin_cnn',emap.traversability_filter)
emap.update_normal=measured('normal',emap.update_normal)
orig_sort=cp.lexsort
def sort(a,*args,**kw):
 order_sizes.append(a.shape);return measured('lexsort',orig_sort)(a,*args,**kw)
cp.lexsort=sort
cp.flatnonzero=measured('flatnonzero',cp.flatnonzero)
for stamp,msg in scans:
 _,pose=min(poses,key=lambda x:abs(x[0]-stamp));q=pose.orientation;rot=Rotation.from_quat([q.x,q.y,q.z,q.w]).as_matrix();pos=np.array([pose.position.x,pose.position.y,pose.position.z]);origin=pos+rot@np.array([.1725,0,.5502]);poi=pos+rot@np.array([.2005158179045505,0,.4242]);pts=point_cloud2.read_points_numpy(msg,field_names=['x','y','z'],skip_nans=True);local=np.ascontiguousarray((pts-origin)@rot,dtype=np.float32)
 measured('move_to',emap.move_to)(poi,rot)
 measured('input_total',emap.input_pointcloud)(local,['x','y','z'],rot,origin,0,0,observation_stamp=stamp)
 data=np.zeros((p.cell_n-2,p.cell_n-2),np.float32)
 for layer in ['elevation','variance']:measured('copy_'+layer,emap.get_map_with_name_ref)(layer,data)
 measured('copy_age',emap.get_observation_age_ref)(stamp,data)
 print('SCAN',stamp,len(local),{k:round(v[-1]*1000,3) for k,v in times.items()},flush=True)
result={'scope':'offline single-process service profile, synchronizes each nested stage; not closed-loop timing or 120s acceptance','config_builtin_requested':cfg['enable_builtin_traversability'],'core_supports_switch':hasattr(p,'enable_builtin_traversability'),'seconds':dict(times),'sort_shapes':order_sizes}
(R/'setup/mapper-offline-profile.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:np.percentile(v[2:] or v,[50,95]).tolist() for k,v in times.items()},indent=2))
