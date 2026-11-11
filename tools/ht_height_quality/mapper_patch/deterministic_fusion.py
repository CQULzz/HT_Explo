"""Ordered GPU batch fusion and snapshot-based visibility updates.

Point decisions read an immutable prior, never a map modified by another point.
Each cell reduces candidates in original point order with one GPU thread. Rays
then read a separate post-integration snapshot; their events are ordered by
(point index, ray step) and reduced by one thread per cell. No floating atomics
or last-writer-wins upper-bound updates are used. This defines formerly racy
semantics; it is not bitwise equivalent to an arbitrary legacy GPU schedule.
"""
from __future__ import annotations

import math
import numpy as np
import cupy as cp


_SOURCE = r'''
extern "C" {
__device__ int cell_of(float x,float y,float res,int width) {
  int r=(int)(x/res+.5f*width),c=(int)(y/res+.5f*width);
  r=max(0,min(width-1,r));c=max(0,min(width-1,c));return r*width+c;
}
__device__ bool inside(int idx,int width) {
  int r=idx/width,c=idx%width;return r>0&&r<width-1&&c>0&&c<width-1;
}
__device__ bool valid_point(float x,float y,float z,const float* t,const float* q) {
  float dx=x-t[0],dy=y-t[1],dz=z-t[2];
  float distance=dx*dx+dy*dy+dz*dz;
  float ramp=max(sqrtf(x*x+y*y)-q[7],0.f)*q[6]+q[8];
  return isfinite(x)&&isfinite(y)&&isfinite(z)&&distance>=q[4]*q[4]&&dz<=ramp&&dz<=q[5];
}
__global__ void prepare(const float* points,const float* R,const float* t,const float* q,
 const float* prior,int n,int width,float* xyz,float* noise,int* cells,int* flags,float* errors) {
 int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;int m=width*width;
 float a=points[3*i],b=points[3*i+1],c=points[3*i+2];
 float x=R[0]*a+R[1]*b+R[2]*c+t[0];
 float y=R[3]*a+R[4]*b+R[5]*c+t[1];
 float z=R[6]*a+R[7]*b+R[8]*c+t[2];
 xyz[3*i]=x;xyz[3*i+1]=y;xyz[3*i+2]=z;noise[i]=q[1]*c*c;
 cells[i]=m;flags[i]=0;errors[i]=0;
 if(!valid_point(x,y,z,t,q))return;
 flags[i]=1;int idx=cell_of(x,y,q[0],width);
 if(!inside(idx,width))return;
 flags[i]|=2;cells[i]=idx;
 float h=prior[idx],v=prior[m+idx];
 float innovation=fmaxf(v+noise[i],0.f),residual=h-z;
 if(prior[2*m+idx]>.5f&&residual*residual<q[2]*q[2]*innovation&&v<q[9]/2.f&&prior[3*m+idx]>q[10]) {
  flags[i]|=4;errors[i]=z-h;
 }
}
__global__ void ranges(const int* keys,int n,int m,int* starts,int* ends) {
 int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;int c=keys[i];if(c<0||c>=m)return;
 if(i==0||keys[i-1]!=c)starts[c]=i;
 if(i+1==n||keys[i+1]!=c)ends[c]=i+1;
}
__global__ void drift(const float* errors,const int* flags,int n,int enabled,int min_count,
 float position_noise,float orientation_noise,float position_threshold,float orientation_threshold,
 float max_drift,float alpha,double* result) {
 if(blockIdx.x||threadIdx.x)return;double sum=0;int count=0;
 for(int i=0;i<n;++i)if(flags[i]&4){sum+=(double)errors[i];++count;}
 bool eligible=enabled&&count>min_count&&(position_noise>position_threshold||orientation_noise>orientation_threshold);
 double mean=eligible?sum/count:0.;result[0]=mean;result[1]=count;result[2]=eligible;
 result[3]=eligible&&fabs(mean)<max_drift?mean*alpha:0.;
}
__global__ void reduce_points(const float* prior,const float* observed_variance,const float* xyz,const float* noise,const int* flags,
 const long long* order,const int* starts,const int* ends,int m,const float* q,
 float* output,float* newmap) {
 int c=blockIdx.x*blockDim.x+threadIdx.x;if(c>=m)return;
 int start=starts[c],end=ends[c],total=start<0?0:end-start,inliers=0,accepted=0,outliers=0;
 double heights=0,variances=0;float h=prior[c],v=prior[m+c];
 if(start>=0)for(int j=start;j<end;++j)if(flags[order[j]]&4)++inliers;
 if(start>=0)for(int j=start;j<end;++j) {
  long long i=order[j];float z=xyz[3*i+2],measurement=noise[i];
  float residual=h-z,innovation=fmaxf(v+measurement,0.f);
  if(residual*residual>q[2]*q[2]*innovation){++outliers;continue;}
  // The edge tolerance is metric and independent of sampling density.
  // Do not mix standard deviation with variance or divide by point count.
  float edge_v=isfinite(observed_variance[c])?observed_variance[c]:v;
  if(q[11]>.5f&&total>q[12]&&z<h-q[2]*sqrtf(fmaxf(edge_v,0.f)))continue;
  float denominator=v+measurement;
  float nh=denominator>0?(h*measurement+z*v)/denominator:h;
  float nv=denominator>0?v*measurement/denominator:v;
  heights+=(double)nh;variances+=(double)nv;++accepted;
 }
 for(int k=0;k<7;++k){output[k*m+c]=prior[k*m+c];newmap[k*m+c]=0;}
 newmap[c]=(float)heights;newmap[m+c]=(float)variances;newmap[2*m+c]=accepted;
 newmap[3*m+c]=inliers;newmap[4*m+c]=total;
 if(accepted>0) {
  output[c]=(float)(heights/accepted);output[m+c]=(float)(variances/accepted);
  output[2*m+c]=1;output[4*m+c]=0;output[5*m+c]=output[c];output[6*m+c]=0;
  if(output[m+c]>q[17]){output[c]=0;output[m+c]=q[13];output[2*m+c]=0;}
 }else {
  // A conflicting scan is one uncertainty update; duplicating its returns
  // must not linearly amplify a single cell's variance.
  output[m+c]=v+(outliers>0?q[3]:0.f);
  if(prior[2*m+c]<.5f){output[c]=0;output[m+c]=q[13];output[2*m+c]=0;}
 }
}
__global__ void emit_rays(const float* xyz,const int* flags,const float* t,const float* q,
 const float* fixed,const float* normals,const float* newmap,int n,int width,int steps,
 int* cells,float* upper,float* decrement,int* inflation) {
 int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;int m=width*width;
 long long base=(long long)i*steps;
 for(int j=0;j<steps;++j){cells[base+j]=m;upper[base+j]=__int_as_float(0x7f800000);decrement[base+j]=0;inflation[base+j]=0;}
 if(!(flags[i]&1))return;
 float x=xyz[3*i],y=xyz[3*i+1],z=xyz[3*i+2];
 float vx=x-t[0],vy=y-t[1],vz=z-t[2],length=sqrtf(vx*vx+vy*vy+vz*vz);
 if(!isfinite(length)||length<=0)return;
 float rx=vx/length,ry=vy/length,rz=vz/length;
 length=min(length,q[14]);float ray_step=q[0]/sqrtf(2.f);int previous=-1;
 for(int j=0;j<steps;++j) {
  float s=(j+1)*ray_step;if(s>=length)break;
  float nx=t[0]+rx*s,ny=t[1]+ry*s,nz=t[2]+rz*s;
  int c=cell_of(nx,ny,q[0],width);if(c==previous)continue;previous=c;
  if(!inside(c,width))continue;
  float dx=x-nx,dy=y-ny,dz=z-nz;if(dx*dx+dy*dy+dz*dz<.1f)continue;
  long long event=base+j;
  if(fixed[2*m+c]<.5f) {
   if(nz<fixed[5*m+c]||fixed[6*m+c]<.5f){cells[event]=c;upper[event]=nz;}
   continue;
  }
  float age=fixed[4*m+c];if(age<.5f)continue;
  if(fixed[c]<=nz+.01f-min(fixed[m+c],1.f)*.05f)continue;
  float dot=rx*normals[c]+ry*normals[m+c]+rz*normals[2*m+c];
  if(fabsf(dot)<q[15])continue;
  if(newmap[3*m+c]>q[12]&&age<1.f)continue;
  cells[event]=c;decrement[event]=q[16]/(length/q[14]);inflation[event]=1;
  if(nz<fixed[5*m+c]||fixed[6*m+c]<.5f)upper[event]=nz;
 }
}
__global__ void reduce_rays(const float* fixed,const int* starts,const int* ends,
 const long long* order,const float* upper,const float* decrement,const int* inflation,
 int m,const float* q,float* output) {
 int c=blockIdx.x*blockDim.x+threadIdx.x;if(c>=m)return;
 int start=starts[c],end=ends[c];if(start<0)return;
 double clean=0;int count=0;float best=fixed[6*m+c]>.5f?fixed[5*m+c]:__int_as_float(0x7f800000);
 bool bound=false;
 for(int j=start;j<end;++j){long long event=order[j];clean+=(double)decrement[event];count+=inflation[event];
  if(isfinite(upper[event])){best=min(best,upper[event]);bound=true;}}
 if(bound){output[5*m+c]=best;output[6*m+c]=1;}
 if(count>0){output[2*m+c]=(float)((double)fixed[2*m+c]-clean);output[m+c]=fixed[m+c]+count*q[3];
  if(output[2*m+c]<.5f){output[c]=0;output[m+c]=q[13];output[2*m+c]=0;}}
}
__global__ void metadata(const int* cells,const int* flags,int n,int m,float* points) {
 int i=blockIdx.x*blockDim.x+threadIdx.x;if(i>=n)return;
 points[3*i]=cells[i]<m?cells[i]:0;points[3*i+1]=(flags[i]&1)?1:0;points[3*i+2]=(flags[i]&2)?1:0;
}
}
'''


class DeterministicFusion:
    """GPU stable reductions; float32 map storage, ordered float64 sums."""
    def __init__(self, param):
        self.param = param
        self.width = int(param.cell_n)
        self.module = cp.RawModule(code=_SOURCE, options=('--std=c++11',))
        self.kernels = {name:self.module.get_function(name) for name in
                        ('prepare','ranges','drift','reduce_points','emit_rays','reduce_rays','metadata')}

    def _launch(self, name, n, args):
        if n:
            self.kernels[name](((int(n)+127)//128,), (128,), args)

    def _ordered_ranges(self, cells, m):
        # Unique secondary integer key removes any equal-key sorting ambiguity.
        ids=cp.arange(cells.size,dtype=cp.int64)
        order=cp.lexsort(cp.stack((ids,cells)))
        keys=cells[order]
        starts=cp.full(m,-1,dtype=cp.int32);ends=cp.full(m,-1,dtype=cp.int32)
        self._launch('ranges',cells.size,(keys,np.int32(cells.size),np.int32(m),starts,ends))
        return order,starts,ends

    def fuse(self, elevation_map, normal_map, points, R, t, new_map,
             position_noise=0., orientation_noise=0., observation_variance=None):
        p=self.param;n=int(points.shape[0]);m=self.width*self.width
        if elevation_map.dtype!=cp.float32 or normal_map.dtype!=cp.float32:
            raise ValueError('Deterministic fusion currently requires float32 maps')
        if not math.isfinite(float(p.resolution)) or p.resolution<=0 or p.max_ray_length<=0:
            raise ValueError('Deterministic fusion requires positive finite geometry')
        q=cp.asarray([p.resolution,p.sensor_noise_factor,p.mahalanobis_thresh,p.outlier_variance,
            p.min_valid_distance,p.max_height_range,p.ramped_height_range_a,p.ramped_height_range_b,
            p.ramped_height_range_c,p.drift_compensation_variance_inlier,p.traversability_inlier,
            float(p.enable_edge_sharpen),p.wall_num_thresh,p.initial_variance,p.max_ray_length,
            p.cleanup_cos_thresh,p.cleanup_step,p.max_variance],dtype=cp.float32)
        prior=elevation_map.copy();xyz=cp.empty((n,3),cp.float32);noise=cp.empty(n,cp.float32)
        cells=cp.empty(n,cp.int32);flags=cp.empty(n,cp.int32);errors=cp.empty(n,cp.float32)
        packed=cp.ascontiguousarray(points,dtype=cp.float32)
        self._launch('prepare',n,(packed,R,t,q,prior,np.int32(n),np.int32(self.width),xyz,noise,cells,flags,errors))
        stats=cp.zeros(4,dtype=cp.float64)
        self.kernels['drift']((1,),(1,),(errors,flags,np.int32(n),np.int32(p.enable_drift_compensation),
            np.int32(p.min_height_drift_cnt),np.float32(position_noise),np.float32(orientation_noise),
            np.float32(p.position_noise_thresh),np.float32(p.orientation_noise_thresh),np.float32(p.max_drift),
            np.float32(p.drift_compensation_alpha),stats))
        prior[0] += stats[3].astype(cp.float32)
        order,starts,ends=self._ordered_ranges(cells,m)
        observed_v=(prior[1] if observation_variance is None else observation_variance).reshape(-1)
        self._launch('reduce_points',m,(prior,observed_v,xyz,noise,flags,order,starts,ends,np.int32(m),q,elevation_map,new_map))
        if p.enable_visibility_cleanup and n:
            steps=int(math.ceil(float(p.max_ray_length)/(float(p.resolution)/math.sqrt(2))))
            if steps>10000 or n*steps>2**31-1:
                raise ValueError('Visibility event capacity outside deterministic implementation bounds')
            slots=n*steps;ray_cells=cp.empty(slots,cp.int32);upper=cp.empty(slots,cp.float32)
            decrement=cp.empty(slots,cp.float32);inflation=cp.empty(slots,cp.int32)
            fixed=elevation_map.copy()
            self._launch('emit_rays',n,(xyz,flags,t,q,fixed,normal_map,new_map,np.int32(n),
                np.int32(self.width),np.int32(steps),ray_cells,upper,decrement,inflation))
            event_ids=cp.flatnonzero(ray_cells<m).astype(cp.int64,copy=False)
            active_cells=ray_cells[event_ids]
            event_order=cp.lexsort(cp.stack((event_ids,active_cells)));ordered_ids=event_ids[event_order]
            keys=active_cells[event_order];rs=cp.full(m,-1,cp.int32);re=cp.full(m,-1,cp.int32)
            self._launch('ranges',keys.size,(keys,np.int32(keys.size),np.int32(m),rs,re))
            self._launch('reduce_rays',m,(fixed,rs,re,ordered_ids,upper,decrement,inflation,np.int32(m),q,elevation_map))
        self._launch('metadata',n,(cells,flags,np.int32(n),np.int32(m),packed))
        points[...] = packed
        return stats
