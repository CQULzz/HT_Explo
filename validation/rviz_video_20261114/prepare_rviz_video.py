from pathlib import Path
import json,csv,time
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
root=Path('/mnt/d/HT-Execution-300s/rviz_video_20261114');root.mkdir(exist_ok=True);(root/'frames').mkdir(exist_ok=True)
run=Path('/home/lzz/ht_600s_20261114/runs/execution_600s_01')
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
poses={};pending={};surface=set();free=set();snapshots=[];last_ray=-1e9;next_frame=0;paths=[]
def process(m):
    global last_ray,next_frame
    s=stamp(m);elapsed=s-start
    if not -0.5<=elapsed<=601 or s-last_ray<1:return
    if s not in poses:return
    last_ray=s;origin=poses[s];points=xyz(m);points=points[np.isfinite(points).all(1)]
    # Display observed vertical structures; no completion of missing surfaces.
    walls=points[(points[:,2]>=.15)&(points[:,2]<=2.5)]
    surface.update(map(tuple,np.unique(np.floor(walls/.20).astype(np.int32),axis=0)))
    if len(points)>1024:points=points[np.linspace(0,len(points)-1,1024).astype(int)]
    delta=points-origin;length=np.linalg.norm(delta,axis=1);good=length>.3;delta=delta[good];length=length[good]
    direction=delta/length[:,None];steps=np.arange(.25,12.,.25)
    rays=origin+direction[:,None,:]*steps[None,:,None];mask=steps[None,:]<(length[:,None]-.25)
    cells=np.unique(np.floor(rays[mask]/.5).astype(np.int32),axis=0)
    cells=cells[cells[:,2]==0];free.update(map(tuple,cells[:,:2]))
    if elapsed>=next_frame:
        idx=len(snapshots);np.savez_compressed(root/'frames'/f'{idx:04d}.npz',surface=(np.array(list(surface),np.float32)+.5)*.20,free=(np.array(list(free),np.float32)+.5)*.5)
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
(root/'PROVENANCE.json').write_text(json.dumps({'source_bag':str(run/'bag'),'source_start_clock':start,'duration_s':600,'playback_rate':4,'surface_display':'Actual registered scans; 0.20m voxel sampling, z in [0.15,2.5]m.','green_display':'Projection of observed ray free voxels with z index 0 (0..0.5m), 0.5m grid, 1Hz/1024 endpoints/12m. This is observation only, not traversability or ground truth.','vehicle':'Configured 0.6x0.6m footprint at recorded odometry; no physical contact simulation.','snapshots':len(snapshots)},indent=2))
print('Prepared',len(snapshots),'observed snapshots;',len(surface),'surface voxels;',len(free),'projected free cells')
