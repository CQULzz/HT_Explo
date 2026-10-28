"""Analytic pose/shape and refusal checks; no ROS, GPU, or terrain labels."""
import numpy as np
import pytest
from scipy.spatial.transform import Rotation
from surface_registration import align_scan,RegistrationConfig


def scene(step=0.,post=0.):
 n=103;res=.04;axis=(np.arange(n)+.5-n/2)*res;x,y=np.meshgrid(axis,axis,indexing='ij')
 z=.02*x-.01*y;z=z+np.where(x>.6,step,0.);z=z+np.where((abs(x+.5)<.10)&(abs(y)<.10),post,0.)
 prior=np.zeros((7,n,n),np.float32);prior[0]=z;prior[1]=.01;prior[2]=1.;prior[4]=.2
 # One actual return per cell, no invented returns in empty areas.
 points=np.c_[x.ravel(),y.ravel(),z.ravel()];return points,prior,res


def mispose():
 return Rotation.from_euler('xy',[.5,-.4],degrees=True).as_matrix(),np.array([0.,0.,.025])


def test_recovers_known_pose_error_on_tilted_reference():
 p,ref,res=scene();R,t=mispose();rr,tt,info=align_scan(p,R,t,ref,np.zeros(3),res)
 assert info['status']=='APPLIED'
 before=p@R.T+t;after=p@rr.T+tt
 assert np.median(abs(after[:,2]-p[:,2]))<.003
 assert np.median(abs(after[:,2]-p[:,2]))<.2*np.median(abs(before[:,2]-p[:,2]))
 assert np.linalg.det(rr)==pytest.approx(1.,abs=1e-12)
 assert info['rigid_after_median_abs_m']<info['rigid_before_median_abs_m']


@pytest.mark.parametrize('height',[.02,.05,.10,.20,.50])
def test_new_step_and_narrow_post_are_not_flattened(height):
 floor,ref,res=scene();p,_,_=scene(step=height,post=height);R,t=mispose()
 rr,tt,info=align_scan(p,R,t,ref,np.zeros(3),res)
 # Registration may refuse ambiguous overlap, but cannot nonrigidly remove a feature.
 before=p@R.T+t;after=p@rr.T+tt
 assert np.allclose(np.linalg.norm(after[1:]-after[:-1],axis=1),np.linalg.norm(before[1:]-before[:-1],axis=1),atol=1e-12)
 normal=rr@np.array([-.02,.01,1.]);normal/=np.linalg.norm(normal)
 heights=np.einsum('ij,j->i',after-(floor@rr.T+tt),normal)
 original=(p-floor)[:,2];assert np.allclose(heights,original/np.sqrt(1.0005),atol=1e-10)
 assert np.max(heights)>=height*.999


def test_unknown_or_stale_reference_cannot_supply_constraints():
 p,ref,res=scene();R,t=mispose()
 for unknown in [True,False]:
  q=ref.copy()
  if unknown:q[2]=0
  else:q[4]=100
  rr,tt,info=align_scan(p,R,t,q,np.zeros(3),res)
  assert info['status']=='INSUFFICIENT_OBSERVED_OVERLAP'
  assert np.array_equal(rr,R) and np.array_equal(tt,t)


def test_large_jump_not_reinterpreted_as_pose_correction():
 p,ref,res=scene();R=np.eye(3);t=np.array([0.,0.,.30]);rr,tt,info=align_scan(p,R,t,ref,np.zeros(3),res)
 assert info['status']!='APPLIED';assert np.array_equal(rr,R) and np.array_equal(tt,t)


def test_already_aligned_input_not_adjusted_and_inputs_immutable():
 p,ref,res=scene(step=.1,post=.3);saved=p.copy(),ref.copy();R=np.eye(3);t=np.zeros(3)
 rr,tt,info=align_scan(p,R,t,ref,np.zeros(3),res)
 assert info['status']!='APPLIED';assert np.array_equal(rr,R) and np.array_equal(tt,t)
 assert np.array_equal(p,saved[0]) and np.array_equal(ref,saved[1])


def test_geometry_and_config_validation():
 p,ref,res=scene()
 with pytest.raises(ValueError):RegistrationConfig(min_cells=0)
 with pytest.raises(ValueError):RegistrationConfig(max_tilt_rad=float('nan'))
 with pytest.raises(ValueError):align_scan(p,np.eye(3)*2,np.zeros(3),ref,np.zeros(3),res)
