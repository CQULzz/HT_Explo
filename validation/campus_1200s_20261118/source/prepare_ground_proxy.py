from pathlib import Path
import numpy as np,json
from scipy.ndimage import binary_erosion
from collections import deque
root=Path('/home/lzz/ht_campus_1200s_20261118/analysis');p=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus/preview/pointcloud.ply')
with p.open('rb') as f:
 while f.readline().strip()!=b'end_header':pass
 xyz=np.frombuffer(f.read(),dtype='<f4').reshape(-1,3)
xyz=xyz[np.isfinite(xyz).all(1)];res=.5;lo=np.floor(xyz[:,:2].min(0)/res).astype(int)-2;hi=np.ceil(xyz[:,:2].max(0)/res).astype(int)+2;shape=tuple((hi-lo+1).tolist());ij=np.floor(xyz[:,:2]/res).astype(int)-lo;flat=np.ravel_multi_index(ij.T,shape);floor=np.full(np.prod(shape),np.inf,np.float32);np.minimum.at(floor,flat,xyz[:,2]);dz=xyz[:,2]-floor[flat]
obstacle=np.zeros(len(floor),bool);obstacle[flat[(dz>.2)&(dz<1.)]]=True
observed=np.isfinite(floor).reshape(shape);obstacle=obstacle.reshape(shape);free=observed&~obstacle
# Conservative footprint support: 3x3 neighborhood, and height continuity of <=0.20m per 0.5m step.
free=binary_erosion(free,structure=np.ones((3,3)),border_value=0);floor=floor.reshape(shape);origin=np.floor(np.array([0.,0.])/res).astype(int)-lo
rr,cc=np.nonzero(free);near=((rr-origin[0])**2+(cc-origin[1])**2)*res**2;near+=np.where(abs(floor[rr,cc])<.5,0,1e6);start=(int(rr[np.argmin(near)]),int(cc[np.argmin(near)]));visited=np.zeros(shape,bool);visited[start]=True;q=deque([start])
while q:
 i,j=q.popleft()
 for di,dj in [(-1,0),(1,0),(0,-1),(0,1)]:
  u,v=i+di,j+dj
  if 0<=u<shape[0] and 0<=v<shape[1] and free[u,v] and not visited[u,v] and abs(float(floor[u,v])-float(floor[i,j]))<=.2:visited[u,v]=True;q.append((u,v))
rr,cc=np.nonzero(visited);ground=np.column_stack([(rr+lo[0]+.5)*res,(cc+lo[1]+.5)*res,floor[rr,cc]]).astype(np.float32);np.savez_compressed(root/'REFERENCE_GROUND_PROXY.npz',connected_ground_xyz=ground,resolution=np.array(res),floor=floor,free=free,connected=visited,origin_index=lo)
meta={'method':'Conservative point-cloud-derived ground connectivity proxy; not certified ground truth or actual HT traversability','resolution_m':res,'min_surface_per_xy':True,'obstacle_vertical_band_m':[.2,1.],'eroded_neighbor_cells':[3,3],'maximum_neighbor_height_difference_m':.2,'connected_ground_cells':len(ground),'proxy_area_m2':len(ground)*res**2,'seed_world_xy':((np.array(start)+lo+.5)*res).tolist(),'connected_bounds_xyz':[ground.min(0).tolist(),ground.max(0).tolist()],'limitations':['Preview point cloud may omit geometry or undersample obstacles','No vehicle contact dynamics or exact mesh path verification','Conservative erosion can exclude reachable narrow paths; roofs and height discontinuities can affect inferred terrain','Report observed fraction on this proxy separately; do not call it full campus ground truth']};(root/'REFERENCE_GROUND_PROXY.json').write_text(json.dumps(meta,indent=2));print(json.dumps(meta,indent=2))
