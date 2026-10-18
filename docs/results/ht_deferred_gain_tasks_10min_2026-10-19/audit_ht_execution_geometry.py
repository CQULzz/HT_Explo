from pathlib import Path
import argparse,json,csv,math
import numpy as np
from scipy.spatial import cKDTree
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry,Path as RosPath
from geometry_msgs.msg import TwistStamped
from sensor_msgs_py import point_cloud2
p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
origin=json.loads((a.trial/'current/measurement_started.json').read_text())['wall_time'];radius=.5+.5*math.hypot(.2,.2)
r=rosbag2_py.SequentialReader();r.open(rosbag2_py.StorageOptions(uri=str(a.trial/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));r.set_filter(rosbag2_py.StorageFilter(topics=['/state_estimation','/cmd_vel','/ht_xytheta_path','/collision_cloud']))
robot=None;cmd=(0.,0.);path=[];rows=[];trajectory=[];tree=None;cloudstamp=0;first=None;pathstamp=0;pathrows=[]
while r.has_next():
 topic,data,ns=r.read_next();t=ns/1e9-origin
 if t<0 or t>600:continue
 if topic=='/state_estimation':
  m=deserialize_message(data,Odometry);v=m.pose.pose.position;q=m.pose.pose.orientation;robot=np.array([v.x,v.y,v.z,math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))]);trajectory.append([t,*robot])
 elif topic=='/cmd_vel':
  m=deserialize_message(data,TwistStamped);cmd=(m.twist.linear.x,m.twist.angular.z)
 elif topic=='/ht_xytheta_path':
  m=deserialize_message(data,RosPath);path=[(v.pose.position.x,v.pose.position.y) for v in m.poses];pathstamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9-origin
  if tree and path:
   ds=tree.query(np.asarray(path))[0];pathrows.append(dict(t_s=t,header_s=pathstamp,root_clearance=float(ds[0]),minimum_clearance=float(np.min(ds)),near_minimum=float(np.min(ds[:min(11,len(ds))])),root=path[0],points=len(path)))
 elif robot is not None:
  m=deserialize_message(data,PointCloud2);xyz=point_cloud2.read_points(m,field_names=('x','y','z'),skip_nans=True);xyz=np.column_stack([xyz[n] for n in ('x','y','z')]);z=(xyz[:,2]>=robot[2]-.5)&(xyz[:,2]<=robot[2]+.5);body=xyz[z];tree=cKDTree(body[:,:2]) if len(body) else None
  d=float(tree.query(robot[:2])[0]) if tree else math.inf
  predicted=robot[[0,1,3]].copy();horizon=max(.2,max(abs(cmd[0])/.5,abs(cmd[1])/1.2)+.1);minimum=d
  for tau in np.arange(0,horizon,.05):
   predicted[:2]+=cmd[0]*.05*np.array([math.cos(predicted[2]+cmd[1]*.025),math.sin(predicted[2]+cmd[1]*.025)]);predicted[2]+=cmd[1]*.05
   if tree:minimum=min(minimum,float(tree.query(predicted[:2])[0]))
  row=dict(t_s=t,cloud_source_s=m.header.stamp.sec+m.header.stamp.nanosec*1e-9-origin,x=float(robot[0]),y=float(robot[1]),yaw=float(robot[3]),min_xy_m=d,command_v=cmd[0],command_w=cmd[1],predicted_min_xy_m=minimum,path_stamp_s=pathstamp,cloud_points=len(body));rows.append(row)
  if first is None and d<radius:
   first=row;np.savez_compressed(a.output/'first_overlap.npz',cloud=xyz,robot=robot,path=np.asarray(path),trajectory=np.asarray(trajectory));
with (a.output/'clearance.csv').open('w') as f:
 if rows:w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
(a.output/'paths.json').write_text(json.dumps(pathrows,indent=2)+'\n')
result=dict(radius_m=radius,collision_point_threshold=1,first_observed_margin_overlap=first,overlap_samples=sum(v['min_xy_m']<radius for v in rows),moving_predictions_inside_margin=sum(v['predicted_min_xy_m']<radius and abs(v['command_v'])>.01 and v['min_xy_m']>=radius for v in rows),samples=len(rows),limitations='Uses bag arrival order, latest received odometry/command and measured collision-cloud points in robot height slice. Does not reproduce planner collision-grid bounds or exact callback state. Predicted arc uses last received constant Twist, not controller internal candidate or simulator braking. Margin overlap is not physical vehicle contact. Sample lag/point noise may contribute; cannot separate them without independent truth.')
(a.output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
fig,ax=plt.subplots(2,1,figsize=(10,7));ax[0].plot([v['t_s'] for v in rows],[v['min_xy_m'] for v in rows],label='Observed obstacle clearance');ax[0].plot([v['t_s'] for v in rows],[v['predicted_min_xy_m'] for v in rows],label='Last command arc clearance');ax[0].axhline(radius,color='red',ls='--',label='Existing collision margin');ax[0].set_ylim(0,2);ax[0].set_ylabel('Reference XY distance (m)');ax[0].legend()
ax[1].plot([v['t_s'] for v in rows],[v['command_v'] for v in rows]);ax[1].set_ylabel('Command v (m/s)');ax[1].set_xlabel('Measurement seconds')
for z in ax:z.grid(alpha=.2)
fig.tight_layout();fig.savefig(a.output/'clearance.png',dpi=180)
if first:
 d=np.load(a.output/'first_overlap.npz');v=d['robot'];cloud=d['cloud'];sel=(np.linalg.norm(cloud[:,:2]-v[:2],axis=1)<2)&(abs(cloud[:,2]-v[2])<=.5);fig,ax=plt.subplots(figsize=(8,7));ax.scatter(cloud[sel,0],cloud[sel,1],s=1,c='gray',label='Observed collision points');traj=d['trajectory'];sel=traj[:,0]>=first['t_s']-15;ax.plot(traj[sel,1],traj[sel,2],color='blue',label='Executed odometry');path=d['path'];
 if len(path):ax.plot(path[:,0],path[:,1],color='orange',label='Last received planned path')
 ax.add_patch(plt.Circle(v[:2],radius,fill=False,color='red',label='Collision margin'));ax.scatter([v[0]],[v[1]],c='black');ax.set_xlim(v[0]-2,v[0]+2);ax.set_ylim(v[1]-2,v[1]+2);ax.set_aspect('equal');ax.set_xlabel('Map X (m)');ax.set_ylabel('Map Y (m)');ax.legend();fig.tight_layout();fig.savefig(a.output/'first_overlap.png',dpi=180)
print(json.dumps(result,indent=2))
