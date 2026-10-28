from pathlib import Path
import json,sqlite3,numpy as np
from scipy.spatial.transform import Rotation,Slerp
from rclpy.serialization import deserialize_message
from tf2_msgs.msg import TFMessage
O=Path(__file__).parent;d=np.load(O/'moving_raw_points.npz');static=np.load(O/'stationary_raw_points.npz');rng=np.random.default_rng(20261029);take=np.sort(rng.choice(len(d['scan']),min(70000,len(d['scan'])),replace=False));xyz=d['sensor_xyz'][take];world=d['world_xyz'][take];scan=d['scan'][take];offset=d['time_offset_ns'][take];probes=d['probe_xy'];traj=json.load(open(O/'moving_TF_TRACK.json'));ns_by_scan={r['scan']:r['stamp_ns'] for r in traj};stamp=np.array([ns_by_scan[int(i)] for i in scan],np.int64)
db=next(Path('/media/lzz/My Passport/HT_newbags_replay_20261028/inputs/rosbag2_2026_10_28-17_00_43').rglob('*.db3'));c=sqlite3.connect('file:'+str(db)+'?mode=ro&immutable=1',uri=True);tid=c.execute("select id from topics where name='/tf'").fetchone()[0];poses={}
for (data,) in c.execute('select data from messages where topic_id=? order by timestamp',(tid,)):
 for t in deserialize_message(data,TFMessage).transforms:
  if (t.header.frame_id,t.child_frame_id)!=('map','base_link'):continue
  n=t.header.stamp.sec*10**9+t.header.stamp.nanosec;p,q=t.transform.translation,t.transform.rotation;poses[n]=([p.x,p.y,p.z],[q.x,q.y,q.z,q.w])
keys=np.array(sorted(poses),np.int64);epoch=int(keys[0]);times=(keys-epoch)/1e9;trans=np.array([poses[k][0] for k in keys]);interp=Slerp(times,Rotation.from_quat([poses[k][1] for k in keys]));local=xyz+[.4215,0.,.78499]
# Reference is a per-probe plane measured in stationary clip, not ground-truth terrain.
region=np.argmin(np.max(abs(world[:,None,:2]-probes[None]),axis=2),axis=1);coef=[]
for x,y in probes:
 v=static['world_xyz'];v=v[np.max(abs(v[:,:2]-[x,y]),axis=1)<=1.];A=np.c_[v[:,:2]-[x,y],np.ones(len(v))];coef.append(np.linalg.lstsq(A,v[:,2],rcond=None)[0])
coef=np.array(coef);rows=[]
for deskew in [False,True]:
 for delta in np.arange(-.30,.3001,.01):
  t=(stamp-epoch+(offset if deskew else 0))/1e9+delta;ok=(t>=times[0])&(t<=times[-1]);tt=t[ok];v=interp(tt).apply(local[ok])+np.column_stack([np.interp(tt,times,trans[:,k]) for k in range(3)]);reg=region[ok];pred=np.sum((v[:,:2]-probes[reg])*coef[reg,:2],axis=1)+coef[reg,2];error=v[:,2]-pred;train=scan[ok]%3!=2;test=~train;center=np.median(error[train]);row={'deskew':deskew,'offset_s':round(float(delta),3),'fitted_constant_z_offset_m':float(center),'train_mae_m':float(np.median(abs(error[train]-center))),'heldout_mae_m':float(np.median(abs(error[test]-center))),'heldout_rms_clipped12cm_m':float(np.sqrt(np.mean(np.minimum((error[test]-center)**2,.12**2))))};rows.append(row)
for deskew in [False,True]:
 subset=[r for r in rows if r['deskew']==deskew];best=min(subset,key=lambda r:r['train_mae_m']);zero=next(r for r in subset if r['offset_s']==0);print('deskew',deskew,'zero',zero,'best_by_train',best,flush=True)
(O/'TIME_OFFSET_PROBE.json').write_text(json.dumps({'scope':'Exploratory offset sweep on fixed point subset; offsets scored against stationary measured planes allowing one fitted constant datum offset. Every third scan held out. Not physical TF recalibration or independent scene.','rows':rows},indent=2)+'\n')
