from pathlib import Path
import json,csv
import numpy as np
import rosbag2_py
from sensor_msgs.msg import PointCloud2
from rclpy.serialization import deserialize_message
from scipy.spatial import cKDTree
root=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');run=Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02');start=json.loads((run/'observations/START.json').read_text())['clock'];end=float(list(csv.DictReader((run/'observations/metrics.csv').open()))[-1]['time']);rd=rosbag2_py.SequentialReader();rd.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));rd.set_filter(rosbag2_py.StorageFilter(topics=['/registered_scan']));observed=set();regions=set();last=-1e9;frames=0;sampled=0
while rd.has_next():
 topic,data,t=rd.read_next();m=deserialize_message(data,PointCloud2);stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
 if not start<=stamp<=end:continue
 f={p.name:p.offset for p in m.fields};dt=np.dtype({'names':['x','y','z'],'formats':['<f4']*3,'offsets':[f[k] for k in ['x','y','z']],'itemsize':m.point_step});a=np.ndarray((m.height,m.width),dtype=dt,buffer=m.data,strides=(m.row_step,m.point_step));pts=np.column_stack([a[k].ravel() for k in ['x','y','z']]);pts=pts[np.isfinite(pts).all(1)];frames+=1
 roi=((pts[:,0]>68)&(pts[:,0]<78)&(pts[:,1]>3)&(pts[:,1]<10))|((pts[:,0]>113)&(pts[:,0]<119)&(pts[:,1]>115)&(pts[:,1]<123));regions.update(map(tuple,np.unique(np.floor(pts[roi]/.5).astype(np.int32),axis=0)))
 if stamp-last>=1:
  observed.update(map(tuple,np.unique(np.floor(pts/.5).astype(np.int32),axis=0)));last=stamp;sampled+=1
obs=(np.array(list(observed),np.float32)+.5)*.5;roi=(np.array(list(regions),np.float32).reshape(-1,3)+.5)*.5;np.save(root/'native_full_range_sampled_observations.npy',obs);np.save(root/'native_ROI_all_frames_observations.npy',roi)
geo=np.load(root/'regional_geometry.npz');xyz=geo['free_xyz'];reachable=geo['reachable'];match=cKDTree(obs).query(xyz)[0]<=.75;np.save(root/'native_full_range_proxy_match.npy',match)
comp=np.load('/home/lzz/tare_native_campus_repeat_20261118/analysis/COVERAGE_REFERENCE_COMPARISON.npz');ref=comp['reference_voxel_centers'];summary={'frames':frames,'sampled_frames':sampled,'full_range_observed_voxels':len(obs),'reference_surface_matched_fraction_full_range_sampled':float((cKDTree(obs).query(ref)[0]<=.75).mean()),'route_seeded_proxy_unmatched_full_range_sampled':int((reachable&~match).sum()),'regions_all_frames_raw_matched':[]}
for p in json.loads((root/'REACHABILITY_PROXY.json').read_text())['largest_regions']:
 lo,hi=np.array(p['bounds_xyz']);sel=reachable&~geo['matched']&np.all(xyz>=lo-.001,axis=1)&np.all(xyz<=hi+.001,axis=1);dist=cKDTree(roi).query(xyz[sel])[0];summary['regions_all_frames_raw_matched'].append({'region':p['region'],'original_unmatched_proxy_cells':int(sel.sum()),'matched_in_all_raw_scans_full_range':int((dist<=.75).sum())})
(root/'FULL_RANGE_OBSERVATION_CHECK.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2))
