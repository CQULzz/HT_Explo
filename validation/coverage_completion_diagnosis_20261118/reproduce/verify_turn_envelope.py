from pathlib import Path
import numpy as np,json
r=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');v=np.load(r/'mesh_vertices_aligned.npy');f=np.load(r/'mesh_faces.npy');path=np.load(r/'R1_proxy_path.npy');tris=v[f];lo=path.min(0)-[1,1,2];hi=path.max(0)+[1,1,2];mask=np.all(tris.max(1)>=lo,axis=1)&np.all(tris.min(1)<=hi,axis=1);tri=tris[mask];print('ROI triangles',len(tri),flush=True)
# Standard triangle-AABB separating-axis test, including triangle normals and edge cross axes.
def colliding(c,half):
 t=tri-c;good=np.all(t.max(1)>=-half,axis=1)&np.all(t.min(1)<=half,axis=1);tt=t[good]
 if not len(tt):return 0
 edges=np.roll(tt,-1,axis=1)-tt;normal=np.cross(edges[:,0],edges[:,1]);axes=[normal]
 for k in range(3):
  basis=np.zeros(3);basis[k]=1
  for j in range(3):axes.append(np.cross(edges[:,j],basis))
 hit=np.ones(len(tt),bool)
 for ax in axes:
  radius=abs(ax)@half;projection=np.einsum('nkj,nj->nk',tt,ax);hit&=(projection.max(1)>=-radius-1e-7)&(projection.min(1)<=radius+1e-7)
 return int(hit.sum())
def surface(p):
 mask=np.all(tri[:,:,:2].min(1)<=p[:2]+1e-6,axis=1)&np.all(tri[:,:,:2].max(1)>=p[:2]-1e-6,axis=1);t=tri[mask];d=t[:,1,:2]-t[:,0,:2];e=t[:,2,:2]-t[:,0,:2];q=p[:2]-t[:,0,:2];den=d[:,0]*e[:,1]-e[:,0]*d[:,1];valid=abs(den)>1e-9;t=t[valid];d=d[valid];e=e[valid];q=q[valid];den=den[valid];u=(q[:,0]*e[:,1]-e[:,0]*q[:,1])/den;w=(d[:,0]*q[:,1]-q[:,0]*d[:,1])/den;valid=(u>=-1e-5)&(w>=-1e-5)&(u+w<=1.00001);z=t[:,0,2]+u*(t[:,1,2]-t[:,0,2])+w*(t[:,2,2]-t[:,0,2]);z=z[valid]
 return None if not len(z) else float(z[np.argmin(abs(z-p[2]))])
samples=[]
for a,b in zip(path[:-1],path[1:]):
 samples.extend([a+(b-a)*u for u in np.arange(0,1,.2)])
samples.append(path[-1]);problems=[];max_support_error=0.;max_support_span=0.;maxhits=0;stepheights=[]
for i,p in enumerate(samples):
 z=surface(p)
 if z is None or abs(z-p[2])>.25:problems.append({'index':i,'type':'missing_or_inconsistent_floor','point':p.tolist(),'mesh_z':z});continue
 support=[]
 for x in [-.425,0,.425]:
  for y in [-.425,0,.425]:support.append(surface(np.array([p[0]+x,p[1]+y,z])))
 if any(h is None for h in support):problems.append({'index':i,'type':'missing_corner_support','point':p.tolist()});continue
 max_support_error=max(max_support_error,abs(z-p[2]));max_support_span=max(max_support_span,max(support)-min(support));stepheights.append(z)
 if max(support)-min(support)>.4:problems.append({'index':i,'type':'large_height_span','point':p.tolist()})
 hits=colliding(np.array([p[0],p[1],z+.575]),np.array([.425,.425,.425]));maxhits=max(maxhits,hits)
 if hits:problems.append({'index':i,'type':'obstacle_mesh_intersection_0.15_to1.0m_band','point':p.tolist(),'triangles':hits})
result={'region':'R1','target_xyz':path[-1].tolist(),'route_anchor_xyz':path[0].tolist(),'path_length_m':float(np.linalg.norm(np.diff(path[:,:2],axis=0),axis=1).sum()),'samples':len(samples),'sample_step_m':.1,'footprint_xy_m':[.85,.85],'obstacle_vertical_band_above_mesh_floor_m':[.15,1.],'support_test':'Nine footprint grid points on actual collision mesh at every sample; floor follows nearest predicted terrain layer','maximum_abs_mesh_floor_vs_preview_m':max_support_error,'maximum_support_height_span_m':max_support_span,'maximum_mesh_collision_triangles':maxhits,'issues':problems,'passed':not problems,'scope':'Static geometric path verification only. Axis-aligned footprint along grid route, no full contact dynamics/turning sweep/hardware certification. Not a new Gazebo exploration.'};(r/'R1_TURN_ENVELOPE_VERIFICATION.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='issues'},indent=2));print('First issues',problems[:8])
