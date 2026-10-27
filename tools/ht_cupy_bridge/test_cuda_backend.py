"""Numerical parity for the same FP32 checkpoint on CPU and CUDA."""
from pathlib import Path
import numpy as np
import pytest
import torch
from model import load_student_model
from cpu_threads import configure_cpu_threads

@pytest.mark.skipif(not torch.cuda.is_available(),reason='CUDA hardware required')
@pytest.mark.parametrize('channels_last',[False,True])
def test_cuda_matches_cpu_fp32(channels_last):
    configure_cpu_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    weight=str(Path(__file__).with_name('student_best_epoch_weights.pth'))
    cpu=load_student_model(weight,torch.device('cpu')).to(memory_format=torch.channels_last)
    layout=torch.channels_last if channels_last else torch.contiguous_format
    gpu=load_student_model(weight,torch.device('cuda')).to(memory_format=layout)
    rng=np.random.default_rng(2301)
    h=rng.normal(0,.02,(1,1,291,291)).astype(np.float32)
    h[:,:,:,140:]+=np.float32(.15)
    x=torch.from_numpy(h).contiguous(memory_format=torch.channels_last)
    with torch.inference_mode():
        a=torch.softmax(cpu(x),dim=2).numpy()
        b=torch.softmax(gpu(x.to('cuda').contiguous(memory_format=layout)),dim=2).cpu().numpy()
    assert a.shape==(1,8,2,241,241)
    np.testing.assert_allclose(a,b,rtol=2e-4,atol=2e-5)
