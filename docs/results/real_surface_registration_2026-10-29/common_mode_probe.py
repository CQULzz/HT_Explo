from pathlib import Path
import json,numpy as np
O=Path(__file__).parent;m=np.load(O/'moving_raw_points.npz');s=np.load(O/'stationary_raw_points.npz');xy=m['probe_xy'];coeff=[]
for x,y in xy:
 v=s['world_xyz'];v=v[np.max(abs(v[:,:2]-[x,y]),axis=1)<1.];A=np.c_[v[:,:2],np.ones(len(v))];coeff.append(np.linalg.lstsq(A,v[:,2],rcond=None)[0])
coeff=np.array(coeff);v=m['world_xyz'];region=np.argmin(np.max(abs(v[:,None,:2]-xy),axis=2),axis=1);dist=np.min(np.max(abs(v[:,None,:2]-xy),axis=2),axis=1);error=v[:,2]-(np.sum(v[:,:2]*coeff[region,:2],axis=1)+coeff[region,2]);rows=[]
for scan in np.unique(m['scan']):
 idx=np.flatnonzero((m['scan']==scan)&(dist<1.)&(abs(error)<.12));p=v[idx];e=error[idx];reg=region[idx]
 for hold in range(3):
  train=reg!=hold;test=~train
  if train.sum()<60 or test.sum()<30:continue
  origin=np.mean(p[train,:2],axis=0);A=np.c_[p[:,:2]-origin,np.ones(len(p))];c=np.linalg.lstsq(A[train],e[train],rcond=None)[0]
  for _ in range(5):
   r=e[train]-A[train]@c;w=np.minimum(1.,.01/np.maximum(abs(r),1e-6));c=np.linalg.lstsq(A[train]*w[:,None],e[train]*w,rcond=None)[0]
  rows.append({'scan':int(scan),'heldout_roi':hold,'heldout_n':int(test.sum()),'raw_rms_m':float(np.sqrt(np.mean(e[test]**2))),'corrected_rms_m':float(np.sqrt(np.mean((e[test]-A[test]@c)**2))),'correction_slope':c[:2].tolist(),'correction_origin_m':float(c[2])})
for hold in range(3):
 r=[x for x in rows if x['heldout_roi']==hold];print(hold,'scans',len(r),'raw med',np.median([x['raw_rms_m'] for x in r]),'corrected med',np.median([x['corrected_rms_m'] for x in r]),'RMS all',np.sqrt(np.average([x['raw_rms_m']**2 for x in r],weights=[x['heldout_n'] for x in r])),np.sqrt(np.average([x['corrected_rms_m']**2 for x in r],weights=[x['heldout_n'] for x in r])),flush=True)
(O/'COMMON_MODE_PROBE.json').write_text(json.dumps({'scope':'Two measured ground ROIs fit one per-scan height/tilt correction, third ROI held out; stationary planes are an external measured reference, not used in candidate runtime. No independent terrain ground truth.','rows':rows},indent=2)+'\n')
