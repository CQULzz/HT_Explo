from pathlib import Path
from collections import deque,Counter
import sys,json,math,time,subprocess
import numpy as np
from scipy.spatial import cKDTree
import rosbag2_py
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
sys.path.insert(0,'/home/lzz/HT_Explo_pcd_20261110/tools/cmu_minimal')
from audit_commands import decode
ROOT=Path('/home/lzz/pcd_test_20261110');OUT=ROOT/'analysis/ht_geometry/exact';OUT.mkdir(exist_ok=True);RUN=ROOT/'runs/user_pcd_8dir_600s_01'
start=json.loads((RUN/'observations/START.json').read_text())['clock'];targets=deque([5,10,20,30,40,50,59,70,90,120,180,240,300,420,590]);terrain=deque(maxlen=50);odometry=deque(maxlen=1000);frames=[];examples=[];totals=Counter();selected=[]
def stamp(m):return m.header.stamp.sec+m.header.stamp.nanosec*1e-9
def xyz(m):
 names=['x','y','z','intensity'];off={f.name:f.offset for f in m.fields};dtype=np.dtype({'names':names,'formats':['<f4']*4,'offsets':[off[k] for k in names],'itemsize':m.point_step});a=np.ndarray((m.height,m.width),dtype=dtype,buffer=m.data,strides=(m.row_step,m.point_step));return np.column_stack([a[k].ravel() for k in names]).astype(float)
def compare(msg,tmsg,odom,target):
 m=decode(msg);p=odom.pose.pose.position;origin=np.array([p.x,p.y]);points=xyz(tmsg);finite=np.isfinite(points).all(1);points=points[finite&(np.linalg.norm(points[:,:2]-origin,axis=1)<4.25)&(points[:,3]>.15)]
 input_path=OUT/f'terrain_{target:03d}.bin';output_path=OUT/f'voxel_{target:03d}.bin';points.astype('<f4').tofile(input_path);subprocess.run([str(OUT.parent/'voxel'),str(input_path),str(output_path)],check=True);centroid=np.fromfile(output_path,dtype='<f4').reshape(-1,4).astype(float);centroid=centroid[centroid[:,3]>.15]
 rr,cc=np.indices((m['rows'],m['cols']));xx=m['cx']+(m['rows']/2-rr-.5)*m['res'];yy=m['cy']+(m['cols']/2-cc-.5)*m['res'];xy=np.c_[xx.ravel(),yy.ravel()]
 common=(np.hypot(xx-p.x,yy-p.y)<4.25-.45)&(np.minimum.reduce([xx+13.5,13.5-xx,yy+13.5,13.5-yy])>.45)&(m['valid']>=.5)
 physical=(m['missing']==0)&(m['occupied']==0);scores=m['scores'];neural=np.isfinite(scores)&(scores>=.5)&(scores<=1)
 tree=cKDTree(centroid[:,:2]);number=tree.query_ball_point(xy,.45,return_length=True).reshape(xx.shape);nearest=tree.query(xy)[0].reshape(xx.shape)
 geometry_reject=number>=2;geometry_clear=number==0;one=number==1
 full=neural&physical[None];domain=common[None];f={}
 f['common_positions']=int(common.sum());f['common_direction_states']=int(common.sum()*8)
 f['ht_full_allowed_states']=int((domain&full).sum());f['ht_full_allowed_geometry_reject_states']=int((domain&full&geometry_reject[None]).sum());f['ht_full_allowed_geometry_clear_states']=int((domain&full&geometry_clear[None]).sum());f['ht_full_allowed_geometry_one_obstacle_states']=int((domain&full&one[None]).sum())
 f['geometry_clear_states']=int((common&geometry_clear).sum()*8);f['geometry_clear_ht_reject_states']=int((domain&geometry_clear[None]&~full).sum())
 f['ht_any_direction_allowed_positions']=int((common&full.any(0)).sum());f['ht_any_direction_allowed_geometry_reject_positions']=int((common&full.any(0)&geometry_reject).sum());f['geometry_reject_positions']=int((common&geometry_reject).sum())
 f.update(target_elapsed_s=target,ht_source_elapsed_s=stamp(msg)-start,terrain_minus_ht_source_s=stamp(tmsg)-stamp(msg),odom_minus_ht_source_s=stamp(odom)-stamp(msg),robot_xy=origin.tolist(),obstacle_centroids=len(centroid))
 frames.append(f)
 for k,v in f.items():
  if k.endswith('_states') or k.endswith('_positions'):totals[k]+=v
 conflict=common&full.any(0)&geometry_reject
 if conflict.any():
  # Pick an example near the robot; mask all three geometric thresholds below .45.
  candidates=np.argwhere(conflict);order=np.argsort(np.linalg.norm(np.c_[xx[conflict],yy[conflict]]-origin,axis=1));r,c=candidates[order[0]];x,y=xx[r,c],yy[r,c];near=tree.query_ball_point([x,y],.45)
  example={'ht_source_elapsed_s':stamp(msg)-start,'terrain_minus_ht_source_s':stamp(tmsg)-stamp(msg),'x':float(x),'y':float(y),'eight_scores':scores[:,r,c].astype(float).tolist(),'allowed_channels':np.flatnonzero(full[:,r,c]).tolist(),'ht_context_valid':True,'ht_footprint_missing':False,'ht_footprint_occupied':False,'geometry_obstacle_centroids_within_0_45m':len(near),'nearest_geometric_obstacle_m':float(nearest[r,c]),'obstacles':centroid[near].tolist()};examples.append(example)
 if len(frames) in [1,7,15]:
  np.savez_compressed(OUT/f'frame_{len(frames):02d}.npz',x=xx,y=yy,common=common,physical=physical,ht_any=full.any(0),geometry_count=number,obstacles=centroid,scores=scores)
 print('frame',target,'HT allowed',f['ht_full_allowed_states'],'geometry conflicts',f['ht_full_allowed_geometry_reject_states'],'source delta',f['terrain_minus_ht_source_s'],flush=True)
reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(RUN/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));reader.set_filter(rosbag2_py.StorageFilter(topics=['/terrain_map','/state_estimation','/ht_traversability/global_local']))
while reader.has_next() and targets:
 topic,data,received=reader.read_next()
 if topic=='/terrain_map':
  m=deserialize_message(data,PointCloud2);terrain.append((stamp(m),m))
 elif topic=='/state_estimation':
  m=deserialize_message(data,Odometry);odometry.append((stamp(m),m))
 else:
  msg=deserialize_message(data,GridMap);t=stamp(msg)
  if t<start+targets[0] or not terrain or not odometry:continue
  ts,tmsg=min(terrain,key=lambda a:abs(a[0]-t));os,odom=min(odometry,key=lambda a:abs(a[0]-t))
  if abs(ts-t)>.08 or abs(os-t)>.025:continue
  target=targets.popleft();compare(msg,tmsg,odom,target)
result={'frame_count':len(frames),'frames':frames,'totals':dict(totals),'counterexamples':examples,'remaining_targets':list(targets),'comparison_definition':{'HT':'ht_valid + full physical support/occupied dilation at radius .45 plus sqrt(2)*grid resolution + selected direction score >=.5, matching Gate spatial conditions; timestamps aligned rather than retimed','geometric_pose_proxy':'Recorded CMU terrain_map, useCost=false, intensity > .15 BEFORE .2m voxel centroid using the actual PCL VoxelGrid implementation, same 4.25m source crop; reject if >=2 obstacle centroids within circular radius .45; zero centroids clear; one is separately counted. This is a point/footprint comparison, NOT the exact native primitive correspondence and path-group score algorithm.','common_domain':'HT-valid cell centers inside source robot radius 3.8m and mission boundary inset .45m; 8 heading channels; terrain-vs-HT source time difference <=80ms, odometry <=25ms','statistics':'Correlated frame-grid-heading counts, not independent trials or ground-truth classification accuracy. Geometry clear means no obstacle in this comparison, not guaranteed real traversability.'}}
if totals['ht_full_allowed_states']:result['fraction_ht_allowed_states_with_geometric_proxy_reject']=totals['ht_full_allowed_geometry_reject_states']/totals['ht_full_allowed_states']
(OUT/'RESULT.json').write_text(json.dumps(result,indent=2));print('TOTAL',dict(totals),flush=True)
