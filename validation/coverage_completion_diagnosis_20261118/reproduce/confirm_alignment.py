from pathlib import Path
import numpy as np,json
from scipy.spatial import cKDTree
r=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');v=np.load(r/'mesh_vertices.npy');obs=np.load('/home/lzz/tare_native_campus_repeat_20261118/analysis/COVERAGE_REFERENCE_COMPARISON.npz')['observed_voxel_centers'][::8];tree=cKDTree(v)
result={}
for shift in [0,1]:
 query=obs.copy();query[:,2]+=shift;dist=tree.query(query)[0];result[str(shift)]={'median_m':float(np.median(dist)),'p90_m':float(np.quantile(dist,.9))}
print(result);(r/'MESH_ALIGNMENT_CHECK.json').write_text(json.dumps({'mesh_extraction_used_declared_pose_z_1':True,'test_add_z_to_observations':result,'interpretation':'Recorded scans agree with mesh Z=0, consistent with saved map state pose0 rather than nominal model pose1; use alignment0 for passive geometry analysis, preserve declared model metadata.'},indent=2))
v[:,2]-=1.;np.save(r/'mesh_vertices_aligned.npy',v)
p=Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118/extract_mesh.py');s=p.read_text(encoding='utf-8-sig').replace("print(json.dumps(summary,indent=2))","print(json.dumps({k:v for k,v in summary.items() if k!='transforms'},indent=2))");p.write_text(s)
