"""Finite visibility geometry and visible-feature retention; no ROS nodes."""
from copy import deepcopy
from pathlib import Path
import numpy as np
import pytest
from ht_scout_bridge.geometry import wheel_occlusion_mask,self_filter_keep_mask,load_calibration

PROFILE=Path(__file__).resolve().parents[1]/'config/scout_extrinsics.yaml'
WHEEL={'axis':'y','center_xyz':[.5,0.,0.],'radius':.2,'half_length':.1}
SETTINGS={'enabled':True,'max_lidar_range_m':1.6,'min_behind_m':.03,'max_behind_m':.5,'ground_z_m':-.6,'min_height_above_ground_m':.03,'max_return_z_m':.3}
ORIGIN=np.array([0.,0.,.5])


def test_shadow_outside_wheel_is_removed_but_before_and_beside_are_visible():
 points=np.array([[.8,0.,-.3],[.2,0.,.3],[.9,.6,-.3],[.9,0.,.5]])
 np.testing.assert_array_equal(wheel_occlusion_mask(points,ORIGIN,[WHEEL],SETTINGS),[True,False,False,False])
 # First endpoint is outside the wheel: endpoint-only filtering missed it.
 assert (.8-.5)**2+(-.3)**2>WHEEL['radius']**2


def test_near_boundary_and_far_shadow_outside_verified_limits_retained():
 direction=np.array([1.,0.,-1.])/np.sqrt(2);just_after=np.array([.5,0.,0.])+.21*direction
 p=np.array([just_after,[3.,0.,-2.5]])
 assert not wheel_occlusion_mask(p,ORIGIN,[WHEEL],SETTINGS).any()


def test_ground_guard_preserves_even_geometrically_occluded_near_ground():
 settings=dict(SETTINGS,ground_z_m=-.31,min_height_above_ground_m=.03)
 assert not wheel_occlusion_mask(np.array([[.8,0.,-.3]]),ORIGIN,[WHEEL],settings).any()


def test_visible_vertical_structure_protects_lower_shadow_returns():
 points=np.array([[.8,0.,-.3],[.8,0.,.1]])
 assert wheel_occlusion_mask(points,ORIGIN,[WHEEL],SETTINGS)[0]
 guarded=dict(SETTINGS,preserve_vertical_support=True,support_radius_m=.04,support_height_m=.04)
 assert not wheel_occlusion_mask(points,ORIGIN,[WHEEL],guarded).any()
 shifted=points.copy();shifted[1,1]=.1
 assert wheel_occlusion_mask(shifted,ORIGIN,[WHEEL],guarded)[0]


def test_finite_y_caps_and_parallel_axes():
 p=np.array([[.8,.3,-.3]])
 assert not wheel_occlusion_mask(p,np.array([0.,.3,.5]),[WHEEL],SETTINGS).any()
 # Ray parallel to the cylinder axis crosses its two end caps.
 settings=dict(SETTINGS,ground_z_m=-.6)
 p=np.array([[.5,.4,0.]])
 assert wheel_occlusion_mask(p,np.array([.5,-.5,0.]),[WHEEL],settings)[0]


@pytest.mark.parametrize('key,value',[('max_lidar_range_m',float('nan')),('ground_z_m',float('inf')),('min_behind_m',0),('max_behind_m',.01)])
def test_invalid_limits_rejected(key,value):
 config=dict(SETTINGS);config[key]=value
 with pytest.raises(ValueError):wheel_occlusion_mask(np.empty((0,3)),ORIGIN,[WHEEL],config)


def test_sensor_inside_occluder_and_missing_geometry_rejected():
 with pytest.raises(ValueError):wheel_occlusion_mask(np.empty((0,3)),[.5,0,0],[WHEEL],SETTINGS)
 with pytest.raises(ValueError):wheel_occlusion_mask(np.empty((0,3)),ORIGIN,[],SETTINGS)


def test_default_profile_retains_previously_retained_ground_with_three_cm_band():
 profile,b,l=load_calibration(PROFILE);f=profile['lidar_self_filter'];assert f['wheel_occlusion']['enabled'] is True
 old=deepcopy(f);old.pop('wheel_occlusion');t=np.linalg.inv(b)@l
 grid=np.arange(-1.5,1.501,.025);x,y=np.meshgrid(grid,grid,indexing='ij');points=[]
 for dz in [-.03,0.,.03]:points.append(np.c_[x.ravel(),y.ravel(),np.full(x.size,-.23479+dz)])
 body=np.concatenate(points);lidar=(body-t[:3,3])@t[:3,:3]
 np.testing.assert_array_equal(self_filter_keep_mask(lidar,f,t),self_filter_keep_mask(lidar,old,t))


def test_existing_body_volumes_and_nonfinite_rejections_unchanged():
 profile,b,l=load_calibration(PROFILE);f=profile['lidar_self_filter'];old=deepcopy(f);old.pop('wheel_occlusion');t=np.linalg.inv(b)@l
 rng=np.random.default_rng(20261029);body=rng.uniform([-1,-1,-.3],[1,1,.7],(20000,3));lidar=(body-t[:3,3])@t[:3,:3]
 before=self_filter_keep_mask(lidar,old,t);after=self_filter_keep_mask(lidar,f,t)
 assert not np.any(after&~before)
 source=np.array([[np.nan,0.,0.],[0.,np.inf,0.]])
 with np.errstate(invalid='ignore'):assert not self_filter_keep_mask(source,f,t).any()


def test_unobstructed_nearby_high_obstacles_and_external_features_retained():
 profile,b,l=load_calibration(PROFILE);f=profile['lidar_self_filter'];old=deepcopy(f);old.pop('wheel_occlusion');t=np.linalg.inv(b)@l
 angles=np.linspace(-np.pi,np.pi,90,endpoint=False);points=[]
 # Endpoints above wheel tops: a descending ray starting above the wheels
 # cannot cross their low solid volume before these points.
 for radius in [.8,1.,1.3]:
  for height in [.20,.35,.50]:points.append(np.c_[radius*np.cos(angles),radius*np.sin(angles),np.full(len(angles),height)])
 body=np.concatenate(points);lidar=(body-t[:3,3])@t[:3,:3];before=self_filter_keep_mask(lidar,old,t);after=self_filter_keep_mask(lidar,f,t)
 np.testing.assert_array_equal(after,before);assert before.sum()>500


def test_visibility_requires_explicit_calibrated_shape_configuration():
 profile,b,l=load_calibration(PROFILE);f=profile['lidar_self_filter'];t=np.linalg.inv(b)@l
 for invalid in [None,{'enabled':'false'}]:
  q=deepcopy(f);q['wheel_occlusion']=invalid
  with pytest.raises(ValueError):self_filter_keep_mask(np.empty((0,3)),q,t)
 legacy={'enabled':True,'min_xyz':[-1,-1,-1],'max_xyz':[1,1,1],'wheel_occlusion':SETTINGS}
 with pytest.raises(ValueError):self_filter_keep_mask(np.empty((0,3)),legacy)
