"""Run after the frozen navigation trial; synthetic shapes do not measure accuracy."""
import json
from pathlib import Path
import platform
import sys
import time
import numpy as np
import torch
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/ht_cupy_bridge'))
from model import load_student_model
from cpu_threads import configure_cpu_threads
limit,metadata=configure_cpu_threads(4)
model=load_student_model(str(root/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'),torch.device('cpu'))
model=model.to(memory_format=torch.channels_last)
results=[]
try:
    with torch.inference_mode():
        for nx,ny in [(51,51),(51,83),(83,51),(291,291),(291,341),(341,291)]:
            tensor=torch.zeros((1,1,nx,ny)).contiguous(memory_format=torch.channels_last)
            model(tensor)
            elapsed=[]
            for _ in range(3):
                t=time.perf_counter();logits=model(tensor);elapsed.append(time.perf_counter()-t)
            assert tuple(logits.shape)==(1,8,2,nx-50,ny-50)
            p=torch.softmax(logits,dim=2)
            assert torch.isfinite(p).all() and torch.allclose(p.sum(2),torch.ones_like(p[:,:,0]),atol=1e-6)
            res=.04093567251461988
            for n in (nx,ny):
                source=((n-1)/2-np.arange(n))*res
                output=((n-51)/2-np.arange(n-50))*res
                np.testing.assert_allclose(source[25:-25],output,rtol=0,atol=1e-14)
            results.append(dict(input_xy=[nx,ny],output_shape=list(logits.shape),
                                median_s=float(np.median(elapsed)),min_s=min(elapsed),max_s=max(elapsed)))
        try:model(torch.zeros((1,1,50,50)))
        except RuntimeError:small='RuntimeError: kernel exceeds input; bridge rejects unsupported shape before inference'
        else:raise AssertionError('Unexpected acceptance of undersized model input')
finally:limit.restore_original_limits()
report=dict(note='Synthetic flat inputs: shapes, crop-center mapping and inference timings only; no accuracy labels.',
            cpu=platform.processor(),torch=torch.__version__,thread_pools=metadata,
            resolution_m=.04093567251461988,source_width_m=291*res,output_width_m=241*res,
            receptive_field_m=51*res,half_crop_m=25*res,results=results,undersized=small)
(root/'validation/logic_resolution_2026-10-22/model_resolution.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
