"""CUDA context preparation with SciPy's column-then-row nearest-point ties.

The height tensor stays on the current PyTorch CUDA stream through DLPack.
Only the three small, published support masks return to the CPU.
"""
import numpy as np

SOURCE=r'''
extern "C" __global__ void vertical(const bool* observed,const float* obstacle,int* nearest,int n,int m) {
  int c=blockDim.x*blockIdx.x+threadIdx.x;if(c>=m)return;
  int last=-1;
  for(int r=0;r<n;++r){int i=r*m+c;if(observed[i]||isfinite(obstacle[i]))last=r;nearest[i]=last;}
  last=-1;
  for(int r=n-1;r>=0;--r){int i=r*m+c;if(observed[i]||isfinite(obstacle[i]))last=r;
    int old=nearest[i];if(last>=0&&(old<0||last-r<r-old))nearest[i]=last;}
}
extern "C" __global__ void horizontal(const float* z,const float* obstacle,const bool* rejected,
  const int* nearest,const bool* inferred,const float* filled,float* height,bool* near,bool* uncertain,
  int n,int m,double resolution) {
  int i=blockDim.x*blockIdx.x+threadIdx.x;if(i>=n*m)return;
  int r=i/m,c=i%m,best=2147483647,br=-1,bc=0;
  // SciPy resolves equal distances by smaller column, then smaller row.
  for(int q=0;q<m;++q){int v=nearest[r*m+q];if(v<0)continue;
    int dr=v-r,dc=q-c,d=dr*dr+dc*dc;if(d<best){best=d;br=v;bc=q;}}
  if(br<0){br=n-1;bc=0;best=(r+1)*(r+1)+c*c;}
  int j=br*m+bc;
  height[i]=inferred[i]?filled[i]:(isfinite(obstacle[j])?obstacle[j]:z[j]);
  near[i]=sqrt((double)best)*resolution<=.25;
  uncertain[i]=rejected[i]&&!isfinite(obstacle[i]);
}
extern "C" __global__ void vertical_support(const bool* near,const bool* uncertain,
  float* average,bool* veto,int n,int m) {
  int i=blockDim.x*blockIdx.x+threadIdx.x;if(i>=n*m)return;
  int r=i/m,c=i%m,count=0;bool bad=false;
  for(int q=max(0,r-25);q<=min(n-1,r+25);++q){count+=near[q*m+c];bad|=uncertain[q*m+c];}
  average[i]=(float)((double)count/51.0);veto[i]=bad;
}
extern "C" __global__ void horizontal_support(const float* average,const bool* veto,
  bool* support,int n,int m) {
  int i=blockDim.x*blockIdx.x+threadIdx.x;if(i>=n*m)return;
  int r=i/m,c=i%m;double sum=0;bool bad=false;
  for(int q=max(0,c-25);q<=min(m-1,c+25);++q){sum+=(double)average[r*m+q];bad|=veto[r*m+q];}
  support[i]=((float)(sum/51.0)>=.9f)&&!bad;
}
'''


class CudaHtContext:
    def __init__(self,device):
        import cupy as cp
        import torch
        if device.type!='cuda':raise ValueError('CUDA context requires a CUDA model')
        self.cp,self.torch=cp,torch
        self.device_index=device.index if device.index is not None else torch.cuda.current_device()
        with cp.cuda.Device(self.device_index):
            module=cp.RawModule(code=SOURCE,options=('--std=c++11','--fmad=false'))
            self.kernels=[module.get_function(n) for n in ['vertical','horizontal','vertical_support','horizontal_support']]
        z=np.zeros((291,291),np.float32);mask=np.ones(z.shape,bool)
        self.prepare(z,mask,~mask,np.full_like(z,np.nan),.041,~mask,z)

    def prepare(self,elevation,observed,rejected,obstacle,resolution,inferred,filled):
        cp,torch=self.cp,self.torch
        z=np.asarray(elevation,np.float32);n,m=z.shape
        if min(n,m)<51 or max(n,m)>1024 or not .02<=resolution<=.1:
            raise ValueError('Unsupported CUDA context geometry')
        if any(np.shape(a)!=z.shape for a in (observed,rejected,obstacle,inferred,filled)):
            raise ValueError('CUDA context arrays must share geometry')
        with cp.cuda.Device(self.device_index),cp.cuda.ExternalStream(torch.cuda.current_stream(self.device_index).cuda_stream):
            dz,do,dr,db,di,df=[cp.asarray(np.ascontiguousarray(a,dtype=t)) for a,t in
                [(z,np.float32),(observed,bool),(rejected,bool),(obstacle,np.float32),(inferred,bool),(filled,np.float32)]]
            nearest=cp.empty((n,m),cp.int32);height=cp.empty((n,m),cp.float32)
            near=cp.empty((n,m),cp.bool_);uncertain=cp.empty_like(near)
            average=cp.empty((n,m),cp.float32);veto=cp.empty_like(near);support=cp.empty_like(near)
            sizes=(np.int32(n),np.int32(m));grid=((n*m+255)//256,)
            self.kernels[0](((m+127)//128,),(128,),(do,db,nearest,*sizes))
            self.kernels[1](grid,(256,),(dz,db,dr,nearest,di,df,height,near,uncertain,*sizes,np.float64(resolution)))
            self.kernels[2](grid,(256,),(near,uncertain,average,veto,*sizes))
            self.kernels[3](grid,(256,),(average,veto,support,*sizes))
            crop=(slice(25,-25),slice(25,-25))
            masks=[a[crop].get() for a in (support,cp.isfinite(db),near&~uncertain)]
            tensor=torch.from_dlpack(height)
        return tensor,*masks
