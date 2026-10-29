from pathlib import Path
from copy import deepcopy
import sqlite3,json,sys,numpy as np
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points,read_points_numpy
R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028/inputs');O=Path(__file__).parent;sys.path.insert(0,str(R/'src/ht_scout_bridge'))
from ht_scout_bridge.geometry import load_calibration,self_filter_keep_mask,wheel_occlusion_mask
p,b,l=load_calibration(R/'src/ht_scout_bridge/config/scout_extrinsics.yaml');T=np.linalg.inv(b)@l;new=p['lidar_self_filter'];old=deepcopy(new);old.pop('wheel_occlusion');bare=deepcopy(new['wheel_occlusion']);bare['preserve_vertical_support']=False;allrows=[];groups=[]
for db in sorted(B.rglob('*.db3')):
 bag='moving' if '17_00_43' in str(db) else 'stationary';c=sqlite3.connect('file:'+str(db)+'?mode=ro&immutable=1',uri=True);tid=c.execute("select id from topics where name='/rslidar_points'").fetchone()[0];packed_old=[];packed_new=[];stamps=[];sizes=[];rows=[]
 for scan,(data,) in enumerate(c.execute('select data from messages where topic_id=? order by timestamp',(tid,))):
  m=deserialize_message(data,PointCloud2);xyz=read_points_numpy(m,field_names=('x','y','z'),skip_nans=False).reshape(-1,3);before=self_filter_keep_mask(xyz,old,T);after=self_filter_keep_mask(xyz,new,T);assert not np.any(after&~before);body=xyz@T[:3,:3].T+T[:3,3];remove=before&~after;ground=before&(abs(body[:,2]+.23479)<=.03);high=before&(body[:,2]>new['wheel_occlusion']['max_return_z_m']+1e-6);assert not (remove&ground).any();assert not (remove&high).any()
  ids=np.flatnonzero(before);raw=wheel_occlusion_mask(body[ids],T[:3,3],new['cylinders'],bare);shadow=np.zeros(len(xyz),bool);shadow[ids]=raw;assert not (remove&~shadow).any();ns=m.header.stamp.sec*10**9+m.header.stamp.nanosec
  row={'bag':bag,'scan':scan,'stamp_ns':ns,'points':len(xyz),'old_kept':int(before.sum()),'new_kept':int(after.sum()),'extra_removed':int(remove.sum()),'body_ground_candidates':int(ground.sum()),'extra_ground_removed':int((remove&ground).sum()),'above_wheel_candidates':int(high.sum()),'extra_above_wheel_removed':int((remove&high).sum()),'raw_shadow_candidates':int(shadow.sum()),'retained_by_visible_vertical_support':int((shadow&after).sum())};rows.append(row);packed_old.append(np.packbits(before));packed_new.append(np.packbits(after));stamps.append(ns);sizes.append(len(xyz))
  if bag=='moving' and scan==95:
   # Timestamp ~9.5s, independently selected in previous body audit.
   fields=read_points(m,skip_nans=False).reshape(-1);np.savez_compressed(O/'POINT_EVIDENCE_scan95.npz',sensor_xyz=xyz,body_xyz=body,old_keep=before,new_keep=after,raw_shadow=shadow,channel=fields['channel'],return_type=fields['return_type'],lidar_distance=fields['distance'],lidar_from_body=np.linalg.inv(T),stamp_ns=ns)
 np.savez_compressed(O/(bag+'_POINT_MASKS.npz'),old_packed=np.stack(packed_old),new_packed=np.stack(packed_new),source_stamp_ns=stamps,source_point_count=sizes,bitorder='big');group={'bag':bag,'raw_scans_audited':len(rows),**{k:sum(r[k] for r in rows) for k in ['points','old_kept','new_kept','extra_removed','body_ground_candidates','extra_ground_removed','above_wheel_candidates','extra_above_wheel_removed','raw_shadow_candidates','retained_by_visible_vertical_support']}};groups.append(group);allrows.extend(rows);c.close();print(group,flush=True)
(O/'POINT_AUDIT.json').write_text(json.dumps({'scope':'All raw scans, including source scans lacking TF: body-frame filter needs no world pose. Ground band and above-wheel categories are model-coordinate checks, not human terrain labels. Packed masks retain full original point ordering.','summary':groups,'rows':allrows},indent=2)+'\n')
