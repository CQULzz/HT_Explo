from pathlib import Path
import json,sys,sqlite3,numpy as np
R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');O=B/'red_region_audit';sys.path.insert(0,str(R/'src/ht_scout_bridge'))
from ht_scout_bridge.geometry import load_calibration,self_filter_keep_mask
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points_numpy,read_points
from rclpy.serialization import deserialize_message
profile,b,l=load_calibration(R/'src/ht_scout_bridge/config/scout_extrinsics.yaml');base_lidar=np.linalg.inv(b)@l
r=json.loads((B/'rebuild_170043/RESULTS.json').read_text());v=json.loads((O/'CONTEXT_VERIFY.json').read_text());db=next((B/'inputs/rosbag2_2026_10_28-17_00_43/rosbag2_2026_10_28-17_00_43').glob('*.db3'));c=sqlite3.connect('file:'+str(db)+'?mode=ro&immutable=1',uri=True);tid=c.execute("select id from topics where name='/rslidar_points'").fetchone()[0];out=[]
for index in [10,11,15,17,19,23,27,31,35,39,43,47]:
 row=r['frames'][index];blob=c.execute('select data from messages where topic_id=? order by timestamp limit 1 offset ?',(tid,row['scan'])).fetchone()[0];m=deserialize_message(blob,PointCloud2);xyz=read_points_numpy(m,field_names=('x','y','z'),skip_nans=False).reshape(-1,3);bp=xyz@base_lidar[:3,:3].T+base_lidar[:3,3];keep=self_filter_keep_mask(xyz,profile['lidar_self_filter'],base_lidar);T=np.array(v[index]['vehicle_matrix']);wp=bp@T[:3,:3].T+T[:3,3];diag=r['diagnostics'][index]['surface'];center=np.load(B/'rebuild_170043/frames'/row['file'])['center'];plane=diag['reference_center_m']+diag['slope_xy'][0]*(wp[:,0]-center[0])+diag['slope_xy'][1]*(wp[:,1]-center[1]);dz=wp[:,2]-plane
 mask=keep&(dz>.06)&(dz<.25)&(bp[:,0]>-1.5)&(bp[:,0]<-.25)&(abs(bp[:,1])<.8)
 selected=bp[mask];extra=read_points(m,field_names=('channel','return_type','distance','azimuth','elevation'),skip_nans=False).reshape(-1);channels,counts=np.unique(extra['channel'][mask],return_counts=True);record={'frame':index,'t_s':row['t_s'],'source_header_ns':m.header.stamp.sec*10**9+m.header.stamp.nanosec,'retained_raw_points_in_rear_bump_region':int(mask.sum()),'body_point_min_median_max':np.quantile(selected,[0,.5,1],axis=0).tolist() if len(selected) else None,'height_above_fitted_ground_min_median_max':np.quantile(dz[mask],[0,.5,1]).tolist() if len(selected) else None};record['channel_counts']={str(int(k)):int(v) for k,v in zip(channels,counts)};record['lidar_range_m_quantiles']=np.quantile(np.linalg.norm(xyz[mask],axis=1),[0,.5,1]).tolist() if mask.any() else None;record['encoded_elevation_quantiles']=np.quantile(extra['elevation'][mask],[0,.5,1]).tolist() if mask.any() else None;out.append(record)
 if False:np.savez_compressed(O/'frame17_raw_rear_points.npz',body_xyz=selected,world_xyz=wp[mask],height_above_plane=dz[mask])
 print(record,flush=True)
(O/'RAW_POINT_CHANNEL_AUDIT.json').write_text(json.dumps(out,indent=2)+'\n');c.close()
