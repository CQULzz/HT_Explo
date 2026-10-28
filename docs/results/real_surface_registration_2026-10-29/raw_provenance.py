from pathlib import Path
import sqlite3,json,sys,numpy as np
from scipy.spatial.transform import Rotation,Slerp
from rclpy.serialization import deserialize_message
from rclpy.time import Time
from rclpy.duration import Duration
from tf2_ros import Buffer
from tf2_msgs.msg import TFMessage
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points
R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028/inputs');O=Path(__file__).parent
sys.path.insert(0,str(R/'src/ht_scout_bridge'));sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
from ht_scout_bridge.geometry import load_calibration,self_filter_keep_mask
from replay_newbags_rviz import matrix
profile,b,l=load_calibration(R/'src/ht_scout_bridge/config/scout_extrinsics.yaml');base_lidar=np.linalg.inv(b)@l
probes=np.array([[-.48,12.24],[-3.,13.],[-1.,18.]])
summary=[]
for db in sorted(B.rglob('*.db3')):
 role='moving' if '17_00_43' in str(db) else 'stationary';c=sqlite3.connect('file:'+str(db)+'?mode=ro&immutable=1',uri=True);topics={n:i for i,n in c.execute('select id,name from topics')};buf=Buffer(cache_time=Duration(seconds=180.));trajectory={}
 for topic in ['/tf_static','/tf']:
  for (data,) in c.execute('select data from messages where topic_id=? order by timestamp',(topics[topic],)):
   for t in deserialize_message(data,TFMessage).transforms:
    (buf.set_transform_static if topic=='/tf_static' else buf.set_transform)(t,'recorded')
    if (t.header.frame_id,t.child_frame_id)==('map','base_link'):
     ns=t.header.stamp.sec*10**9+t.header.stamp.nanosec;trajectory[ns]=matrix(t)
 keys=np.array(sorted(trajectory),np.int64);epoch=int(keys[0]);times=(keys-epoch)/1e9;trans=np.array([trajectory[k][:3,3] for k in keys]);rots=Rotation.from_matrix([trajectory[k][:3,:3] for k in keys]);interp=Slerp(times,rots)
 rows=[];out={k:[] for k in ['world_xyz','deskew_xyz','sensor_xyz','channel','scan','time_offset_ns']}
 skipped=0;tftrack=[]
 for scan,(data,) in enumerate(c.execute('select data from messages where topic_id=? order by timestamp',(topics['/rslidar_points'],))):
  m=deserialize_message(data,PointCloud2);ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec
  try:T=matrix(buf.lookup_transform('map',m.header.frame_id,Time(nanoseconds=ns)))
  except Exception:skipped+=1;continue
  p=read_points(m,skip_nans=False).reshape(-1);xyz=np.c_[p['x'],p['y'],p['z']];keep=self_filter_keep_mask(xyz,profile['lidar_self_filter'],base_lidar);world=xyz@T[:3,:3].T+T[:3,3]
  roi=keep & (np.min(np.max(abs(world[:,None,:2]-probes[None]),axis=2),axis=1)<=1.3)
  # Broad relative-height gate excludes ceilings; not a ground-truth flat mask.
  roi &= (world[:,2]>T[2,3]-1.25)&(world[:,2]<T[2,3]-.25)
  ii=np.flatnonzero(roi);pts=xyz[ii];w=world[ii];offset=p['time_stamp'][ii].astype(np.int64);pointtime=(ns-epoch+offset)/1e9;valid=(pointtime>=times[0])&(pointtime<=times[-1]);desk=np.full(w.shape,np.nan)
  if valid.any():
   lidar_from_base=matrix(buf.lookup_transform('base_link',m.header.frame_id,Time(nanoseconds=ns)));local=pts[valid]@lidar_from_base[:3,:3].T+lidar_from_base[:3,3]
   tt=pointtime[valid];translation=np.column_stack([np.interp(tt,times,trans[:,k]) for k in range(3)]);desk[valid]=interp(tt).apply(local)+translation
  if len(ii):
   out['world_xyz'].append(w.astype(np.float32));out['deskew_xyz'].append(desk.astype(np.float32));out['sensor_xyz'].append(pts);out['channel'].append(p['channel'][ii]);out['scan'].append(np.full(len(ii),scan,np.int32));out['time_offset_ns'].append(offset)
   displacement=desk[valid]-w[valid];rows.append({'scan':scan,'stamp_ns':ns,'points_in_fixed_probes':len(ii),'deskew_vertical_abs_p99_m':float(np.quantile(abs(displacement[:,2]),.99)) if valid.any() else None,'deskew_xyz_norm_p99_m':float(np.quantile(np.linalg.norm(displacement,axis=1),.99)) if valid.any() else None})
  tftrack.append({'scan':scan,'stamp_ns':ns,'lidar_world_matrix':T.tolist()})
 for k in out:out[k]=np.concatenate(out[k])
 np.savez_compressed(O/(role+'_raw_points.npz'),**out,probe_xy=probes)
 aggregate={}
 for j,(x,y) in enumerate(probes):
  z=out['world_xyz'];use=np.max(abs(z[:,:2]-[x,y]),axis=1)<=1.;v=z[use];s=out['scan'][use];ring=out['channel'][use]
  if len(v)<20:continue
  A=np.c_[v[:,:2]-[x,y],np.ones(len(v))];coef=np.linalg.lstsq(A,v[:,2],rcond=None)[0]
  for _ in range(5):
   error=v[:,2]-A@coef;weights=np.minimum(1.,.03/np.maximum(abs(error),1e-6));coef=np.linalg.lstsq(A*weights[:,None],v[:,2]*weights,rcond=None)[0]
  residual=v[:,2]-A@coef;clean=abs(residual)<.12;v=v[clean];s=s[clean];ring=ring[clean];residual=residual[clean]
  bins=np.floor(v[:,:2]/.04+.5).astype(np.int64);_,cell=np.unique(bins,axis=0,return_inverse=True)
  # Median removal of stationary cell shape tests temporal consistency; it does not prove physical flatness.
  means=np.bincount(cell,weights=residual)/np.bincount(cell);within=residual-means[cell];byring=[]
  for k in np.unique(ring):
   q=within[ring==k];byring.append({'channel':int(k),'n':len(q),'median_after_cell_mean_m':float(np.median(q)),'rms_after_cell_mean_m':float(np.sqrt(np.mean(q*q)))})
  aggregate[str(j)]={'world_xy':[x,y],'points':len(v),'scans':int(len(np.unique(s))),'raw_plane_rms_m':float(np.sqrt(np.mean(residual**2))),'within_4cm_cell_rms_m':float(np.sqrt(np.mean(within**2))),'by_channel':byring}
 record={'bag':role,'source_db':str(db),'exact_tf_skips':skipped,'point_time_interpretation':'Diagnostic assumption: time_stamp UINT32 is nanoseconds offset from cloud header; no deployment of deskew.','per_scan':rows,'fixed_probe_raw_stats':aggregate}
 (O/(role+'_RAW_PROVENANCE.json')).write_text(json.dumps(record,indent=2)+'\n');(O/(role+'_TF_TRACK.json')).write_text(json.dumps(tftrack)+'\n');summary.append({'bag':role,'points':len(out['scan']),'median_scan_vertical_deskew_p99_m':float(np.median([r['deskew_vertical_abs_p99_m'] for r in rows if r['deskew_vertical_abs_p99_m'] is not None])),'raw_probe_stats':aggregate});print(role,len(out['scan']),flush=True);c.close()
(O/'RAW_SUMMARY.json').write_text(json.dumps(summary,indent=2)+'\n')
