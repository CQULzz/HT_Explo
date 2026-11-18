from pathlib import Path
import numpy as np,json
from scipy.spatial import cKDTree
r=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');a=np.load(r/'regional_geometry.npz');xyz=a['free_xyz'];roi=np.load(r/'native_ROI_all_frames_observations.npy');original=a['omitted'];mask=original&(xyz[:,0]>68)&(xyz[:,0]<78)&(xyz[:,1]>3)&(xyz[:,1]<10);points=xyz[mask];remain=points[cKDTree(roi).query(points)[0]>.75];np.save(r/'R1_unmatched_all_frames.npy',remain);print('Remaining ROI1',len(remain),remain.tolist())
