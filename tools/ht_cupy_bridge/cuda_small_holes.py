"""CUDA box-filter moments with the CPU reference's scalar FP64 recurrence.

Only statistics move to CUDA. Eligibility, plane solving, threshold decisions
and connected-component diagnostics stay on the existing NumPy/SciPy path.
CuPy is optional until a CUDA instance is explicitly constructed.
"""
import numpy as np


SOURCE = r'''
__device__ double value(const float* z,const bool* known,int n,int m,
                       int r,int c,int channel,double resolution) {
  if(r<0||r>=n||c<0||c>=m||!known[r*m+c])return 0.0;
  double x=__dmul_rn((double)r,resolution),y=__dmul_rn((double)c,resolution);
  double h=(double)z[r*m+c];
  switch(channel) {
    case 0:return x; case 1:return y; case 2:return h;
    case 3:return __dmul_rn(x,x); case 4:return __dmul_rn(y,y);
    case 5:return __dmul_rn(x,y); case 6:return __dmul_rn(h,x);
    case 7:return __dmul_rn(h,y); default:return __dmul_rn(h,h);
  }
}
extern "C" __global__ void vertical(const float* z,const bool* known,double* out,
                                     int n,int m,int size,double resolution) {
  int i=blockDim.x*blockIdx.x+threadIdx.x;if(i>=9*m)return;
  int channel=i/m,c=i%m,radius=size/2;double sum=0.0;
  for(int r=-radius;r<=radius;++r)
    sum=__dadd_rn(sum,value(z,known,n,m,r,c,channel,resolution));
  out[channel*n*m+c]=__ddiv_rn(sum,(double)size);
  for(int r=1;r<n;++r) {
    double entering=value(z,known,n,m,r+radius,c,channel,resolution);
    double leaving=value(z,known,n,m,r-radius-1,c,channel,resolution);
    sum=__dadd_rn(sum,__dsub_rn(entering,leaving));
    out[channel*n*m+r*m+c]=__ddiv_rn(sum,(double)size);
  }
}
__device__ double column(const double* values,int n,int m,int channel,int r,int c) {
  return c<0||c>=m?0.0:values[channel*n*m+r*m+c];
}
extern "C" __global__ void selected_horizontal(const double* values,const int* starts,
 const int* columns,double* out,int n,int m,int size,int count) {
  int i=blockDim.x*blockIdx.x+threadIdx.x;if(i>=9*n)return;
  int channel=i/n,r=i%n,p=starts[r],end=starts[r+1],radius=size/2;
  if(p==end)return;
  double sum=0.0;
  for(int c=-radius;c<=radius;++c)
    sum=__dadd_rn(sum,column(values,n,m,channel,r,c));
  for(int c=0;p<end;++c) {
    if(c)sum=__dadd_rn(sum,__dsub_rn(column(values,n,m,channel,r,c+radius),
                                   column(values,n,m,channel,r,c-radius-1)));
    while(p<end&&columns[p]==c)out[channel*count+p++]=__ddiv_rn(sum,(double)size);
  }
}
'''


class CudaSmallHoleMoments:
    def __init__(self, device):
        import cupy as cp
        import torch
        if device.type != 'cuda':
            raise ValueError('CUDA hole moments require a CUDA device')
        self.cp, self.torch = cp, torch
        self.device_index = device.index if device.index is not None else torch.cuda.current_device()
        with cp.cuda.Device(self.device_index):
            module = cp.RawModule(code=SOURCE, options=('--std=c++11', '--fmad=false'))
            self.vertical = module.get_function('vertical')
            self.horizontal = module.get_function('selected_horizontal')
        self.self_test_cases = 0
        self._self_check()

    def sample(self, z, known, resolution, size, index):
        """Nine original moments, sampled in sorted row/column index order."""
        z = np.asarray(z, np.float32); known = np.asarray(known, bool)
        rows, columns = (np.asarray(a, np.int64) for a in index)
        if (z.ndim != 2 or known.shape != z.shape or min(z.shape) < 1
                or max(z.shape) > 1024 or not .02 <= resolution <= .1
                or not isinstance(size, (int, np.integer)) or size < 1 or size % 2 != 1
                or rows.ndim != 1 or columns.shape != rows.shape
                or np.any(rows < 0) or np.any(rows >= z.shape[0])
                or np.any(columns < 0) or np.any(columns >= z.shape[1])):
            raise ValueError('Invalid CUDA hole moment geometry')
        if not len(rows):
            return np.empty((9, 0), np.float64)
        if (np.any(np.diff(rows) < 0)
                or np.any((rows[1:] == rows[:-1]) & (columns[1:] < columns[:-1]))):
            raise ValueError('CUDA moment indices must be sorted by row then column')
        n, m = z.shape
        starts = np.r_[0, np.cumsum(np.bincount(rows, minlength=n))].astype(np.int32)
        cp, torch = self.cp, self.torch
        with cp.cuda.Device(self.device_index), cp.cuda.ExternalStream(
                torch.cuda.current_stream(self.device_index).cuda_stream):
            dz = cp.asarray(np.ascontiguousarray(z))
            dk = cp.asarray(np.ascontiguousarray(known))
            vertical = cp.empty((9, n, m), cp.float64)
            output = cp.empty((9, len(rows)), cp.float64)
            counts = (np.int32(n), np.int32(m), np.int32(size))
            self.vertical(((9*m+127)//128,), (128,),
                          (dz, dk, vertical, *counts, np.float64(resolution)))
            self.horizontal(((9*n+127)//128,), (128,),
                            (vertical, cp.asarray(starts),
                             cp.asarray(np.ascontiguousarray(columns, dtype=np.int32)),
                             output, *counts, np.int32(len(rows))))
            return output.get()

    def _self_check(self):
        from scipy.ndimage import uniform_filter
        rng = np.random.default_rng(1101)
        for shape, resolution, size in [((23, 29), .04, 7),
                                       ((19, 17), .04093567251461988, 7),
                                       ((11, 13), .02, 17),
                                       ((291, 291), .04, 7)]:
            z = rng.normal(-.6, .07, shape).astype(np.float32)
            known = rng.random(shape) > .2; z[~known] = np.nan
            index = tuple(a.ravel() for a in np.indices(shape))
            actual = self.sample(z, known, resolution, size, index)
            rr, cc = np.indices(shape); x, y = rr*resolution, cc*resolution
            k = known.astype(np.float64); h = np.where(known, z, 0.).astype(np.float64)
            inputs = [k*x, k*y, h, k*x*x, k*y*y, k*x*y, h*x, h*y, h*h]
            expected = np.array([uniform_filter(a, size=size, mode='constant')[index] for a in inputs])
            if actual.tobytes() != expected.tobytes():
                raise RuntimeError('CUDA hole moments failed exact SciPy startup self-check')
            self.self_test_cases += 1


def create_small_hole_moments(backend, device):
    if backend not in ('auto', 'numpy', 'cuda'):
        raise ValueError('ht_small_hole_fit_backend must be auto, numpy or cuda')
    if backend == 'numpy' or device.type != 'cuda':
        if backend == 'cuda':
            raise ValueError('CUDA hole moments requested with a CPU model')
        return 'numpy', None, {'reason': 'explicit_numpy' if backend == 'numpy' else 'cpu_device'}
    try:
        engine = CudaSmallHoleMoments(device)
        return 'cuda', engine, {'self_test_cases': engine.self_test_cases, 'moment_precision': 'float64'}
    except Exception as error:
        if backend == 'cuda':
            raise
        return 'numpy', None, {'reason': 'cuda_initialization_or_self_check_failed', 'error': str(error)}
