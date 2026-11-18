from pathlib import Path
import json,numpy as np
from scipy.ndimage import distance_transform_edt,uniform_filter,maximum_filter
root=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');p=root/'validation/campus_repeat_1200s_20261118';a=np.load(p/'data/ht_map_last.npz');meta=json.loads((p/'data/MAP_SNAPSHOTS.json').read_text())['snapshots'][-1];res=meta['resolution_m']
known=(a['ht_measured_valid']>=.5)|(a['ht_obstacle']>=.5);near=distance_transform_edt(~known)*res<=.25;physical=a['ht_observation_valid']>=.5;uncertain=near&~physical;ratio=uniform_filter(near.astype(np.float32),51,mode='constant');veto=maximum_filter(uncertain,size=51)
for r,c in [(123,124),(112,119),(106,116),(100,114)]:
 bad=np.argwhere(uncertain[r-25:r+26,c-25:c+26])+[r-25,c-25]; print('query',r,c,'ratio',float(ratio[r,c]),'veto',bool(veto[r,c]),'bad',bad.tolist())
print('near physical diff',int(uncertain.sum()))
np.savez_compressed('/mnt/d/HT-Window-Recovery-20261118/context_probe.npz',known=known,near=near,uncertain=uncertain,ratio=ratio,valid=a['ht_valid'],physical=physical)
