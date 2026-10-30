import importlib.util
from pathlib import Path
import numpy as np
import pytest
from scipy.ndimage import distance_transform_edt
from small_hole_kernels import warmup_small_holes,distance_offsets
from small_holes import repair_small_holes
from test_small_holes import fixture


def test_auto_and_explicit_backend_share_prewarmed_kernel():
    assert warmup_small_holes('auto')[1] is warmup_small_holes('numba')[1]


@pytest.mark.parametrize('resolution',[.02,.03,.04,.04093567251461988,.042,.06,.1,
                                         np.nextafter(.04,0),np.nextafter(.04,1)])
def test_candidate_distance_matches_edt_including_edges_and_radius_ties(resolution):
    _,kernel=warmup_small_holes('numba')
    rng=np.random.default_rng(20261031)
    for density in [.001,.1,.5,1.]:
        known=np.ascontiguousarray(rng.random((47,53))<density);known[0,0]=True
        rows,cols=np.indices(known.shape)
        rows=np.ascontiguousarray(rows.ravel());cols=np.ascontiguousarray(cols.ravel())
        actual=kernel(known,rows,cols,distance_offsets(resolution)).reshape(known.shape)
        expected=distance_transform_edt(~known)*resolution<=.12+1e-9
        np.testing.assert_array_equal(actual,expected)


@pytest.mark.parametrize('resolution',[.02,.04,.04093567251461988,.042,.06,.1])
def test_full_repair_exactly_matches_reference_for_random_holes_and_protection(resolution):
    rng=np.random.default_rng(1028)
    for iteration in range(15):
        rows,cols=np.indices((61,61));z=(.1+.05*rows*resolution-.03*cols*resolution).astype(np.float32)
        z[rng.random(z.shape)<.06+iteration*.02]=np.nan
        observed=np.isfinite(z);rejected=rng.random(z.shape)<.005
        obstacles=np.where(rng.random(z.shape)<.003,.6,np.nan).astype(np.float32)
        variance=np.full(z.shape,.001,np.float32);age=np.zeros(z.shape,np.float32)
        current=z.copy();protected=rng.random(z.shape)<.005
        args=[z,observed,rejected,obstacles,current,variance,age]
        before=[v.copy() for v in args]
        a=repair_small_holes(*args,resolution,protected=protected,backend='numpy')
        b=repair_small_holes(*args,resolution,protected=protected,backend='numba')
        np.testing.assert_array_equal(a[0],b[0]);np.testing.assert_array_equal(a[1],b[1]);assert a[2]==b[2]
        for original,after in zip(before,args):np.testing.assert_array_equal(original,after)


def test_readonly_transposed_input_and_no_observation_stay_safe():
    args=list(fixture())
    args=[a.T for a in args]
    for a in args:a.flags.writeable=False
    a=repair_small_holes(*args,.04,backend='numpy');b=repair_small_holes(*args,.04,backend='numba')
    np.testing.assert_array_equal(a[0],b[0]);np.testing.assert_array_equal(a[1],b[1])
    args=[np.full((11,11),np.nan,np.float32),np.zeros((11,11),bool),np.zeros((11,11),bool),
          np.full((11,11),np.nan,np.float32),np.full((11,11),np.nan,np.float32),
          np.full((11,11),.001,np.float32),np.zeros((11,11),np.float32)]
    result,filled,_=repair_small_holes(*args,.04,backend='numba')
    assert not filled.any() and np.isnan(result).all()
