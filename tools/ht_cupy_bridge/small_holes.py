"""Bounded local interpolation; never persisted as a new observation.

Small gaps require fresh, quality-approved samples in all four quadrants,
a nearest measurement within 12cm and a locally planar 9x9 window at 4cm resolution. Unobserved pits are intrinsically ambiguous:
this is a bounded interpolation assumption, not negative-obstacle detection.
"""
import numpy as np
from scipy.ndimage import label,uniform_filter,maximum_filter,minimum_filter,distance_transform_edt


def repair_small_holes(height, observed, rejected, obstacle, fresh_height,
                       fresh_variance, fresh_age, resolution, protected=None):
    z=np.asarray(height,np.float32)
    arrays=[np.asarray(v) for v in (observed,rejected,obstacle,fresh_height,fresh_variance,fresh_age)]
    if z.ndim!=2 or any(v.shape!=z.shape for v in arrays) or not .02<=resolution<=.1:
        raise ValueError('Invalid small-hole inputs')
    observed,rejected,obstacle,current,var,age=arrays
    blocked=np.asarray(rejected,bool)|np.isfinite(obstacle)
    if protected is not None:
        if np.shape(protected)!=z.shape:raise ValueError('Invalid protected mask')
        blocked|=np.asarray(protected,bool)
    # No interpolation across an observed, even shallow, negative feature.
    # Fit every candidate from original measurements in one vectorized pass.
    # No iterative propagation and no fitted value enters the historical map.
    output,filled=_narrow_gaps(z,observed,blocked,current,var,age,resolution)
    _,missing_components=label(~np.isfinite(z),structure=np.ones((3,3)))
    _,filled_components=label(filled,structure=np.ones((3,3)))
    stats={'candidate_components':missing_components,'filled_components':filled_components,
           'filled_cells':int(filled.sum())}
    return output,filled,stats


def _narrow_gaps(z,observed,blocked,current,var,age,resolution):
    radius=max(1,int(np.floor(.16/resolution+1e-8)));size=2*radius+1
    known=(np.asarray(observed,bool)&np.isfinite(z)&np.isfinite(current)&np.isfinite(var)
        &(var>=0)&(var<=.25)&np.isfinite(age)&(age>=-.001)&(age<=2.)
        &(np.abs(current-z)<=.03)&~blocked)
    mean=lambda a:uniform_filter(np.asarray(a,np.float64),size=size,mode='constant')
    count=mean(known)*size**2
    changed_surface=np.isfinite(z)&np.isfinite(current)&(np.abs(current-z)>.03)&np.isfinite(age)&(age<=2.)
    protected=maximum_filter(blocked|changed_surface,size=size,mode='constant')
    candidate=~np.isfinite(z)&~protected&(count>=12)
    # Integrals count original samples strictly in each of four quadrants.
    n,m=z.shape;rr=np.arange(n);cc=np.arange(m)
    ii=np.pad(known.astype(np.int64).cumsum(0).cumsum(1),((1,0),(1,0)))
    for dr in [-1,1]:
        r0=np.maximum(0,rr-radius) if dr<0 else rr+1
        r1=rr if dr<0 else np.minimum(n,rr+radius+1)
        r0=np.minimum(r0,n)
        for dc in [-1,1]:
            c0=np.maximum(0,cc-radius) if dc<0 else np.minimum(m,cc+1)
            c1=cc if dc<0 else np.minimum(m,cc+radius+1)
            q=ii[r1[:,None],c1]-ii[r0[:,None],c1]-ii[r1[:,None],c0]+ii[r0[:,None],c0]
            candidate&=q>=2
    candidate&=distance_transform_edt(~known)*resolution<=.12+1e-9
    if not np.any(candidate):return z,np.zeros(z.shape,bool)
    # The box-filter moments still use the original full-grid arithmetic.
    # Solve planes only at eligible missing pixels, instead of allocating
    # eleven more 291x291 fit/slope/residual arrays every frame. Other pixels
    # cannot be filled, so their plane solutions are unused work.
    index=np.nonzero(candidate)
    sample_mean=lambda a:mean(a)[index]
    rr,cc=np.indices(z.shape);x=rr*resolution;y=cc*resolution
    h=np.where(known,z,0.).astype(np.float64);k=known.astype(np.float64)
    norm=np.maximum(sample_mean(k),1e-15)
    ex=sample_mean(k*x)/norm;ey=sample_mean(k*y)/norm;ez=sample_mean(h)/norm
    xx=sample_mean(k*x*x)/norm-ex*ex;yy=sample_mean(k*y*y)/norm-ey*ey;xy=sample_mean(k*x*y)/norm-ex*ey
    xz=sample_mean(h*x)/norm-ex*ez;yz=sample_mean(h*y)/norm-ey*ez;zz=sample_mean(h*h)/norm-ez*ez
    det=xx*yy-xy*xy;good=det>1e-8
    a=np.divide(xz*yy-yz*xy,det,out=np.zeros_like(det),where=good)
    b=np.divide(yz*xx-xz*xy,det,out=np.zeros_like(det),where=good)
    rms=np.sqrt(np.maximum(0.,zz-a*xz-b*yz));pred=ez+a*(x[index]-ex)+b*(y[index]-ey)
    lo=minimum_filter(np.where(known,z,np.inf),size=size,mode='constant',cval=np.inf)[index]
    hi=maximum_filter(np.where(known,z,-np.inf),size=size,mode='constant',cval=-np.inf)[index]
    accepted=good&(np.hypot(a,b)<=.35)&(rms<=.006)&(pred>=lo-.01)&(pred<=hi+.01)
    # Reject measured jumps at the edge of the support window (including pits).
    jumps=np.zeros(z.shape,bool)
    v=known[:-1]&known[1:]&(np.abs(np.diff(z,axis=0))>.018)
    jumps[:-1]|=v;jumps[1:]|=v
    v=known[:,:-1]&known[:,1:]&(np.abs(np.diff(z,axis=1))>.018)
    jumps[:,:-1]|=v;jumps[:,1:]|=v
    accepted&=~maximum_filter(jumps,size=size,mode='constant')[index]
    filled=np.zeros(z.shape,bool);filled[index]=accepted
    result=z.copy();result[filled]=pred[accepted].astype(np.float32)
    return result,filled
