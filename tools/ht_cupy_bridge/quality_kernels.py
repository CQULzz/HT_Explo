"""Optional compiled mask calculation. No fastmath or changed metric gates."""
import numpy as np
try:
    from numba import njit
    AVAILABLE=True
except ImportError:
    AVAILABLE=False
    def njit(*args,**kwargs):return lambda function:function

@njit(cache=True,fastmath=False)
def isolated_mask(height,variance,observed,jump,far_jump,spread,uncertain,min_neighbors):
    rows,cols=height.shape;out=np.zeros(height.shape,np.bool_)
    for i in range(rows):
        for j in range(cols):
            if not observed[i,j] or variance[i,j]<uncertain:continue
            center=height[i,j];count=0;close=0;far=0
            lo=np.float32(np.inf);hi=np.float32(-np.inf)
            for dx in range(-1,2):
                for dy in range(-1,2):
                    if dx==0 and dy==0:continue
                    r=i+dx;c=j+dy
                    if r<0 or r>=rows or c<0 or c>=cols:continue
                    value=height[r,c]
                    if not np.isfinite(value):continue
                    count+=1;difference=abs(np.float32(value-center))
                    if difference<jump:close+=1
                    if difference>=far_jump:far+=1
                    lo=min(lo,value);hi=max(hi,value)
            out[i,j]=(count>=min_neighbors and far==count and close==0 and np.float32(hi-lo)<=spread)
    return out

@njit(cache=True,fastmath=False)
def neighborhood_masks(height,observed,radius,symmetric,jump,match,small_jump):
    rows,cols=height.shape
    edge=np.zeros(height.shape,np.bool_);full=np.zeros(height.shape,np.bool_)
    small=np.zeros(height.shape,np.bool_);balanced=np.zeros(height.shape,np.uint8)
    for i in range(rows):
        for j in range(cols):
            if not observed[i,j]:continue
            center=height[i,j];all_known=True;count=0;boundary=False
            for dx in range(-radius,radius+1):
                for dy in range(-radius,radius+1):
                    r=i+dx;c=j+dy
                    known=(r>=0 and r<rows and c>=0 and c<cols)
                    if known:known=np.isfinite(height[r,c])
                    if not known:all_known=False;continue
                    if abs(np.float32(height[r,c]-center))>=jump:boundary=True
                    paired=True
                    if symmetric and radius==1:
                        r=i-dx;c=j-dy
                        paired=(r>=0 and r<rows and c>=0 and c<cols)
                        if paired:paired=np.isfinite(height[r,c])
                    if paired:count+=1
            feature=False
            for dx,dy in ((1,0),(0,1),(1,1),(1,-1)):
                a=i+dx;b=j+dy;c=i-dx;d=j-dy
                if a<0 or a>=rows or b<0 or b>=cols or c<0 or c>=rows or d<0 or d>=cols:continue
                plus=height[a,b];minus=height[c,d]
                if not np.isfinite(plus) or not np.isfinite(minus):continue
                dp=abs(np.float32(plus-center));dm=abs(np.float32(minus-center))
                if (dp<=match and dm>=small_jump) or (dm<=match and dp>=small_jump):feature=True
            full[i,j]=all_known;balanced[i,j]=count;small[i,j]=feature;edge[i,j]=boundary or feature
    return edge,full,balanced,small
