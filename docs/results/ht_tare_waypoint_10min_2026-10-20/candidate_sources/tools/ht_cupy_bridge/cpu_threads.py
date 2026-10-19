"""Bound independent CPU pools; PyTorch's thread setting does not cover BLAS."""
from threadpoolctl import threadpool_info, threadpool_limits
import torch


def configure_cpu_threads(pytorch_threads=2):
    # Nx3 surface fits do not benefit from 28 BLAS workers. Their idle spin
    # after each tiny fit otherwise competes with fusion and path planning.
    if not isinstance(pytorch_threads,int) or not 1<=pytorch_threads<=8:
        raise ValueError('pytorch_threads must be an integer from 1 to 8')
    limit = threadpool_limits(limits=1, user_api='blas')
    torch.set_num_threads(pytorch_threads)
    return limit, {'pytorch_threads': torch.get_num_threads(),
                   'blas_pools': [p for p in threadpool_info() if p['user_api'] == 'blas']}
