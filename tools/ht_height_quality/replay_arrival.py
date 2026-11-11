"""Isolated production CUDA fusion on archived scans and one seeded source cell.

No ROS node, simulator, driver or threshold changes. The seed is an archived
raw map cell, not a replay of the complete mapper history/scheduler.
"""
from pathlib import Path
from types import SimpleNamespace
import json,math,yaml
import numpy as np,cupy as cp,rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from nav_msgs.msg import Odometry
from scipy.spatial.transform import Rotation
from elevation_mapping_cupy.deterministic_fusion import DeterministicFusion

ROOT=Path('/home/lzz/ht_quality_20261111');RUN=Path('/home/lzz/ht_recovery_20261111/runs/cmu_recovery_300s_02')
start=json.loads((RUN/'observations/START.json').read_text())['clock']
cfg=yaml.safe_load(Path('/home/lzz/ht_quality_20261111/config/trial_core.yaml').read_text())
cfg['drift_compensation_variance_inlier']=cfg['drift_compensation_variance_inler']
cfg['cell_n']=293;p=SimpleNamespace(**cfg);fusion=DeterministicFusion(p)
reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(RUN/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
reader.set_filter(rosbag2_py.StorageFilter(topics=['/registered_scan','/state_estimation_at_scan','/state_estimation']))
reader.seek(int((start+263.5)*1e9));clouds=[];poses=[]
while reader.has_next():
    topic,data,received=reader.read_next()
    if received/1e9>start+264.95:break
    msg=deserialize_message(data,PointCloud2 if topic=='/registered_scan' else Odometry)
    stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
    if topic=='/registered_scan':
        if 263.8<stamp-start<264.9:
            a=point_cloud2.read_points(msg,field_names=('x','y','z'),skip_nans=True)
            clouds.append((stamp,np.stack([a[k] for k in ('x','y','z')],axis=-1)))
    else:poses.append((stamp,msg,topic))

cell_center=np.asarray([368*p.resolution,1188*p.resolution,0.],np.float32)
width=p.cell_n;m=width*width;i=j=width//2;c=i*width+j
q=cp.asarray([p.resolution,p.sensor_noise_factor,p.mahalanobis_thresh,p.outlier_variance,
              p.min_valid_distance,p.max_height_range,p.ramped_height_range_a,p.ramped_height_range_b,
              p.ramped_height_range_c,p.drift_compensation_variance_inlier,p.traversability_inlier,
              float(p.enable_edge_sharpen),p.wall_num_thresh,p.initial_variance,p.max_ray_length,
              p.cleanup_cos_thresh,p.cleanup_step,p.max_variance],cp.float32)

def seed():
    state=cp.zeros((7,width,width),cp.float32)
    state[1]=p.initial_variance
    state[0,i,j]=.84132981300354;state[1,i,j]=.0006000176072120667
    state[2,i,j]=1;state[3,i,j]=1
    return state

state=seed();observed_v=cp.full((width,width),cp.nan,cp.float32)
observed_v[i,j]=.0006000176072120667
normals=cp.zeros((3,width,width),cp.float32);new=cp.zeros_like(state)
rows=[];density=[]
for nscan,(stamp,world) in enumerate(clouds):
    pose_stamp,pose,topic=min(poses,key=lambda a:abs(a[0]-stamp))
    pos=pose.pose.pose.position;rot=pose.pose.pose.orientation
    sensor=np.asarray([pos.x,pos.y,pos.z],np.float32)
    R=Rotation.from_quat([rot.x,rot.y,rot.z,rot.w]).as_matrix().astype(np.float32)
    local=((world-sensor)@R).astype(np.float32)
    points=cp.asarray(local);rotation=cp.asarray(R);translation=cp.asarray(sensor-cell_center)
    # One 5Hz time-variance tick per approximately 0.2s scan, explicitly stated.
    state[1]+=p.time_variance*state[2]
    prior_h=float(state[0,i,j]);prior_v=float(state[1,i,j])
    n=len(local);xyz=cp.empty((n,3),cp.float32);noise=cp.empty(n,cp.float32)
    cells=cp.empty(n,cp.int32);flags=cp.empty(n,cp.int32);errors=cp.empty(n,cp.float32)
    fusion._launch('prepare',n,(points,rotation,translation,q,state,np.int32(n),np.int32(width),xyz,noise,cells,flags,errors))
    use=(cells==c)&((flags&2)!=0);zs=xyz[use,2]
    outliers=cp.square(zs-prior_h)>p.mahalanobis_thresh**2*(prior_v+noise[use])
    if nscan==1:
        for copies in [1,2,4]:
            s=state.copy();new_d=cp.zeros_like(s)
            fusion.fuse(s,normals,cp.tile(cp.asarray(local),(copies,1)),rotation,translation,new_d,
                        observation_variance=observed_v)
            density.append({'copies':copies,'accepted':float(new_d[2,i,j]),
                            'height':float(s[0,i,j]),'variance':float(s[1,i,j])})
    fusion.fuse(state,normals,points,rotation,translation,new,observation_variance=observed_v)
    observed_v=cp.where(new[2]>0,state[1],observed_v)
    row={'scan_elapsed':stamp-start,'pose_topic':topic,'pose_stamp_delta_s':pose_stamp-stamp,
         'sensor_position':sensor.astype(float).tolist(),'prior_height':prior_h,'prior_variance':prior_v,
         'valid_points_in_cell':int(use.sum()),'classified_outliers':int(outliers.sum()),
         'valid_return_min_z':float(zs.min()) if zs.size else None,
         'valid_return_max_z':float(zs.max()) if zs.size else None,
         'accepted':float(new[2,i,j]),'output_height':float(state[0,i,j]),
         'output_variance':float(state[1,i,j]),'observation_variance':float(observed_v[i,j])}
    rows.append(row);print(json.dumps(row),flush=True)
result={'scope':'Production CUDA kernel, original scans, nearest recorded scan-time odometry, one cell seeded from the raw263.719358 map; exactly one configured 0.0001 time-variance tick before each scan. Not full mapper/scheduler/history replay or vehicle test.',
        'seed_elapsed':263.7193582057953,'seed_height':.84132981300354,
        'seed_variance':.0006000176072120667,'rows':rows,'density_repetition':density}
with (ROOT/'analysis/ARRIVAL_FUSION_PROBE_20261111.json').open('x') as f:json.dump(result,f,indent=2)
print('DENSITY',json.dumps(density))
