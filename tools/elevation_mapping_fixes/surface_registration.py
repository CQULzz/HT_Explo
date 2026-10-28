"""Constrained scan-to-map Z/tilt alignment, preserving rigid shape.

No neural score enters the fit. Correspondences require previously observed,
recent, locally continuous surfaces. Unknown cells never provide constraints.
A withheld spatial subset validates the residual reduction before commitment.
"""
from dataclasses import dataclass
import math
import numpy as np
from scipy.ndimage import maximum_filter,minimum_filter
from scipy.spatial.transform import Rotation

@dataclass(frozen=True)
class RegistrationConfig:
 min_cells:int=200
 max_reference_age_s:float=2.
 max_reference_variance_m2:float=.25
 max_reference_jump_m:float=.075
 association_m:float=.10
 robust_scale_m:float=.015
 max_tilt_rad:float=math.radians(2.)
 max_translation_m:float=.08
 min_axis_std_m:float=.30
 min_heldout_improvement_m:float=.002
 min_inlier_fraction:float=.70

 def __post_init__(self):
  if isinstance(self.min_cells,bool) or not isinstance(self.min_cells,int) or self.min_cells<20:
   raise ValueError('min_cells must be an integer >=20')
  for name,value in vars(self).items():
   if name!='min_cells' and (not math.isfinite(value) or value<=0):
    raise ValueError(name+' must be positive and finite')
  if self.min_inlier_fraction>1 or self.max_tilt_rad>=math.pi/4:
   raise ValueError('Invalid inlier fraction or tilt bound')

def align_scan(points,R,t,prior,center,resolution,cfg=None):
 cfg=cfg or RegistrationConfig();R=np.asarray(R,np.float64);t=np.asarray(t,np.float64);prior=np.asarray(prior);center=np.asarray(center);w=np.asarray(points,np.float64)@R.T+t
 if (prior.ndim!=3 or prior.shape[0]<5 or prior.shape[1]!=prior.shape[2]
     or R.shape!=(3,3) or t.shape!=(3,) or center.shape!=(3,)
     or not np.isfinite(R).all() or not np.isfinite(t).all() or not np.isfinite(center).all()
     or not math.isfinite(resolution) or resolution<=0
     or not np.allclose(R.T@R,np.eye(3),atol=1e-5) or np.linalg.det(R)<.99999
     or w.ndim!=2 or w.shape[1]!=3):
  raise ValueError('Invalid rigid scan/reference geometry')
 z,var,valid,age=prior[0],prior[1],prior[2]>.5,prior[4];width=z.shape[0]
 observed=valid & np.isfinite(z)&np.isfinite(var)&(var>=0)&(var<=cfg.max_reference_variance_m2)&np.isfinite(age)&(age<=cfg.max_reference_age_s)
 lo=minimum_filter(np.where(observed,z,np.inf),size=3,mode='constant',cval=np.inf);hi=maximum_filter(np.where(observed,z,-np.inf),size=3,mode='constant',cval=-np.inf)
 supported=minimum_filter(observed.astype(np.uint8),size=3,mode='constant',cval=0).astype(bool)
 smooth=observed & supported & (hi-lo<cfg.max_reference_jump_m)
 finite=np.isfinite(w).all(axis=1);idx=np.zeros((len(w),2),np.int64);idx[finite]=np.floor((w[finite,:2]-center[:2])/resolution+.5*width).astype(np.int64)
 inside=finite&(idx[:,0]>0)&(idx[:,0]<width-1)&(idx[:,1]>0)&(idx[:,1]<width-1)
 ids=np.flatnonzero(inside);ij=idx[ids];keep=smooth[ij[:,0],ij[:,1]];ids=ids[keep];ij=ij[keep]
 if len(ids)<cfg.min_cells:return R,t,{'status':'INSUFFICIENT_OBSERVED_OVERLAP','points':len(ids)}
 keys=ij[:,0]*width+ij[:,1];keys,inverse=np.unique(keys,return_inverse=True);counts=np.bincount(inverse);means=np.column_stack([np.bincount(inverse,weights=w[ids,k])/counts for k in range(3)])
 i,j=keys//width,keys%width;target=z[i,j]+center[2];error=means[:,2]-target;use=abs(error)<=cfg.association_m
 keys,means,error=keys[use],means[use],error[use];n=len(keys)
 if n<cfg.min_cells:return R,t,{'status':'INSUFFICIENT_ASSOCIATED_CELLS','cells':n}
 xy=means[:,:2]-t[:2];A=np.c_[xy,np.ones(n)];train=(keys%5)!=0;test=~train
 if train.sum()<cfg.min_cells*.6 or test.sum()<20:return R,t,{'status':'INSUFFICIENT_VALIDATION_CELLS','cells':n}
 span=np.linalg.eigvalsh(np.cov(xy[train].T))
 if span.min()<cfg.min_axis_std_m**2:return R,t,{'status':'DEGENERATE_GEOMETRY','cells':n}
 coef=np.linalg.lstsq(A[train],error[train],rcond=None)[0]
 for _ in range(5):
  residual=error[train]-A[train]@coef;weight=np.minimum(1.,cfg.robust_scale_m/np.maximum(abs(residual),1e-9));root=np.sqrt(weight);coef=np.linalg.lstsq(A[train]*root[:,None],error[train]*root,rcond=None)[0]
 before=float(np.median(abs(error[test])));after=float(np.median(abs(error[test]-A[test]@coef)));fraction=float(np.mean(abs(error[train]-A[train]@coef)<2*cfg.robust_scale_m))
 info={'status':'REJECTED','cells':n,'train_cells':int(train.sum()),'heldout_cells':int(test.sum()),'raw_heldout_median_abs_m':before,'corrected_heldout_median_abs_m':after,'coef_source_minus_reference':coef.tolist(),'train_inlier_fraction':fraction}
 if abs(coef[2])>cfg.max_translation_m or np.linalg.norm(coef[:2])>math.tan(cfg.max_tilt_rad):info['status']='CORRECTION_EXCEEDS_BOUND';return R,t,info
 if fraction<cfg.min_inlier_fraction:info['status']='INCONSISTENT_SURFACES';return R,t,info
 if before-after<cfg.min_heldout_improvement_m:info['status']='NO_VALIDATED_IMPROVEMENT';return R,t,info
 correction=Rotation.from_rotvec([-coef[1],coef[0],0.]).as_matrix();rr=correction@R;tt=t.copy();tt[2]-=coef[2]
 # Validate the actual rigid transform against held-out, still-observed map
 # correspondences; a linear height subtraction alone is not the runtime.
 moved=(means-t)@correction.T+tt
 at=np.floor((moved[:,:2]-center[:2])/resolution+.5*width).astype(np.int64)
 usable=test&(at[:,0]>0)&(at[:,0]<width-1)&(at[:,1]>0)&(at[:,1]<width-1)
 known=np.flatnonzero(usable);known=known[smooth[at[known,0],at[known,1]]]
 if len(known)<max(20,.7*test.sum()):info['status']='RIGID_VALIDATION_LOST_OVERLAP';return R,t,info
 actual=moved[known,2]-center[2]-z[at[known,0],at[known,1]]
 actual_before=float(np.median(abs(error[known])));actual_after=float(np.median(abs(actual)))
 info.update(rigid_heldout_cells=len(known),rigid_before_median_abs_m=actual_before,rigid_after_median_abs_m=actual_after)
 if actual_before-actual_after<cfg.min_heldout_improvement_m:info['status']='NO_RIGID_VALIDATED_IMPROVEMENT';return R,t,info
 info['status']='APPLIED';info['rotation_vector_rad']=[float(-coef[1]),float(coef[0]),0.];info['translation_z_m']=float(-coef[2]);return rr,tt,info
