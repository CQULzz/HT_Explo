#!/usr/bin/env python3
"""Read-only compute preflight; performs a tiny GPU calculation, no ROS nodes."""
import argparse,json,sys,importlib.util


def main():
    p=argparse.ArgumentParser();p.add_argument('--require-cuda',action='store_true');p.add_argument('--cupy',action='store_true');p.add_argument('--require-numba',action='store_true');a=p.parse_args()
    report={'python':sys.executable,'numba_installed':importlib.util.find_spec('numba') is not None}
    ok=True
    if report['numba_installed']:
        try:
            import numba
            report['numba']=numba.__version__
        except Exception as e:
            report['numba_error']=str(e)
            if a.require_numba:ok=False
    elif a.require_numba:ok=False
    try:
        import torch
        report.update(torch=torch.__version__,torch_cuda_build=torch.version.cuda,cuda_available=torch.cuda.is_available())
        if report['cuda_available']:
            report.update(gpu=torch.cuda.get_device_name(0),compute_capability=list(torch.cuda.get_device_capability(0)))
            x=torch.ones((4,4),device='cuda');value=(x@x).sum().item();torch.cuda.synchronize()
            report['torch_gpu_calculation_passed']=value==64
            ok &= value==64
        elif a.require_cuda:ok=False
    except Exception as e:report['torch_error']=str(e);ok=False
    if a.cupy:
        try:
            import cupy as cp
            report.update(cupy=cp.__version__,cupy_cuda_runtime=cp.cuda.runtime.runtimeGetVersion(),cupy_gpu_calculation_passed=int(cp.arange(16).sum().get())==120)
            ok &= report['cupy_gpu_calculation_passed']
        except Exception as e:report['cupy_error']=str(e);ok=False
    report['requested_checks_passed']=bool(ok);print(json.dumps(report,ensure_ascii=False,indent=2))
    return 0 if ok else 2


if __name__=='__main__':raise SystemExit(main())
