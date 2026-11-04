"""Bounded ray shadows of an actual planar URDF mesh; holes remain holes."""
from functools import lru_cache
from pathlib import Path
import math
import numpy as np


@lru_cache(maxsize=1)
def rear_deck():
    # Vendored, source-indexed triangles from the confirmed rack STL, in
    # base_link. Do not replace the concave surface by its bounding box.
    with np.load(Path(__file__).with_name('data')/'rack_rear_deck.npz',allow_pickle=False) as data:
        triangles=np.array(data['triangles'],np.float64)
    if triangles.shape!=(536,3,3) or not np.isfinite(triangles).all():
        raise ValueError('Invalid URDF rear-deck surface')
    height=float(triangles[0,0,2])
    if not np.allclose(triangles[:,:,2],height,atol=1e-7,rtol=0):
        raise ValueError('Rear-deck surface is not planar')
    a=triangles[:,0,:2];v=triangles[:,1,:2]-a;w=triangles[:,2,:2]-a
    determinant=v[:,0]*w[:,1]-v[:,1]*w[:,0]
    usable=np.abs(determinant)>1e-14
    return height,a[usable],v[usable],w[usable],determinant[usable]


def rack_occlusion_mask(points,origin,config):
    """Remove only bounded, above-ground returns behind actual deck material.

    Removing a return grants no free-space/ground observation. Visible upper
    returns protect external vertical objects, as in the wheel-shadow gate.
    """
    points=np.asarray(points,np.float64);origin=np.asarray(origin,np.float64)
    if (points.ndim!=2 or points.shape[1]!=3 or origin.shape!=(3,)
            or not np.isfinite(points).all() or not np.isfinite(origin).all()):
        raise ValueError('Invalid rack visibility geometry')
    settings={}
    for name in ('max_lidar_range_m','min_behind_m','max_behind_m','ground_z_m',
                 'min_height_above_ground_m','support_radius_m','support_height_m'):
        x=float(config[name])
        if not math.isfinite(x) or (name!='ground_z_m' and x<=0):
            raise ValueError('Invalid rack visibility bound: '+name)
        settings[name]=x
    if settings['min_behind_m']>=settings['max_behind_m']:
        raise ValueError('Invalid rack shadow interval')
    preserve=config.get('preserve_vertical_support',True)
    if not isinstance(preserve,bool):raise ValueError('Invalid rack support switch')
    height,a,v,w,determinant=rear_deck()
    if origin[2]<=height+1e-4:raise ValueError('Lidar must be above the rear-deck surface')
    direction=points-origin;length=np.linalg.norm(direction,axis=1)
    ground_limit=settings['ground_z_m']+settings['min_height_above_ground_m']
    eligible=((length>0)&(length<=settings['max_lidar_range_m'])
              &(points[:,2]>ground_limit)&(points[:,2]<height))
    indices=np.flatnonzero(eligible);result=np.zeros(len(points),bool)
    if not len(indices):return result
    t=(height-origin[2])/direction[indices,2]
    behind=(1-t)*length[indices]
    selected=(t>0)&(t<1)&(behind>=settings['min_behind_m'])&(behind<=settings['max_behind_m'])
    indices=indices[selected];t=t[selected]
    intersections=origin[:2]+t[:,None]*direction[indices,:2]
    # Conservative broad phase only: no triangle can contain a point outside
    # the union's bounds. Most near rays cross the plane beside the rack.
    lower=np.minimum(a,np.minimum(a+v,a+w)).min(axis=0)-1e-9
    upper=np.maximum(a,np.maximum(a+v,a+w)).max(axis=0)+1e-9
    in_bounds=(intersections>=lower).all(axis=1)&(intersections<=upper).all(axis=1)
    indices=indices[in_bounds];intersections=intersections[in_bounds]
    # At most128 rays x536 faces per batch, bounded scratch and no JIT/GPU.
    for start in range(0,len(indices),128):
        delta=intersections[start:start+128,None,:]-a[None,:,:]
        u=(delta[:,:,0]*w[:,1]-delta[:,:,1]*w[:,0])/determinant
        z=(v[:,0]*delta[:,:,1]-v[:,1]*delta[:,:,0])/determinant
        inside=(u>=-1e-10)&(z>=-1e-10)&(u+z<=1+1e-10)
        result[indices[start:start+128]]=inside.any(axis=1)
    if preserve and result.any():
        blocked=np.flatnonzero(result)
        visible=np.flatnonzero(~result&(points[:,2]>ground_limit))
        if len(visible):
            from scipy.spatial import cKDTree
            tree=cKDTree(points[visible,:2])
            neighbours=tree.query_ball_point(points[blocked,:2],r=settings['support_radius_m'])
            for index,nearby in zip(blocked,neighbours):
                if len(nearby) and points[visible[nearby],2].max()-points[index,2]>=settings['support_height_m']:
                    result[index]=False
    return result
