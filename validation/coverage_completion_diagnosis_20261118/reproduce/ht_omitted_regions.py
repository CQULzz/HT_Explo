from pathlib import Path
import csv,json,numpy as np
from scipy.spatial import cKDTree
r=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');run=Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02');rows=list(csv.DictReader((run/'observations/metrics.csv').open()));a=np.array([[float(d[k]) for k in ['x','y','z']] for d in rows]);a[:,2]-=.75;ht=np.load(r/'ht_full_range_sampled_observations.npy');dist=cKDTree(ht).query(a)[0];native=np.load(r/'native_full_range_sampled_observations.npy');d_native=cKDTree(native).query(a)[0];missing=(dist>.75)&(d_native<=.75);buckets=np.floor(a[:,:2]/40).astype(int);regions=[]
for key in np.unique(buckets[missing],axis=0):
 sel=missing&np.all(buckets==key,axis=1);p=a[sel]
 if sel.sum()<20:continue
 length=np.linalg.norm(np.diff(a[:,:2],axis=0),axis=1);contribution=float(length[sel[:-1]&sel[1:]].sum());center=p.mean(0);q=p[np.argmin(np.linalg.norm(p-center,axis=1))];regions.append({'bucket_xy_m':[(key*40).tolist(),((key+1)*40).tolist()],'representative_actual_ground_xyz':q.tolist(),'actual_native_ground_samples':int(sel.sum()),'native_driving_length_in_bucket_unmatched_by_HT_m':contribution,'note':'Actual native 0.6m vehicle driving proves native reachability along trace; does not certify Scout 0.93x0.70m reachability or all area in bucket.'})
regions.sort(key=lambda p:p['native_driving_length_in_bucket_unmatched_by_HT_m'],reverse=True);(r/'HT_OMITTED_NATIVE_DRIVEN_REGIONS.json').write_text(json.dumps(regions,indent=2));print(json.dumps(regions[:4],indent=2))
