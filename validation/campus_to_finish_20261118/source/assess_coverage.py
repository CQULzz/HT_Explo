from pathlib import Path
import json,csv,math
import numpy as np
from scipy.spatial import cKDTree
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('/home/lzz/ht_campus_to_finish_20261118');run=root/'runs/campus_to_finish_01';out=root/'analysis';start=json.loads((run/'observations/START.json').read_text())['clock'];rows=list(csv.DictReader((run/'observations/metrics.csv').open()));end=float(rows[-1]['time']);reference=np.load(out/'CAMPUS_REFERENCE_05M.npz')['voxels'];ground=np.load(out/'REFERENCE_GROUND_PROXY.npz')['connected_ground_xyz']
def key(m):return m.header.stamp.sec*1000000000+m.header.stamp.nanosec
def xyz(m):
 fields={f.name:f.offset for f in m.fields};dt=np.dtype({'names':['x','y','z'],'formats':['<f4']*3,'offsets':[fields[k] for k in ['x','y','z']],'itemsize':m.point_step});a=np.ndarray((m.height,m.width),dtype=dt,buffer=m.data,strides=(m.row_step,m.point_step));return np.column_stack([a[k].ravel() for k in ['x','y','z']])
rd=rosbag2_py.SequentialReader();rd.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));rd.set_filter(rosbag2_py.StorageFilter(topics=['/registered_scan','/state_estimation_at_scan']));poses={};pending={};observed=set();last=-1e9;used=0;total_scans=0;unmatched=0
progress=[]
def process(m):
 global last,used
 stamp=key(m)/1e9
 if not start<=stamp<=end or stamp-last<1:return
 origin=poses.get(key(m))
 if origin is None:return
 pts=xyz(m);pts=pts[np.isfinite(pts).all(1)];pts=pts[np.linalg.norm(pts-origin,axis=1)<=15.];cells=np.unique(np.floor(pts/.5).astype(np.int32),axis=0);observed.update(map(tuple,cells));last=stamp;used+=1
 if used%100==0:print('Matched sampled scans',used,'unique observation voxels',len(observed),flush=True)
while rd.has_next():
 topic,data,t=rd.read_next()
 if topic=='/state_estimation_at_scan':
  m=deserialize_message(data,Odometry);p=m.pose.pose.position;poses[key(m)]=np.array([p.x,p.y,p.z])
  if key(m) in pending:process(pending.pop(key(m)))
  if len(poses)>100:poses.pop(next(iter(poses)))
 else:
  total_scans+=1;m=deserialize_message(data,PointCloud2)
  if key(m) in poses:process(m)
  else:pending[key(m)]=m
  if len(pending)>100:pending.pop(next(iter(pending)));unmatched+=1
assert used>0
obs=(np.array(list(observed),np.float32)+.5)*.5;ref=(reference.astype(np.float32)+.5)*.5;tree=cKDTree(obs);dist=tree.query(ref,workers=2)[0];gdist=tree.query(ground,workers=2)[0];matched=dist<=.75;gm=gdist<=.75;np.savez_compressed(out/'COVERAGE_REFERENCE_COMPARISON.npz',reference_voxel_centers=ref,reference_matched=matched,ground_proxy_xyz=ground,ground_proxy_matched=gm,observed_voxel_centers=obs)
traj=np.array([[float(r[k]) for k in ['x','y','yaw']] for r in rows]);traj[:,0]-=.1725*np.cos(traj[:,2]);traj[:,1]-=.1725*np.sin(traj[:,2]);to_route=cKDTree(traj[:,:2]).query(ground[:,:2],workers=2)[0];far=(~gm)&(to_route>20);examples=ground[far][np.linspace(0,max(0,far.sum()-1),min(8,int(far.sum()))).astype(int)].tolist() if far.any() else []
result={'source':'Independent official campus preview pointcloud, SHA in CAMPUS_REFERENCE.json','sampled_scans_used':used,'registered_scans_read':total_scans,'unpaired_scan_evictions':unmatched,'observation_sampling':'At most 1 frame per wall-stamped second, endpoints within15m of exact paired scanner pose; finite raw registered scan returns only','voxel_size_m':.5,'nearest_observed_voxel_center_tolerance_m':.75,'all_reference_surface_voxels':len(ref),'matched_reference_surface_voxels':int(matched.sum()),'reference_surface_matched_fraction':float(matched.mean()),'connected_ground_proxy_cells':len(ground),'matched_ground_proxy_cells':int(gm.sum()),'ground_proxy_observed_fraction':float(gm.mean()),'unobserved_ground_proxy_cells_over20m_from_recorded_route':int(far.sum()),'unobserved_ground_proxy_examples_xyz':examples,'limitations':'Surface match and pointcloud-derived ground connectivity are diagnostic proxies; neither is a certified ground-truth coverage percentage. Cannot infer all unmatched structures are reachable or require observation.'};(out/'COVERAGE_ASSESSMENT.json').write_text(json.dumps(result,indent=2))
fig,axes=plt.subplots(1,2,figsize=(15,7));a=axes[0];a.scatter(ref[::4,0],ref[::4,1],s=.15,c='#cbd5e1',label='Independent campus reference surfaces');a.scatter(obs[:,0],obs[:,1],s=.12,c='#0284c7',label='Measured endpoints, <=15m, sampled1Hz');a.plot(traj[:,0],traj[:,1],c='#ef4444',lw=1,label='Actual base trajectory');a.set_title('Full campus reference and actual observation extent')
a=axes[1];a.scatter(ground[~gm,0],ground[~gm,1],s=1,c='#d97706',label='Unmatched connected-ground proxy');a.scatter(ground[gm,0],ground[gm,1],s=1,c='#0f766e',label='Matched ground proxy');a.plot(traj[:,0],traj[:,1],c='#ef4444',lw=1,label='Actual base trajectory');a.set_title('Conservative ground proxy; not certified traversability')
for a in axes:a.set_aspect('equal');a.set_xlabel('World X (m)');a.set_ylabel('World Y (m)');a.grid(alpha=.15);a.legend(markerscale=4,fontsize=8)
fig.tight_layout();fig.savefig(out/'campus_reference_coverage.png',dpi=160);plt.close(fig);print(json.dumps(result,indent=2),flush=True)
