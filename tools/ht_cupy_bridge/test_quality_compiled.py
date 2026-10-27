"""Exact comparisons against the retained NumPy implementation."""
import numpy as np
import pytest
from elevation_quality import preprocess_elevation,ElevationQualityConfig,quality_backend_name
from quality_kernels import AVAILABLE

pytestmark=pytest.mark.skipif(not AVAILABLE,reason='Numba is optional')

def compare(z,v,cfg):
    a=preprocess_elevation(z,v,.04,cfg,backend='numpy')
    b=preprocess_elevation(z,v,.04,cfg,backend='numba')
    for name in ['observed_quality','rejected_mask','edge_mask','height_m']:
        np.testing.assert_array_equal(getattr(a,name),getattr(b,name),err_msg=name)
    for key in a.stats:
        if key!='elapsed_ms':assert a.stats[key]==b.stats[key],key

@pytest.mark.parametrize('radius',[1,2])
@pytest.mark.parametrize('symmetric',[False,True])
def test_random_and_metric_boundaries(radius,symmetric):
    rng=np.random.default_rng(2310)
    cfg=ElevationQualityConfig(radius_cells=radius,sparse_symmetric=symmetric)
    for shape in [(1,1),(1,9),(4,5),(27,31),(291,291)]:
        z=rng.normal(0,.02,shape).astype(np.float32);v=rng.uniform(0,.03,shape).astype(np.float32)
        z[rng.random(shape)<.3]=np.nan;v[rng.random(shape)<.04]=np.inf
        compare(z,v,cfg)
    for level in [.005,.015,.04,.075,.12,.15,.5]:
        for value in [np.nextafter(np.float32(level),np.float32(-np.inf)),np.float32(level),np.nextafter(np.float32(level),np.float32(np.inf))]:
            z=np.zeros((13,15),np.float32);v=np.full_like(z,.01);z[6,7]=value;z[6,8]=value
            compare(z,v,cfg);compare(-z,v,cfg)

@pytest.mark.parametrize('scenario',['holes','ramp','step','post','isolated','variance','unknown'])
def test_terrain_and_invalid_data(scenario):
    ii,jj=np.indices((41,45));z=np.zeros((41,45),np.float32);v=np.full_like(z,.01)
    if scenario=='holes':z[12:27,14:29]=np.nan
    if scenario=='ramp':z=(ii*.002+jj*.001).astype(np.float32)
    if scenario=='step':z[:,23:]=.15
    if scenario=='post':z[20:22,20:22]=.2;v[20:22,20:22]=1e-5
    if scenario=='isolated':z[20,22]=.5;z[8,8]=-.5
    if scenario=='variance':v[:5]=-1;v[5:10]=np.nan;v[10:15]=np.inf;v[15:20]=.25;v[20:25]=np.nextafter(np.float32(.25),np.float32(np.inf))
    if scenario=='unknown':z[:]=np.nan
    compare(z,v,ElevationQualityConfig())
    compare(z.T,v.T,ElevationQualityConfig())

def test_explicit_numpy_and_unknown_backend():
    assert quality_backend_name('numpy')=='numpy'
    with pytest.raises(ValueError):quality_backend_name('other')


def test_missing_optional_numba_uses_reference(monkeypatch):
    import quality_kernels
    monkeypatch.setattr(quality_kernels,'AVAILABLE',False)
    assert quality_backend_name('auto')=='numpy'
    with pytest.raises(RuntimeError):quality_backend_name('numba')
    z=np.zeros((7,7),np.float32);v=np.full_like(z,.01)
    np.testing.assert_array_equal(preprocess_elevation(z,v,.04).height_m,
                                  preprocess_elevation(z,v,.04,backend='numpy').height_m)
