from pathlib import Path
import csv,json,numpy as np
r=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');data={}
for tag,run in [('ht',Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01')),('native',Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02'))]:
 rows=list(csv.DictReader((run/'observations/metrics.csv').open()));a=np.array([[float(x[k]) for k in ['elapsed_s','x','y','distance_m']] for x in rows]);d=np.hypot(a[:,1]-74.5,a[:,2]-7);history=json.loads((r/(tag+'_task_cells_history.json')).read_text());key=lambda topic:topic+':7,0';data[tag]={'trajectory_bounds_xy':[a[:,1:3].min(0).tolist(),a[:,1:3].max(0).tolist()],'closest_to_R1':{'elapsed_s':float(a[d.argmin(),0]),'distance_m':float(d.min()),'xy':a[d.argmin(),1:3].tolist()},'nominal_xy_bucket_near_R1':{topic:history.get(key(topic)) for topic in ['/filtered_frontier_cloud','/uncovered_cloud']}}
 arrays=np.load(r/(tag+'_task_cloud_union.npz'))
 for topic in arrays.files:
  pts=arrays[topic];sel=np.linalg.norm(pts[:,:2]-np.array([74.5,7]),axis=1)<5.;p=pts[sel];data[tag][topic+'_region_z_range']=None if not len(p) else [float(p[:,2].min()),float(p[:,2].max())]
print(json.dumps(data,indent=2));(r/'REGION_HISTORY.json').write_text(json.dumps(data,indent=2))
