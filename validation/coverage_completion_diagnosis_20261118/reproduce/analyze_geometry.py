from pathlib import Path
import json,csv
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components,dijkstra
from scipy.spatial import cKDTree
from scipy.ndimage import label
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
root=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');out=Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118');base=Path('/home/lzz/tare_native_campus_repeat_20261118/analysis');z=np.load(base/'REFERENCE_GROUND_PROXY.npz');floor=z['floor'];free=z['free'];lo=z['origin_index'];res=.5
ij=np.argwhere(free);flat=np.ravel_multi_index(ij.T,free.shape);index=np.full(free.shape,-1,np.int32);index[free]=np.arange(len(ij));edges=[]
for axis in [0,1]:
 a=ij.copy();a[:,axis]+=1;valid=(a[:,axis]<free.shape[axis]);src=np.flatnonzero(valid);target=index[tuple(a[valid].T)];good=target>=0;src=src[good];target=target[good];good=np.abs(floor[tuple(ij[src].T)]-floor[tuple(ij[target].T)])<=.2;edges.append((src[good],target[good]))
src=np.concatenate([e[0] for e in edges]);dst=np.concatenate([e[1] for e in edges]);graph=coo_matrix((np.full(len(src)*2,.5), (np.r_[src,dst],np.r_[dst,src])),shape=(len(ij),len(ij))).tocsr();n,component=connected_components(graph)
xyz=np.column_stack([(ij+lo+.5)*res,floor[free]])
run2=Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02');r1=Path('/home/lzz/tare_native_campus_20261118/runs/native_campus_01');ht=Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01')
def trajectory(run):
 rows=list(csv.DictReader((run/'observations/metrics.csv').open()));return np.array([[float(r[k]) for k in ['x','y','z']] for r in rows])
traj=trajectory(run2);tree=cKDTree(xyz[:,:2]);ds,near=tree.query(traj[:,:2],k=8);valid=(ds<=.75)&(abs(xyz[near,2]-(traj[:,2,None]-.75))<=.35);seed=np.unique(near[valid]);seedcomponents=np.unique(component[seed]);reachable=np.isin(component,seedcomponents)
comp=np.load(base/'COVERAGE_REFERENCE_COMPARISON.npz');obs=comp['observed_voxel_centers'];matched=cKDTree(obs).query(xyz,workers=2)[0]<=.75;route_distance=cKDTree(traj[:,:2]).query(xyz[:,:2])[0];omitted=reachable&~matched;far=omitted&(route_distance>20)
grid=np.zeros(free.shape,bool);grid[tuple(ij[omitted].T)]=True;labels,num=label(grid);patch=[]
for l in range(1,num+1):
 loc=np.argwhere(labels==l)
 if len(loc)<20:continue
 ids=index[tuple(loc.T)];center=xyz[ids].mean(0);candidate=ids[np.argmin(np.linalg.norm(xyz[ids]-center,axis=1))];patch.append({'cells':len(ids),'area_m2':len(ids)*.25,'center_xyz':xyz[candidate].tolist(),'bounds_xyz':[xyz[ids].min(0).tolist(),xyz[ids].max(0).tolist()],'max_distance_to_actual_route_m':float(route_distance[ids].max()),'representative_index':int(candidate)})
patch.sort(key=lambda p:p['area_m2'],reverse=True)
paths=[]
for k,p in enumerate(patch[:15]):
 p['region']='R'+str(k+1);target=p['representative_index'];dd,pred=dijkstra(graph,indices=target,return_predecessors=True);source=seed[np.argmin(dd[seed])];p['shortest_proxy_path_from_recorded_route_m']=float(dd[source]);seq=[int(source)]
 while seq[-1]!=target:
  nxt=int(pred[seq[-1]]);assert nxt>=0;seq.append(nxt)
 paths.append(xyz[seq]);p['path_vertices']=len(seq)
 np.save(root/(p['region']+'_proxy_path.npy'),xyz[seq])
# Direct prior driving evidence: compare measured wheel-ground proxy centers, not virtual graph paths.
t1=trajectory(r1);ground1=t1.copy();ground1[:,2]-=.75;dist1=cKDTree(obs).query(ground1)[0];actual_ground_unmatched=ground1[dist1>.75]
result={'method':'Unchanged conservative footprint mask and height steps <=0.2m/0.5m; components seeded near physically recorded native02 driving, floor height matched. Virtual paths are static point-cloud evidence, not physical/dynamic reachability certification.','free_cells':len(ij),'all_components':int(n),'seeded_components':len(seedcomponents),'route_seeded_connected_cells':int(reachable.sum()),'matched_cells':int((reachable&matched).sum()),'unmatched_cells':int(omitted.sum()),'unmatched_farther20m_from_route':int(far.sum()),'largest_regions':patch[:15],'prior_native01_ground_trajectory_samples_unmatched_by_native02_scans':len(actual_ground_unmatched),'missing_does_not_mean_unreachable':True}
(root/'REACHABILITY_PROXY.json').write_text(json.dumps(result,indent=2));(out/'REACHABILITY_PROXY.json').write_text(json.dumps(result,indent=2));np.savez_compressed(root/'regional_geometry.npz',free_xyz=xyz,reachable=reachable,matched=matched,component=component,seed=seed,omitted=omitted,prior_actual_unmatched_xyz=actual_ground_unmatched)
ref=comp['reference_voxel_centers'];fig,ax=plt.subplots(figsize=(11,10));ax.scatter(ref[::5,0],ref[::5,1],s=.15,c='#d1d5db',label='Reference surfaces');ax.scatter(xyz[reachable&matched,0],xyz[reachable&matched,1],s=.2,c='#0f766e',label='Route-seeded proxy, observed');ax.scatter(xyz[omitted,0],xyz[omitted,1],s=1,c='#ef4444',label='Proxy reachable, unmatched');ax.plot(traj[:,0],traj[:,1],c='#2563eb',lw=.65,label='Native02 actual route')
for p,path in zip(patch[:15],paths):
 c=p['center_xyz'];ax.text(c[0],c[1],p['region'],fontsize=9,bbox={'facecolor':'white','alpha':.8,'pad':1});ax.plot(path[:,0],path[:,1],c='#f59e0b',lw=1)
ax.set(aspect='equal',xlabel='World X (m)',ylabel='World Y (m)',title='Unobserved regions: static reachability evidence, not ground truth');ax.legend(fontsize=8);ax.grid(alpha=.2);fig.tight_layout();fig.savefig(out/'regional_geometry.png',dpi=160);print(json.dumps(result,indent=2))
