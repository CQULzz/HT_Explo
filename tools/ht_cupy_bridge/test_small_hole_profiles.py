import numpy as np
import pytest
from small_holes import repair_small_holes
from small_hole_kernels import distance_offsets,warmup_small_holes
from scipy.ndimage import distance_transform_edt
from test_small_holes import fixture


def test_moderate_fills_more_of_a_planar_gap_and_preserves_measurements():
    z=np.zeros((61,61),np.float32);z[28:33,28:33]=np.nan;obs=np.isfinite(z)
    args=(z,obs,np.zeros_like(obs),np.full_like(z,np.nan),z.copy(),np.full_like(z,.001),np.zeros_like(z),.041)
    strict,sm,_=repair_small_holes(*args,profile='strict')
    moderate,mm,_=repair_small_holes(*args,profile='moderate')
    assert not sm[30,30] and mm[30,30] and mm.sum()>sm.sum()
    assert np.all(mm[sm]);np.testing.assert_array_equal(moderate[sm],strict[sm])
    np.testing.assert_array_equal(moderate[obs],z[obs])
    assert np.isnan(z[30,30]) and not obs[30,30]


@pytest.mark.parametrize('case',['large','obstacle','protected','stale','variance','step','negative_feature'])
def test_moderate_keeps_large_blind_center_and_observed_hazard_vetoes(case):
    a=list(fixture());protected=np.zeros_like(a[1])
    if case=='large':a[0][20:41,20:41]=np.nan;a[1][20:41,20:41]=False;a[4][:]=a[0]
    if case=='obstacle':a[3][28,30]=.7
    if case=='protected':protected[28,30]=True
    if case=='stale':a[6][:]=3.
    if case=='variance':a[5][:]=.3
    if case=='step':a[0][32:]-=.03;a[4][:]=a[0]
    if case=='negative_feature':a[0][30,30]=-.3;a[1][30,30]=True;a[4][:]=a[0]
    result,filled,_=repair_small_holes(*a,.04,profile='moderate',protected=protected)
    assert not filled[30,30]
    if case not in ('large',):assert not filled.any()
    np.testing.assert_array_equal(result[np.isfinite(a[0])],a[0][np.isfinite(a[0])])


def test_profiles_keep_old_fills_exact_and_numpy_numba_agree():
    rng=np.random.default_rng(1031)
    for i in range(32):
        a=list(fixture());holes=rng.random(a[0].shape)<.08+i*.01;a[0][holes]=np.nan;a[1][holes]=False;a[4][:]=a[0]
        a[2][:]=rng.random(a[0].shape)<.001
        old=repair_small_holes(*a,.04,profile='strict')
        new=repair_small_holes(*a,.04,profile='moderate',backend='numpy')
        compiled=repair_small_holes(*a,.04,profile='moderate',backend='numba')
        assert np.all(new[1][old[1]])
        np.testing.assert_array_equal(new[0][old[1]],old[0][old[1]])
        np.testing.assert_array_equal(new[0],compiled[0]);np.testing.assert_array_equal(new[1],compiled[1])


@pytest.mark.parametrize('resolution',[.02,.04,.04093567251461988,.1])
def test_relaxed_distance_kernel_matches_euclidean_reference(resolution):
    rng=np.random.default_rng(18);known=np.ascontiguousarray(rng.random((47,53))<.02);known[0,0]=True
    rr,cc=np.indices(known.shape);kernel=warmup_small_holes('numba')[1]
    result=kernel(known,np.ascontiguousarray(rr.ravel()),np.ascontiguousarray(cc.ravel()),distance_offsets(resolution,.18))
    np.testing.assert_array_equal(result.reshape(known.shape),distance_transform_edt(~known)*resolution<=.18+1e-9)


def test_unknown_profile_is_rejected():
    with pytest.raises(ValueError):repair_small_holes(*fixture(),.04,profile='unbounded')
