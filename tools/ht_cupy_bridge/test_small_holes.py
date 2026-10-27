import numpy as np
import pytest
from small_holes import repair_small_holes


def fixture():
    rr,cc=np.indices((61,61));z=(.1+.12*rr*.04-.06*cc*.04).astype(np.float32)
    observed=np.ones(z.shape,bool);observed[29:32,29:32]=False
    z[~observed]=np.nan
    return z,observed,np.zeros_like(observed),np.full_like(z,np.nan),z.copy(),np.full_like(z,.001),np.zeros_like(z)

def test_small_enclosed_planar_gap_and_immutability():
    args=fixture();before=[v.copy() for v in args]
    z,mask,s=repair_small_holes(*args,.04)
    assert mask.sum()==9 and s['filled_components']==1
    assert np.isfinite(z).all()
    rr,cc=np.indices(z.shape);np.testing.assert_allclose(z,.1+.12*rr*.04-.06*cc*.04,atol=2e-7)
    for a,b in zip(args,before):np.testing.assert_array_equal(a,b)
    np.testing.assert_array_equal(z[~mask],args[0][~mask])

@pytest.mark.parametrize('case',['large','edge','stale','uncertain','obstacle','negative_step','positive_step','small_negative_step','small_positive_step','source_changed','variance','slope'])
def test_unsafe_or_unsupported_gaps_remain_unknown(case):
    a=list(fixture());z,obs,reject,obstacle,current,var,age=a
    if case=='large':z[26:35,26:35]=np.nan;obs[26:35,26:35]=False;current[:]=z
    if case=='edge':z[:32,29:32]=np.nan;obs[:32,29:32]=False;current[:]=z
    if case=='stale':age[:]=3.
    if case=='uncertain':reject[30,30]=True
    if case=='obstacle':obstacle[28,30]=.7
    if case in ('negative_step','positive_step','small_negative_step','small_positive_step'):
        jump=.03 if case.startswith('small_') else .15
        z[32:,:]+=-jump if 'negative' in case else jump;current[:]=z
    if case=='source_changed':current[27,30]+=.1
    if case=='variance':var[:]=.3
    if case=='slope':
        rr,cc=np.indices(z.shape);z[np.isfinite(z)]+=(rr*.04)[np.isfinite(z)];current[:]=z
    result,filled,_=repair_small_holes(*a,.04)
    if case=='edge':
        assert not filled[0,30] and np.isnan(result[0,30])
        np.testing.assert_array_equal(result[np.isfinite(z)],z[np.isfinite(z)])
    else:
        assert not filled.any();np.testing.assert_array_equal(result,z)

def test_real_observed_negative_feature_is_never_erased():
    a=list(fixture());a[0][30,30]=-.3;a[1][30,30]=True;a[4][:]=a[0]
    result,filled,_=repair_small_holes(*a,.04)
    assert result[30,30]==np.float32(-.3) and not filled.any()

def test_open_narrow_scan_strip_fills_only_between_four_supported_quadrants():
    rr,cc=np.indices((61,61));z=(.1+.1*rr*.04).astype(np.float32)
    z[29:32,:]=np.nan;obs=np.isfinite(z)
    result,filled,_=repair_small_holes(z,obs,np.zeros_like(obs),np.full_like(z,np.nan),z.copy(),np.full_like(z,.001),np.zeros_like(z),.04)
    assert filled[30,30] and not filled[30,0]
    assert result[30,30]==np.float32(.22)

def test_protected_feature_and_wide_open_strip_are_not_bridged():
    z=np.zeros((61,61),np.float32);z[26:35,:]=np.nan;obs=np.isfinite(z)
    result,filled,_=repair_small_holes(z,obs,np.zeros_like(obs),np.full_like(z,np.nan),z.copy(),np.full_like(z,.001),np.zeros_like(z),.04)
    assert not filled[30,30] and np.isnan(result[30,30])
    z=np.zeros((61,61),np.float32);z[29:32,:]=np.nan;obs=np.isfinite(z)
    protected=np.zeros_like(obs);protected[28,30]=True
    _,filled,_=repair_small_holes(z,obs,np.zeros_like(obs),np.full_like(z,np.nan),z.copy(),np.full_like(z,.001),np.zeros_like(z),.04,protected=protected)
    assert not filled[30,30]


def test_mapper_absolute_variance_does_not_replace_local_planarity_check():
    a=list(fixture());a[5][:]=.01
    _,filled,_=repair_small_holes(*a,.04)
    assert filled.sum()==9
