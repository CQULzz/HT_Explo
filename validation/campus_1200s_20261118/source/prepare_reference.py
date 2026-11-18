from pathlib import Path
import json,hashlib
import numpy as np
p=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus/preview/pointcloud.ply');root=Path('/home/lzz/ht_campus_1200s_20261118/analysis');root.mkdir(exist_ok=True)
with p.open('rb') as f:
 header=[]
 while True:
  line=f.readline();header.append(line.decode().rstrip())
  if line.strip()==b'end_header':break
 a=np.frombuffer(f.read(),dtype='<f4').reshape(-1,3)
a=a[np.isfinite(a).all(1)];vox=np.unique(np.floor(a/.5).astype(np.int32),axis=0);np.savez_compressed(root/'CAMPUS_REFERENCE_05M.npz',voxels=vox)
meta={'source':str(p),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'points':len(a),'finite_bounds_xyz':[a.min(0).tolist(),a.max(0).tolist()],'voxel_size_m':.5,'reference_voxels':len(vox),'definition':'Independent CMU campus preview surface point cloud, not a ground-truth traversability or reachable-ground mask. Includes non-navigable structures; do not call matched surface fraction full exploration coverage.'};(root/'CAMPUS_REFERENCE.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
