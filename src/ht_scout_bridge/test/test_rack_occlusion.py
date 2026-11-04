from pathlib import Path
from copy import deepcopy
import numpy as np
import pytest
from ht_scout_bridge.geometry import load_calibration,self_filter_keep_mask
from ht_scout_bridge.planar_occlusion import rack_occlusion_mask,rear_deck

HERE=Path(__file__).parent
PROFILE=HERE.parent/'config/scout_extrinsics.yaml'

def setup():
    profile,base,lidar=load_calibration(PROFILE)
    transform=np.linalg.inv(base)@lidar
    return profile['lidar_self_filter'],transform

def test_recorded_returns_behind_urdf_rack_are_removed_before_mapping():
    profile,t=setup()
    with np.load(HERE/'fixtures/rack_occlusion/recorded_rear_returns.npz') as fixture:
        points=fixture['points']
        # Independent full3D STL ray audit, not the planar production reducer.
        assert len(points)==28 and np.all(fixture['full_mesh_far_hit_m']>.05)
    lidar=(points-t[:3,3])@t[:3,:3]
    old=deepcopy(profile);old['rack_occlusion']['enabled']=False
    assert self_filter_keep_mask(lidar,old,t).all()
    assert not self_filter_keep_mask(lidar,profile,t).any()

def test_visible_upper_post_protects_its_lower_return():
    profile,t=setup();cfg=profile['rack_occlusion']
    points=np.array([[-.47,-.11,.22],[-.47,-.11,.50]])
    np.testing.assert_array_equal(rack_occlusion_mask(points,t[:3,3],cfg),[False,False])
    assert rack_occlusion_mask(points[:1],t[:3,3],cfg)[0]

def test_deck_holes_are_not_filled_by_a_rectangular_occluder():
    # This ray crosses the deck bounding rectangle through an open edge gap.
    profile,t=setup();origin=t[:3,3];height=rear_deck()[0]
    intersection=np.array([-.395,.10,height]);point=origin+1.2*(intersection-origin)
    cfg={**profile['rack_occlusion'],'preserve_vertical_support':False}
    assert not rack_occlusion_mask(point[None],origin,cfg)[0]

def test_ground_and_bounded_far_shadows_remain_unchanged():
    profile,t=setup();cfg=profile['rack_occlusion']
    x,y=np.meshgrid(np.linspace(-1.5,1.5,301),np.linspace(-1.5,1.5,301))
    ground=np.column_stack([x.ravel(),y.ravel(),np.full(x.size,-.23479)])
    assert not rack_occlusion_mask(ground,t[:3,3],cfg).any()
    p=np.array([[-.47,-.11,.22]])
    assert rack_occlusion_mask(p,t[:3,3],cfg)[0]
    assert not rack_occlusion_mask(p,t[:3,3],{**cfg,'max_lidar_range_m':.6})[0]
    assert not rack_occlusion_mask(p,t[:3,3],{**cfg,'max_behind_m':.1})[0]
    assert not rack_occlusion_mask(p,t[:3,3],{**cfg,'min_behind_m':.4})[0]

@pytest.mark.parametrize('key,value',[('max_lidar_range_m',float('nan')),('support_height_m',0),('min_behind_m',.6)])
def test_invalid_bounds_fail_closed(key,value):
    profile,t=setup()
    with pytest.raises(ValueError):rack_occlusion_mask(np.array([[-.47,-.11,.22]]),t[:3,3],{**profile['rack_occlusion'],key:value})
