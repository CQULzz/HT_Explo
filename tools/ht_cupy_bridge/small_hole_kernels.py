"""Exact bounded-distance checks at already eligible gap pixels only."""
from functools import lru_cache
import warnings
import numpy as np


def _near_known(known,rows,columns,offsets):
    result=np.zeros(len(rows),np.bool_)
    n,m=known.shape
    for k in range(len(rows)):
        for j in range(len(offsets)):
            r,c=rows[k]+offsets[j,0],columns[k]+offsets[j,1]
            if 0<=r<n and 0<=c<m and known[r,c]:
                result[k]=True
                break
    return result


@lru_cache(maxsize=32)
def distance_offsets(resolution):
    radius=int(np.ceil((.12+1e-9)/resolution))
    offsets=np.array([(r,c) for r in range(-radius,radius+1) for c in range(-radius,radius+1)
                      if np.sqrt(float(r*r+c*c))*resolution<=.12+1e-9],np.int64).reshape(-1,2)
    offsets.flags.writeable=False
    return offsets


@lru_cache(maxsize=3)
def warmup_small_holes(backend='auto'):
    if backend not in ('auto','numpy','numba'):raise ValueError('Unknown small-hole backend')
    if backend=='numpy':return 'numpy',None
    try:
        return 'numba',_compiled_selector()
    except Exception as exc:
        if backend=='numba':raise RuntimeError('Compiled small-hole backend unavailable') from exc
        warnings.warn(f'Compiled small-hole checks unavailable; using reference: {exc}',RuntimeWarning)
        return 'numpy',None


@lru_cache(maxsize=1)
def _compiled_selector():
    from numba import njit
    kernel=njit(cache=True,fastmath=False)(_near_known)
    kernel(np.ones((5,5),np.bool_),np.array([2],np.int64),np.array([2],np.int64),distance_offsets(.04))
    return kernel
