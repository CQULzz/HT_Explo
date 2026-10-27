"""Thread-pool limits must preserve plane selection and HT hard-gate decisions."""
from pathlib import Path
import unittest

import numpy as np
import torch
from threadpoolctl import threadpool_info, threadpool_limits

from cpu_threads import configure_cpu_threads
from local_surface import SurfaceReferenceEstimator
from model import load_student_model


class CpuPoolTest(unittest.TestCase):
    def test_limits_preserve_surface_and_directional_hard_gates(self):
        previous_torch = torch.get_num_threads()
        torch.set_num_threads(2)
        resolution=.04093567251461988
        x,y=np.meshgrid((145-np.arange(291))*resolution,
                        (145-np.arange(291))*resolution,indexing='ij')
        z=(.04*x+.02*y+.1).astype(np.float32)
        z[110:120,140:155] += .8
        variance=np.full(z.shape,.002,np.float32)
        age=np.zeros(z.shape,np.float32)
        model=load_student_model(str(Path(__file__).with_name('student_best_epoch_weights.pth')),torch.device('cpu'))
        def predict():
            ref,stats=SurfaceReferenceEstimator().estimate(z,variance,resolution,age,1.1)
            with torch.inference_mode():
                p=torch.softmax(model(torch.from_numpy((z-ref)[None,None])),dim=2)[0,:,1].numpy()
            return ref,stats,p
        try:
            with threadpool_limits(limits=28,user_api='blas'):
                before=predict()
            limit,metadata=configure_cpu_threads()
            try:
                after=predict()
                self.assertEqual(torch.get_num_threads(),2)
                self.assertTrue(metadata['blas_pools'])
                self.assertTrue(all(p['num_threads']==1 for p in threadpool_info() if p['user_api']=='blas'))
                np.testing.assert_allclose(before[0],after[0],atol=1e-7,rtol=0)
                self.assertEqual(before[1]['plane_fit'],after[1]['plane_fit'])
                # BLAS plane-fit reduction order has FP32-scale propagation into
                # scores (1.1325e-6 on the unchanged ARM64 baseline). Keep the
                # actual >=0.5 decisions below strictly identical.
                np.testing.assert_allclose(before[2],after[2],atol=2e-6,rtol=0)
                np.testing.assert_array_equal(before[2]>=.5,after[2]>=.5)
            finally:
                limit.restore_original_limits()
        finally:
            torch.set_num_threads(previous_torch)


if __name__=='__main__':
    unittest.main()
