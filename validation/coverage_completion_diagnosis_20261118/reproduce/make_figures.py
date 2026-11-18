from pathlib import Path
import numpy as np,csv,json
from scipy.spatial import cKDTree
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
r=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');out=Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118');old=np.load('/home/lzz/tare_native_campus_repeat_20261118/analysis/COVERAGE_REFERENCE_COMPARISON.npz');ref=old['reference_voxel_centers'];native=np.load(r/'native_full_range_sampled_observations.npy');ht=np.load(r/'ht_full_range_sampled_observations.npy');remaining=np.load(r/'R1_unmatched_all_frames.npy');path=np.load(r/'R1_proxy_path.npy')
fig,axes=plt.subplots(1,3,figsize=(18,6))
runs=[Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02')]*2+[Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01')]
for ax,obs,title,run in zip(axes,[old['observed_voxel_centers'],native,ht],['Native: <=15m subset, 44.81%','Native: full raw range, 93.87%','HT: full raw range, 27.20%'],runs):
 match=cKDTree(obs).query(ref)[0]<=.75;ax.scatter(ref[~match,0][::3],ref[~match,1][::3],s=.3,c='#cbd5e1',label='Unmatched reference surface');ax.scatter(ref[match,0][::3],ref[match,1][::3],s=.3,c='#0284c7',label='Matched measured returns');rows=list(csv.DictReader((run/'observations/metrics.csv').open()));p=np.array([[float(d[k]) for k in ['x','y']] for d in rows]);ax.plot(p[:,0],p[:,1],lw=.7,c='#ef4444',label='Actual trajectory');ax.set(title=title,aspect='equal',xlabel='World X (m)',ylabel='World Y (m)',xlim=(-215,135),ylim=(-160,165));ax.grid(alpha=.15)
axes[0].legend(fontsize=7,markerscale=3);fig.suptitle('Same 1Hz observation sampling / 0.75m reference match. Surface matching is not certified traversability.',fontsize=11);fig.tight_layout();fig.savefig(out/'corrected_observation_comparison.png',dpi=150);plt.close(fig)
fig,ax=plt.subplots(figsize=(9,7));sel=(native[:,0]>54)&(native[:,0]<82)&(native[:,1]>-3)&(native[:,1]<13);ax.scatter(native[sel,0],native[sel,1],s=1,c='#0284c7',alpha=.5,label='Full-range sampled returns, XY projection');ax.scatter(remaining[:,0],remaining[:,1],s=25,c='#ef4444',label='18 ground cells unmatched in all raw frames');ax.plot(path[:,0],path[:,1],c='#16a34a',lw=2,label='15m static mesh-checked path');ax.scatter(path[0,0],path[0,1],s=50,c='#16a34a',marker='s');ax.set(aspect='equal',title='R1: residual ground hole with static geometric access',xlabel='World X (m)',ylabel='World Y (m)',xlim=(55,80),ylim=(-1,12));ax.grid(alpha=.2);ax.legend(fontsize=8);fig.tight_layout();fig.savefig(out/'R1_mesh_path.png',dpi=160)
print('Corrected figures saved')
