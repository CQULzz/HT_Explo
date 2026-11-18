import numpy as np,json
from pathlib import Path
from scipy.ndimage import distance_transform_edt,label,binary_dilation
r=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/campus_repeat_1200s_20261118');a=np.load(r/'data/ht_map_last.npz');m=json.loads((r/'data/MAP_SNAPSHOTS.json').read_text())['snapshots'][-1];res=m['resolution_m'];cx,cy,_=m['center_xyz'];rr,cc=np.indices(a['ht_valid'].shape);xx=cx+(len(rr)/2-rr-.5)*res;yy=cy+(len(rr)/2-cc-.5)*res
physical=a['ht_observation_valid']>=.5;distance=distance_transform_edt(physical)*res;valid=(a['ht_valid']>=.5)&(a['ht_obstacle']<.5)&(distance>=.5818)&(np.max([a['ht_dir_'+str(i)] for i in range(8)],axis=0)>=.5)
l,n=label(valid,np.ones((3,3)));k=l[123,124];d=np.hypot(xx-.1725,yy);connected=l==k
print('connected_cells',connected.sum(),'best_xy',xx[connected][d[connected].argmin()],yy[connected][d[connected].argmin()],'best_goal_distance',d[connected].min(),'start_goal_distance',np.hypot(-4.210022-.1725,-1.912616))
np.savez_compressed('/mnt/d/HT-Window-Recovery-20261118/connectivity_probe.npz',x=xx,y=yy,valid=valid,connected=connected)
