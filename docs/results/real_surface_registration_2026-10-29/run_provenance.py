from pathlib import Path
import os,sys,json,time,numpy as np
O=Path(__file__).parent;R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');C=Path('/home/lzz/my test/ht_cupy_gpu_ws_20261028/src/elevation_mapping_cupy_2204/elevation_mapping_cupy')
sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
import cupy as cp
import elevation_mapping_cupy.deterministic_fusion as df
from elevation_mapping_cupy import ElevationMap
import replay_newbags_rviz as replay
mode=sys.argv[1];bag=sys.argv[2];assert mode in ['baseline','sigma','profile_clock','profile_clock_sigma','registration']
if mode in ['sigma','profile_clock_sigma','registration']:
 # Diagnostic intervention only. Do not alter independent mapper source yet.
 assert 'fabsf(h-z)>v*q[2]' in df._SOURCE
 df._SOURCE=df._SOURCE.replace('fabsf(h-z)>v*q[2]','fabsf(h-z)>q[2]*sqrtf(fmaxf(v+measurement,0.f))')
if mode.startswith('profile_clock'):
 old_variance=ElevationMap.update_variance
 def variance(self):
  self.param.time_variance=.0001*5.*float(self.param.time_interval)
  old_variance(self)
 ElevationMap.update_variance=variance
if mode=='registration':
 from surface_registration import align_scan
 old_input=ElevationMap.input_pointcloud
 alignment=[]
 def registered_input(self,points,channels,R,t,*args,**kwargs):
  rr,tt,info=align_scan(points,R,t,cp.asnumpy(self.elevation_map),cp.asnumpy(self.center),self.resolution)
  alignment.append(info)
  return old_input(self,points,channels,rr.astype(np.float32),tt.astype(np.float32),*args,**kwargs)
 ElevationMap.input_pointcloud=registered_input
records=[];prior_fuse=df.DeterministicFusion.fuse;old_move=ElevationMap.move_to;center=[np.zeros(3)];current=[None]
def move(self,p,R):
 old_move(self,p,R);center[0]=cp.asnumpy(self.center).copy();current[0]=self
ElevationMap.move_to=move
probes=[(-.48,12.24),(-3.,13.),(-1.,18.)]
def fuse(self,elevation_map,normal_map,points,R,t,new_map,*a,**kw):
 pre=cp.asnumpy(elevation_map[:3]);xyz=cp.asnumpy(points[:,:3]);rot=cp.asnumpy(R);trans=cp.asnumpy(t)
 w=xyz@rot.T+trans;world=w+center[0];width=self.width;p=self.param
 idx=np.clip((w[:,:2]/p.resolution+.5*width).astype(int),0,width-1);i,j=idx.T
 h,v,valid=pre[0,i,j],pre[1,i,j],pre[2,i,j]>.5
 measure=p.sensor_noise_factor*xyz[:,2]**2;delta=abs(h-w[:,2]);oldgate=v*p.mahalanobis_thresh;sgate=p.mahalanobis_thresh*np.sqrt(np.maximum(v+measure,0.))
 geometry=np.all(np.isfinite(w),axis=1)&(i>0)&(i<width-1)&(j>0)&(j<width-1)&(np.linalg.norm(w-trans,axis=1)>=p.min_valid_distance)&(w[:,2]-trans[2]<=p.max_height_range)&(w[:,2]-trans[2]<=np.maximum(np.linalg.norm(w[:,:2],axis=1)-p.ramped_height_range_b,0.)*p.ramped_height_range_a+p.ramped_height_range_c)
 row={'scan':len(records),'probes':[]}
 for x,y in probes:
  use=geometry&valid&(abs(world[:,0]-x)<=1.)&(abs(world[:,1]-y)<=1.)
  if use.sum():
   z=world[use,2];A=np.c_[world[use,:2]-[x,y],np.ones(use.sum())];coef=np.linalg.lstsq(A,z,rcond=None)[0];res=z-A@coef
   row['probes'].append({'world_xy':[x,y],'points':int(use.sum()),'raw_plane_rms_m':float(np.sqrt(np.mean(res**2))),'median_abs_innovation_m':float(np.median(delta[use])),'prior_std_p50_m':float(np.median(np.sqrt(v[use]))),'old_gate_p50_m':float(np.median(oldgate[use])),'innovation_gate_p50_m':float(np.median(sgate[use])),'old_rejected':int((delta[use]>oldgate[use]).sum()),'sigma_rejected':int((delta[use]>sgate[use]).sum()),'rejected_only_old':int(((delta[use]>oldgate[use])&(delta[use]<=sgate[use])).sum())})
 result=prior_fuse(self,elevation_map,normal_map,points,R,t,new_map,*a,**kw)
 records.append(row)
 return result
df.DeterministicFusion.fuse=fuse
out=O/(mode+'_'+bag);sys.argv=['replay','--bag',str(Path('/media/lzz/My Passport/HT_newbags_replay_20261028/inputs')/('rosbag2_2026_10_28-'+('17_00_43' if bag=='moving' else '16_53_17'))/('rosbag2_2026_10_28-'+('17_00_43' if bag=='moving' else '16_53_17'))),'--output',str(out),'--cupy-package',str(C)]
try:replay.main()
finally:
 if mode=='registration':(O/(mode+'_'+bag+'_ALIGNMENT.json')).write_text(json.dumps(alignment,indent=2)+'\n')
 (O/(mode+'_'+bag+'_PROVENANCE.json')).write_text(json.dumps({'scope':'Instrumented full replay; sigma case is diagnostic source-text substitution only. Same upstream measurement values, filter, TF and HT; not production change yet.','mode':mode,'bag':bag,'records':records},indent=2)+'\n')
