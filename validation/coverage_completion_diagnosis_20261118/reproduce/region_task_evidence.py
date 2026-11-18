from pathlib import Path
import numpy as np,json
from scipy.spatial import cKDTree
r=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');points=np.load(r/'R1_unmatched_all_frames.npy');results={}
for tag in ['native','ht']:
 arrays=np.load(r/(tag+'_task_cloud_union.npz'));summary={}
 for topic in arrays.files:
  pts=arrays[topic];d=cKDTree(pts).query(points)[0];near=pts[np.linalg.norm(pts[:,:2]-np.array([74.5,7]),axis=1)<5.];summary[topic]={'nearest_3d_distance_to_remaining_R1_m':float(d.min()),'union_voxels_within_xy5m_of_R1':len(near),'points_xyz':near.tolist() if len(near)<100 else near[::max(1,len(near)//80)].tolist()}
 results[tag]=summary
(r/'REGION_TASK_EVIDENCE.json').write_text(json.dumps(results,indent=2));print(json.dumps({tag:{topic:{k:v for k,v in val.items() if k!='points_xyz'} for topic,val in value.items()} for tag,value in results.items()},indent=2))
# Keep full matrices in local metadata only; concise delivery index omits thousands of node transforms.
p=r/'MESH_INDEX.json';j=json.loads(p.read_text());j.pop('transforms',None);(r/'MESH_INDEX_COMPACT.json').write_text(json.dumps(j,indent=2))
p=Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118/verify_mesh_path.py');s=p.read_text(encoding='utf-8-sig').replace('[-.3,0,.3]','[-.425,0,.425]').replace('np.array([.3,.3,.425])','np.array([.425,.425,.425])').replace("'footprint_xy_m':[.6,.6]","'footprint_xy_m':[.85,.85]").replace("'R1_MESH_PATH_VERIFICATION.json'","'R1_TURN_ENVELOPE_VERIFICATION.json'");Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118/verify_turn_envelope.py').write_text(s)
