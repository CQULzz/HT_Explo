import numpy as np
import pytest
import torch
from ht_support import prepare_ht_context
from cuda_ht_context import CudaHtContext

pytestmark=pytest.mark.skipif(not torch.cuda.is_available(),reason='CUDA hardware required')

def test_cuda_matches_scipy_ties_masks_and_interpolated_input():
    gpu=CudaHtContext(torch.device('cuda'));rng=np.random.default_rng(3125)
    for i in range(42):
        shape=(91,91) if i<30 else (291,291)
        z=rng.normal(0,.12,shape).astype(np.float32)
        observed=rng.random(shape)<[0.,.01,.2,.95,1.][i%5]
        z[~observed]=np.nan
        obstacle=np.where(rng.random(shape)<(.01 if i%4 else 0),np.float32(.8),np.nan)
        rejected=rng.random(shape)<(.001 if i%3 else 0)
        inferred=(~observed)&(rng.random(shape)<.01);filled=np.zeros(shape,np.float32)
        resolution=[.02,.04,.041,.1][i%4]
        height,support,occupied,physical=prepare_ht_context(z,observed,rejected,obstacle,resolution)
        height[inferred]=filled[inferred]
        result=gpu.prepare(z,observed,rejected,obstacle,resolution,inferred,filled)
        np.testing.assert_array_equal(result[0].cpu().numpy(),height)
        for actual,expected in zip(result[1:],(support,occupied,physical)):
            np.testing.assert_array_equal(actual,expected)

def test_cuda_context_uses_current_torch_stream_and_owns_each_result():
    gpu=CudaHtContext(torch.device('cuda'));z=np.zeros((91,91),np.float32)
    ones=np.ones_like(z,bool);zeros=~ones;obstacle=np.full_like(z,np.nan)
    stream=torch.cuda.Stream()
    with torch.cuda.stream(stream):
        first=gpu.prepare(z,ones,zeros,obstacle,.041,zeros,z)[0]
        second=gpu.prepare(z+1,ones,zeros,obstacle,.041,zeros,z)[0]
        result=first+second
    stream.synchronize()
    assert torch.all(first==0) and torch.all(second==1) and torch.all(result==1)

def test_cuda_context_rejects_cpu_and_bad_geometry():
    with pytest.raises(ValueError):CudaHtContext(torch.device('cpu'))
    gpu=CudaHtContext(torch.device('cuda'))
    z=np.zeros((10,10),np.float32);mask=z.astype(bool)
    with pytest.raises(ValueError):gpu.prepare(z,mask,mask,z,.041,mask,z)
