from pathlib import Path
import numpy as np,json
from scipy.spatial import cKDTree
r=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');v=np.load(r/'mesh_vertices.npy');f=np.load(r/'mesh_faces.npy');a=v[f];lo=a[:,:,:2].min(1);hi=a[:,:,:2].max(1)
for p in [[0,0],[73.25,6.75],[115.75,118.25],[-175,50],[-150,0]]:
 mask=np.all(lo<=p,axis=1)&np.all(hi>=p,axis=1);tri=a[mask];d=tri[:,1,:2]-tri[:,0,:2];e=tri[:,2,:2]-tri[:,0,:2];q=np.array(p)-tri[:,0,:2];den=d[:,0]*e[:,1]-e[:,0]*d[:,1];good=abs(den)>1e-8;tri=tri[good];d=d[good];e=e[good];q=q[good];den=den[good];u=(q[:,0]*e[:,1]-e[:,0]*q[:,1])/den;w=(d[:,0]*q[:,1]-q[:,0]*d[:,1])/den;good=(u>=-1e-6)&(w>=-1e-6)&(u+w<=1.000001);zz=tri[:,0,2]+u*(tri[:,1,2]-tri[:,0,2])+w*(tri[:,2,2]-tri[:,0,2]);print('vertical mesh intersections',p,zz[good].tolist())
obs=np.load('/home/lzz/tare_native_campus_repeat_20261118/analysis/COVERAGE_REFERENCE_COMPARISON.npz')['observed_voxel_centers'][::8];tree=cKDTree(v)
print('mesh vertex NN',dict(zip(['median','p90'],np.quantile(tree.query(obs)[0],[.5,.9]).tolist())))
