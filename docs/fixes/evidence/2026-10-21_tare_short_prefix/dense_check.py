import sys,json,math
from pathlib import Path
import numpy as np,cv2
import rosbag2_py
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Path as RosPath,Odometry
from grid_map_msgs.msg import GridMap
sys.path.insert(0,str(Path.cwd()/'presentations'))
from audit_pose_admissibility_changes import Field
trial=Path('presentations/scheduled_results/ht_tare_native_5scene_10min_2026-10-20_19-39-37/garage')
out=Path('.git/diagnostics/garage_prefix_rootcause')
origin=json.load(open(trial/'current/measurement_started.json'))['wall_time']
r=rosbag2_py.SequentialReader();r.open(rosbag2_py.StorageOptions(uri=str(trial/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));r.set_filter(rosbag2_py.StorageFilter(topics=['/tare_route_branch','/ht_traversability/global_local','/state_estimation']))
field=None;pose=None;reports=[]
def pref(branch,length):
 for p,q in zip(branch,branch[1:]):
  d=np.linalg.norm(q-p)
  if d>1e-9 and d>=length:return p+(q-p)*(length/d)
  length-=d
 return branch[-1]
def inspect(f,p):
 return [f.inspect([*p,k*np.pi/4])['status'] for k in range(8)]
def ht_direct(f,start,end):
 # Current-pose rotations and entire straight translation, exact raster-cell supercover.
 yaw=math.atan2(end[1]-start[1],end[0]-start[0]);delta=(yaw-start[2]+math.pi)%(2*math.pi)-math.pi
 headings=[start[2]+delta*i/100 for i in range(101)]
 if any(f.inspect([*start[:2],h])['status']!='KNOWN' for h in headings):return False
 def grid(p):return np.array([f.n*.5-(p[0]-f.cx)/f.res,f.n*.5-(p[1]-f.cy)/f.res])
 a=grid(start);b=grid(end);v=b-a;k=int(math.floor(yaw/(math.pi/4)+.5))%8
 cuts={0.,1.}
 for axis in range(2):
  if abs(v[axis])<1e-12:continue
  for line in range(math.floor(min(a[axis],b[axis]))+1,math.ceil(max(a[axis],b[axis]))):
   t=(line-a[axis])/v[axis]
   if 0<t<1:cuts.add(float(t))
 cuts=sorted(cuts);ts=cuts+[(x+y)/2 for x,y in zip(cuts,cuts[1:])]
 cells=set()
 for t in ts:
  p=a+t*v;rr=[math.floor(p[0])];cc=[math.floor(p[1])]
  if abs(p[0]-round(p[0]))<1e-9:rr=[round(p[0])-1,round(p[0])]
  if abs(p[1]-round(p[1]))<1e-9:cc=[round(p[1])-1,round(p[1])]
  cells.update((r,c) for r in rr for c in cc)
 return all(0<=r<f.n and 0<=c<f.n and f.valid[r,c] and not f.unknown[r,c] and not f.blocked[k,r,c] for r,c in cells)
def intervals(vals):
 result=[]
 for x,ok in vals:
  if ok:
   if not result or x-result[-1][-1]>.050001:result.append([x])
   else:result[-1].append(x)
 return [[round(a[0],2),round(a[-1],2),len(a)] for a in result]
while r.has_next():
 topic,raw,ns=r.read_next();t=ns/1e9-origin
 if t<575:continue
 if t>=600:break
 if topic=='/ht_traversability/global_local':field=Field(deserialize_message(raw,GridMap),'configuration')
 elif topic=='/state_estimation':
  m=deserialize_message(raw,Odometry);p=m.pose.pose.position;q=m.pose.pose.orientation;pose=[p.x,p.y,math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))]
 elif field is not None and pose is not None:
  m=deserialize_message(raw,RosPath);b=np.array([[p.pose.position.x,p.pose.position.y] for p in m.poses]);total=sum(np.linalg.norm(q-p) for p,q in zip(b,b[1:]));rows=[]
  for step in [.05,.2,.25]:
   vals=[]
   for length in np.arange(0,min(6,total)+1e-5,step):
    p=pref(b,length);dist=np.linalg.norm(p-np.array(pose[:2]));states=inspect(field,p);ok=dist>=.4 and 'KNOWN' in states;vals.append((float(length),ok))
   accepted=[round(l,3) for l,ok in vals if ok]
   rows.append(dict(step=step,accepted_prefixes=accepted,accepted_le4=[l for l in accepted if l<=4],accepted_under1=[l for l in accepted if l<1],runs=intervals(vals) if step==.05 else None))
  fixed={str(l):inspect(field,pref(b,l)) for l in [4.,3.,2.,1.,5.]}
  ht_only_direct={str(l):ht_direct(field,pose,pref(b,l)) for l in [0.,.05,.1,.2,.25,.3,3.6,3.8,3.9,5.]}
  reports.append(dict(t=t,map_stamp=field.stamp,map_age=t+origin-field.stamp,pose=pose,robot_support=inspect(field,np.array(pose[:2])),branch=b.tolist(),branch_total=total,branch_anchor_distance=float(np.linalg.norm(b[0]-pose[:2])),fixed=fixed,ht_only_direct=ht_only_direct,samples=rows))
(out/'dense_checks.json').write_text(json.dumps(reports,indent=2)+'\n')
print(json.dumps(reports[-1],indent=2))
print('branch count',len(reports))
