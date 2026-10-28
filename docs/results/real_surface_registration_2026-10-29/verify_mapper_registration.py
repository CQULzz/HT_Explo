from pathlib import Path
import json,numpy as np,cupy as cp
from scipy.spatial.transform import Rotation
from elevation_mapping_cupy import ElevationMap,Parameter
O=Path(__file__).parent;C=Path('/home/lzz/my test/ht_cupy_gpu_ws_20261028/src/elevation_mapping_cupy_2204/elevation_mapping_cupy');plugin=O/'regression_plugins.yaml';plugin.write_text('min_filter:\n  enable: false\n')
def create(enabled):
 p=Parameter(use_chainer=False,resolution=.04,map_length=4.,weight_file=str(C/'config/core/weights.dat'),plugin_config_file=str(plugin),enable_drift_compensation=False,enable_overlap_clearance=False,enable_visibility_cleanup=False,enable_deterministic_fusion=True,enable_surface_registration=enabled);p.subscriber_cfg={'scan':{'data_type':'pointcloud'}};p.update();return ElevationMap(p)
axis=np.arange(-1.8,1.801,.04)+.013;x,y=np.meshgrid(axis,axis,indexing='ij');ground=np.c_[x.ravel(),y.ravel(),np.full(x.size,-.75)].astype(np.float32);R=Rotation.from_euler('xy',[.5,-.4],degrees=True).as_matrix();t=np.array([0.,0.,.025]);rows=[]
for height in [0.,.02,.05,.10,.20,.50]:
 a=create(False);b=create(True)
 for scan in range(4):
  for m in [a,b]:m.input_pointcloud(ground.copy(),['x','y','z'],np.eye(3),np.zeros(3),0.,0.,observation_stamp=100.+scan*.1)
 pts=ground.copy();feature=((pts[:,0]>.65)&(pts[:,0]<.95)&(abs(pts[:,1])<.2));pts[feature,2]+=height
 a.input_pointcloud(pts.copy(),['x','y','z'],np.eye(3),np.zeros(3),0.,0.,observation_stamp=101.)
 b.input_pointcloud(pts.copy(),['x','y','z'],R.copy(),t.copy(),0.,0.,observation_stamp=101.)
 ga=cp.asnumpy(a.elevation_map);gb=cp.asnumpy(b.elevation_map);use=(ga[2]>.5)&(gb[2]>.5);error=gb[0,use]-ga[0,use]
 row={'feature_height_m':height,'status':b.last_surface_registration['status'],'median_abs_height_error_vs_perfect_pose_m':float(np.median(abs(error))),'p99_abs_height_error_vs_perfect_pose_m':float(np.quantile(abs(error),.99)),'actual_max_observed_height_above_floor_m':float(np.max(gb[0,use]+.75)),'perfect_pose_max_observed_height_above_floor_m':float(np.max(ga[0,use]+.75)),'observation_stamp_not_future':bool(cp.nanmax(b.observation_stamps)<=101.)};rows.append(row);print(row,flush=True)
 assert row['status']=='APPLIED' and row['p99_abs_height_error_vs_perfect_pose_m']<.003 and row['observation_stamp_not_future']
 assert abs(row['actual_max_observed_height_above_floor_m']-row['perfect_pose_max_observed_height_above_floor_m'])<.003
(O/'MAPPER_REGISTRATION_REGRESSION.json').write_text(json.dumps({'scope':'Synthetic rigid-pose recovery in actual CUDA mapper; features compare to the same Gaussian fusion with perfect pose, not physical obstacle traversability labels.','cases':rows,'passed':True},indent=2)+'\n')
