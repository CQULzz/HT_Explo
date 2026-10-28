"""Boundary and collateral-removal regressions for XY-only filter dilation."""
from copy import deepcopy
import numpy as np
import pytest
from ht_scout_bridge.geometry import self_filter_keep_mask


def profile(padding):
    return dict(enabled=True,frame='base_link',horizontal_padding_m=padding,
        boxes=[dict(min_xyz=[-.48,-.21,-.12],max_xyz=[.48,.21,.12])],
        cylinders=[dict(center_xyz=[-.249,-.29153,-.0702],radius=.18459,half_length=.078265,axis='y')])


def test_horizontal_dilation_removes_side_return_without_expanding_below_wheels():
    pts=np.array([[-.249,-.56,-.19],[-.249,-.56,-.26],[-.249,-.56,.12],
                  [0,0,-.23479],[.8,.8,-.19]])
    np.testing.assert_array_equal(self_filter_keep_mask(pts,profile(0),np.eye(4)),[True]*5)
    np.testing.assert_array_equal(self_filter_keep_mask(pts,profile(.2),np.eye(4)),[False,True,True,True,True])


def test_actual_small_obstacle_in_enlarged_region_is_also_removed_and_must_be_reported():
    # A broad filter cannot distinguish self from an external small object.
    pts=np.array([[-.249,-.55,-.17]])
    assert self_filter_keep_mask(pts,profile(0),np.eye(4))[0]
    assert not self_filter_keep_mask(pts,profile(.2),np.eye(4))[0]


@pytest.mark.parametrize('value',[-.01,float('nan'),float('inf')])
def test_invalid_padding_refused(value):
    with pytest.raises(ValueError):self_filter_keep_mask(np.zeros((1,3)),profile(value),np.eye(4))


def test_zero_padding_matches_existing_union_and_does_not_mutate_profile():
    p=profile(0);original=deepcopy(p);pts=np.random.default_rng(81).uniform(-1,1,(50000,3));inside=np.zeros(len(pts),bool)
    for b in p['boxes']:inside|=(pts>=b['min_xyz']).all(1)&(pts<=b['max_xyz']).all(1)
    for c in p['cylinders']:
        d=pts-c['center_xyz'];inside|=(d[:,0]**2+d[:,2]**2<=c['radius']**2)&(abs(d[:,1])<=c['half_length'])
    np.testing.assert_array_equal(self_filter_keep_mask(pts,p,np.eye(4)),~inside)
    assert p==original
