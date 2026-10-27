"""Fold inference BN without changing the checkpoint or model semantics."""
from pathlib import Path
import numpy as np
import pytest
import torch
from model import load_student_model, fuse_student_for_inference


@pytest.fixture(scope='module')
def models():
    torch.set_num_threads(4)
    original=load_student_model(str(Path(__file__).with_name('student_best_epoch_weights.pth')),torch.device('cpu'))
    return original,fuse_student_for_inference(original)


@pytest.mark.parametrize('scene',['flat','step','slope'])
def test_actual_weights_keep_eight_direction_probabilities_within_fp32_tolerance(models,scene):
    original,fused=models
    x=np.zeros((1,1,291,291),np.float32)
    if scene=='step':x[:,:,:,145:]=.15
    if scene=='slope':x[:]=np.arange(291,dtype=np.float32)[None,None,:,None]*.004
    before={k:v.clone() for k,v in original.state_dict().items()}
    with torch.inference_mode():
        ref=torch.softmax(original(torch.from_numpy(x)),dim=2)
        result=torch.softmax(fused(torch.from_numpy(x)),dim=2)
    torch.testing.assert_close(result,ref,atol=1e-5,rtol=1e-5)
    assert result.shape==(1,8,2,241,241)
    assert not any(isinstance(m,torch.nn.BatchNorm2d) for m in fused.modules())
    for k,v in original.state_dict().items():assert torch.equal(v,before[k])


def test_training_statistics_cannot_be_folded(models):
    original,_=models
    original.train()
    try:
        with pytest.raises(ValueError):fuse_student_for_inference(original)
    finally:original.eval()
