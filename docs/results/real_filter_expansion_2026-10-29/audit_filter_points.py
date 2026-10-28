from pathlib import Path
from copy import deepcopy
import json,sqlite3,sys,numpy as np
R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');O=Path('/media/lzz/My Passport/HT_filter_expansion_2026-10-29');sys.path.insert(0,str(R/'src/ht_scout_bridge'));sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
import rclpy
from rclpy.duration import Duration
from rclpy.time import Time
from rclpy.serialization import deserialize_message
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points_numpy
from replay_newbags_rviz import matrix
from ht_scout_bridge.geometry import load_calibration,self_filter_keep_mask
profile,b,l=load_calibration(R/'src/ht_scout_bridge/config/scout_extrinsics.yaml');base_lidar=np.linalg.inv(b)@l;rows=[];rclpy.init()
for suffix,stem in [('165317','rosbag2_2026_10_28-16_53_17'),('170043','rosbag2_2026_10_28-17_00_43')]:
 ref=json.loads((B/('rebuild_'+suffix)/'RESULTS.json').read_text());db=next((B/'inputs'/stem/stem).glob('*.db3'));c=sqlite3.connect('file:'+str(db)+'?mode=ro&immutable=1',uri=True);ids={n:i for i,n in c.execute('select id,name from topics')};buf=Buffer(cache_time=Duration(seconds=180.))
 for name in ['/tf_static','/tf']:
  for (blob,) in c.execute('select data from messages where topic_id=? order by timestamp',(ids[name],)):
   for t in deserialize_message(blob,TFMessage).transforms:(buf.set_transform_static if name=='/tf_static' else buf.set_transform)(t,'recorded')
 chosen={f['scan']:(idx,f) for idx,f in enumerate(ref['frames'])}
 for scan,(blob,) in enumerate(c.execute('select data from messages where topic_id=? order by timestamp',(ids['/rslidar_points'],))):
  if scan not in chosen:continue
  idx,f=chosen[scan];m=deserialize_message(blob,PointCloud2);xyz=read_points_numpy(m,field_names=('x','y','z'),skip_nans=False).reshape(-1,3);T=matrix(buf.lookup_transform('map','scout_chassis_link',Time(nanoseconds=f['stamp_ns'])));bp=xyz@base_lidar[:3,:3].T+base_lidar[:3,3];wp=bp@T[:3,:3].T+T[:3,3];d=ref['diagnostics'][idx]['surface'];z=np.load(B/('rebuild_'+suffix)/'frames'/f['file']);refh=d['reference_center_m']+d['slope_xy'][0]*(wp[:,0]-z['center'][0])+d['slope_xy'][1]*(wp[:,1]-z['center'][1]);residual=wp[:,2]-refh
  old=self_filter_keep_mask(xyz,profile['lidar_self_filter'],base_lidar);rear=(bp[:,0]<-.25)&(bp[:,0]>-1.5)&(abs(bp[:,1])<.8);bump=rear&(residual>.06)&(residual<.25)&old;ground=old&(abs(residual)<=.03);high=old&(residual>=.15)
  for margin in [.05,.1,.2]:
   pp=deepcopy(profile['lidar_self_filter']);pp['horizontal_padding_m']=margin;keep=self_filter_keep_mask(xyz,pp,base_lidar);removed=old&~keep
   rows.append(dict(scene=suffix,frame=idx,t_s=f['t_s'],margin_m=margin,additional_removed=int(removed.sum()),baseline_bump_points=int(bump.sum()),removed_bump_points=int((removed&bump).sum()),baseline_candidate_ground_points=int(ground.sum()),removed_candidate_ground_points=int((removed&ground).sum()),removed_above15cm_points=int((removed&high).sum())))
 c.close();print('sampled',suffix,len(ref['frames']),'source scans at original HT source times',flush=True)
rclpy.try_shutdown();summary=[]
for scene in ['165317','170043']:
 for margin in [.05,.1,.2]:
  group=[r for r in rows if r['scene']==scene and r['margin_m']==margin];summary.append(dict(scene=scene,margin_m=margin,source_scans_sampled=len(group),**{k:sum(r[k] for r in group) for k in ['additional_removed','baseline_bump_points','removed_bump_points','baseline_candidate_ground_points','removed_candidate_ground_points','removed_above15cm_points']}))
(O/'POINT_REMOVAL_AUDIT.json').write_text(json.dumps({'scope':'Original source scans at each HT output time, ground/bump categories relative to local fitted plane; not human ground truth; repeated returns are not unique physical points','summary':summary,'rows':rows},indent=2)+'\n');print(summary,flush=True)
