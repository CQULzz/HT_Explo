from pathlib import Path
import numpy as np
import pytest
import torch
import cuda_small_holes as module
from small_holes import repair_small_holes


@pytest.fixture(scope='module')
def engine():
    if not torch.cuda.is_available():pytest.skip('CUDA hardware required')
    return module.CudaSmallHoleMoments(torch.device('cuda'))


@pytest.mark.parametrize('profile',['strict','moderate'])
@pytest.mark.parametrize('resolution',[.02,.04,.04093567251461988,.06,.1])
def test_gpu_moments_preserve_entire_repair_and_never_mutate_inputs(engine,profile,resolution):
    rng=np.random.default_rng(1102)
    for noise in [0.,.002,.008,.015]:
        r,c=np.indices((63,67));z=(-.6+.07*r*resolution-.03*c*resolution+rng.normal(0,noise,r.shape)).astype(np.float32)
        z[rng.random(z.shape)<.18]=np.nan
        observed=np.isfinite(z);rejected=rng.random(z.shape)<.001
        obstacles=np.where(rng.random(z.shape)<.0005,.4,np.nan).astype(np.float32)
        variance=np.full(z.shape,.001,np.float32);age=np.zeros(z.shape,np.float32)
        age[:5]=2.001;age[-3:]=-.002;variance[:, :3]=.251
        protected=rng.random(z.shape)<.001
        arrays=[z,observed,rejected,obstacles,z.copy(),variance,age];before=[a.copy() for a in arrays]
        a=repair_small_holes(*arrays,resolution,protected=protected,profile=profile,backend='numba')
        b=repair_small_holes(*arrays,resolution,protected=protected,profile=profile,backend='numba',moment_provider=engine)
        assert a[0].tobytes()==b[0].tobytes()
        np.testing.assert_array_equal(a[1],b[1]);assert a[2]==b[2]
        for x,y in zip(arrays,before):np.testing.assert_array_equal(x,y)


def test_gpu_repair_preserves_readonly_strides_and_empty_query(engine):
    r,c=np.indices((41,43));z=(.1+.002*r-.001*c).astype(np.float32);z[18:21,20:23]=np.nan
    arrays=[z,np.isfinite(z),np.zeros(z.shape,bool),np.full(z.shape,np.nan,np.float32),z.copy(),np.full(z.shape,.001,np.float32),np.zeros(z.shape,np.float32)]
    arrays=[a.T for a in arrays]
    for a in arrays:a.flags.writeable=False
    old=repair_small_holes(*arrays,.04,profile='moderate',backend='numba')
    new=repair_small_holes(*arrays,.04,profile='moderate',backend='numba',moment_provider=engine)
    assert old[0].tobytes()==new[0].tobytes();assert old[2]==new[2]
    assert engine.sample(arrays[0],arrays[1],.04,7,(np.array([],int),np.array([],int))).shape==(9,0)


def test_auto_fallback_and_explicit_failure_are_distinct(monkeypatch):
    class Broken:
        def __init__(self,device):raise RuntimeError('deliberate self-check failure')
    monkeypatch.setattr(module,'CudaSmallHoleMoments',Broken)
    name,obj,details=module.create_small_hole_moments('auto',torch.device('cuda'))
    assert name=='numpy' and obj is None and 'self-check failure' in details['error']
    with pytest.raises(RuntimeError):module.create_small_hole_moments('cuda',torch.device('cuda'))


def test_cpu_auto_has_no_cuda_instance_and_invalid_backend_is_rejected():
    name,obj,_=module.create_small_hole_moments('auto',torch.device('cpu'));assert name=='numpy' and obj is None
    with pytest.raises(ValueError):module.create_small_hole_moments('cuda',torch.device('cpu'))
    with pytest.raises(ValueError):module.create_small_hole_moments('fast',torch.device('cpu'))
