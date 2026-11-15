from pathlib import Path
import json,csv,time,os
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
root=Path(os.environ['HT_VIDEO_ROOT']);root.mkdir(exist_ok=True);(root/'frames').mkdir(exist_ok=True)
run=Path(os.environ['HT_VIDEO_RUN'])
start=json.loads((run/'observations/START.json').read_text())['clock']
rows=list(csv.DictReader((run/'observations/metrics.csv').open()))
trajectory=np.array([[float(r[k]) for k in ['elapsed_s','x','y','z','yaw','distance_m','sampled_free_volume_m3']] for r in rows])
np.save(root/'trajectory.npy',trajectory)
def stamp(m):return m.header.stamp.sec+m.header.stamp.nanosec*1e-9
def xyz(m):
    f={f.name:f.offset for f in m.fields};dt=np.dtype({'names':['x','y','z'],'formats':['<f4']*3,'offsets':[f[k] for k in ['x','y','z']],'itemsize':m.point_step})
    a=np.ndarray((m.height,m.width),dtype=dt,buffer=m.data,strides=(m.row_step,m.point_step))
    return np.column_stack([a[k].ravel() for k in ['x','y','z']])
rd=rosbag2_py.SequentialReader();rd.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));rd.set_filter(rosbag2_py.StorageFilter(topics=['/registered_scan','/state_estimation_at_scan','/local_path']))
poses={};pending={};surface=set();free=set();ground={};snapshots=[];last_ray=-1e9;next_frame=0;paths=[]
def process(m):
    global last_ray,next_frame
    s=stamp(m);elapsed=s-start
    if not -0.5<=elapsed<=601 or s-last_ray<1:return
    if s not in poses:return
    last_ray=s;origin=poses[s];points=xyz(m);points=points[np.isfinite(points).all(1)]
    # Display observed vertical structures; no completion of missing surfaces.
    floor=float(origin[2]-.75)
    near=points[np.linalg.norm(points[:,:2]-origin[:2],axis=1)<=12.]
    low=near[np.abs(near[:,2]-floor)<=.35]
    for p in low:
        k=tuple(np.floor(p[:2]/.5).astype(int));ground[k]=min(ground.get(k,float('inf')),float(p[2]))
    walls=near[(near[:,2]>=floor+.15)&(near[:,2]<=floor+2.5)]
    surface.update(map(tuple,np.unique(np.floor(walls/.20).astype(np.int32),axis=0)))
    if len(points)>1024:points=points[np.linspace(0,len(points)-1,1024).astype(int)]
    delta=points-origin;length=np.linalg.norm(delta,axis=1);good=length>.3;delta=delta[good];length=length[good]
    direction=delta/length[:,None];steps=np.arange(.25,12.,.25)
    rays=origin+direction[:,None,:]*steps[None,:,None];mask=steps[None,:]<(length[:,None]-.25)
    cells=np.unique(np.floor(rays[mask]/.5).astype(np.int32),axis=0)
    cells=cells[(cells[:,2]*.5+.25>=floor+.05)&(cells[:,2]*.5+.25<=floor+.85)];free.update(map(tuple,cells[:,:2]))
    if elapsed>=next_frame:
        idx=len(snapshots);np.savez_compressed(root/'frames'/f'{idx:04d}.npz',surface=(np.array(list(surface),np.float32)+.5)*.20,free=np.array([[float(k[0])*.5+.25,float(k[1])*.5+.25,ground[k]+.02] for k in free if k in ground],np.float32).reshape(-1,3))
        snapshots.append({'elapsed_s':max(0,elapsed),'file':f'frames/{idx:04d}.npz'});next_frame=elapsed+2
while rd.has_next():
    topic,data,t=rd.read_next()
    if topic=='/local_path':
        from nav_msgs.msg import Path as RosPath
        m=deserialize_message(data,RosPath);p=[[v.pose.position.x,v.pose.position.y,v.pose.position.z] for v in m.poses]
        paths.append({'elapsed_s':stamp(m)-start,'points':p})
    elif topic=='/state_estimation_at_scan':
        m=deserialize_message(data,Odometry);s=stamp(m);p=m.pose.pose.position;poses[s]=np.array([p.x,p.y,p.z])
        if s in pending:process(pending.pop(s))
        if len(poses)>100:poses.pop(next(iter(poses)))
    else:
        m=deserialize_message(data,PointCloud2);s=stamp(m)
        if s in poses:process(m)
        else:pending[s]=m
        if len(pending)>30:pending.pop(next(iter(pending)))
(root/'snapshots.json').write_text(json.dumps(snapshots,indent=2));(root/'paths.json').write_text(json.dumps(paths))
(root/'PROVENANCE.json').write_text(json.dumps({'source_bag':str(run/'bag'),'source_start_clock':start,'duration_s':600,'playback_rate':4,'surface_display':'Actual scans within 12m of sensor; 0.20m display voxels, +0.15 to +2.5m relative to scan-pose ground reference (sensor_z-0.75m).','green_display':'Near-ground ray-free XY projection, shown only where a low measured return exists. Tile display height uses the lowest measured return near that scan ground reference; no terrain is invented in unmeasured cells. Observation visualization only, not traversability or terrain truth.','vehicle':'Configured 0.6x0.6m footprint at recorded odometry; no physical contact simulation.','snapshots':len(snapshots)},indent=2))
print('Prepared',len(snapshots),'observed snapshots;',len(surface),'surface voxels;',len(free),'projected free cells')

# Keep the recorded gate/recovery status visible in the video.
status=[];last=None;gate='WAITING';recovery='';invalid_goal=False
for line in (run/'observations/events.jsonl').open():
    e=json.loads(line);d=e['data'];t=e['time']-start
    if t<0:continue
    if e['kind']=='/ht_minimal/command_audit' and 'reason' in d:gate=d['reason']
    if e['kind']=='/ht_minimal/recovery':recovery=d.get('state','') if d.get('active') else ''
    if e['kind']=='waypoint':invalid_goal=not all(isinstance(d.get(k),(float,int)) and np.isfinite(d[k]) for k in ['x','y','z'])
    value='INVALID_WAYPOINT' if invalid_goal else ('RECOVERY: '+recovery if recovery else gate)
    if value!=last:status.append({'elapsed_s':t,'value':value});last=value
(root/'status.json').write_text(json.dumps(status))
