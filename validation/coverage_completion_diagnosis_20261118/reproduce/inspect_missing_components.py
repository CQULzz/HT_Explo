from pathlib import Path
import numpy as np,json
from scipy.spatial import cKDTree
r=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');a=np.load(r/'regional_geometry.npz');pts=a['free_xyz'];com=a['component'];reach=a['reachable'];matched=a['matched'];tree=cKDTree(pts[reach,:2]);rows=[]
for i in np.unique(com[~reach]):
 p=pts[com==i]
 if len(p)<50:continue
 dist,idx=tree.query(p[:,:2]);j=np.argmin(dist);p2=pts[reach][idx[j]];rows.append({'cells':len(p),'bounds_xyz':[p.min(0).tolist(),p.max(0).tolist()],'unobserved_cells':int((~matched[com==i]).sum()),'nearest_route_connected_gap_xy_m':float(dist[j]),'gap_z_m':float(p[j,2]-p2[2]),'gap_endpoints_xyz':[p[j].tolist(),p2.tolist()]})
rows.sort(key=lambda e:e['unobserved_cells'],reverse=True);(r/'UNSEEDED_COMPONENTS.json').write_text(json.dumps(rows,indent=2));print(json.dumps(rows[:7],indent=2))
print('meshes',[(p.name,p.stat().st_size) for p in Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus/meshes').rglob('*') if p.is_file()])
