#!/usr/bin/env python3
"""Offline ground-truth checks; never used to authorize online motion."""
import argparse,json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np

ap=argparse.ArgumentParser()
ap.add_argument('mesh',type=Path,help='actual simulator indoor/meshes/indoor.dae')
a=ap.parse_args()
r=ET.parse(a.mesh).getroot(); ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
mesh=r.find('.//c:geometry/c:mesh',ns)
position_source=next(s for s in mesh.findall('c:source',ns)
                     if 'position' in s.attrib.get('id','').lower())
pos=np.fromstring(position_source.find('c:float_array',ns).text,sep=' ').reshape(-1,3)
triangles=[]
for sub in mesh.findall('c:triangles',ns):
    stride=max(int(i.attrib.get('offset','0')) for i in sub.findall('c:input',ns))+1
    ids=np.fromstring(sub.find('c:p',ns).text,sep=' ',dtype=int).reshape(-1,3,stride)[:,:,0]
    triangles.append(pos[ids])
t=np.vstack(triangles)
near=t[(t[:,:,0].min(1)<7)&(t[:,:,0].max(1)>-2)&
       (t[:,:,1].min(1)<16)&(t[:,:,1].max(1)>-3)]
sections=[]
for z in (.2,.4,.75,1.):
    segments=[]
    for triangle in near:
        if triangle[:,2].min()>z or triangle[:,2].max()<z: continue
        cut=[]
        for p,q in ((triangle[0],triangle[1]),(triangle[1],triangle[2]),(triangle[2],triangle[0])):
            if (p[2]<=z<q[2]) or (q[2]<=z<p[2]):
                cut.append(p[:2]+(z-p[2])/(q[2]-p[2])*(q[:2]-p[:2]))
        if len(cut)==2: segments.append(cut)
    for y in (5.25,5.55,5.85,7.,10.):
        xs=[]
        for p,q in segments:
            if (p[1]<=y<q[1]) or (q[1]<=y<p[1]):
                xs.append(float(p[0]+(y-p[1])/(q[1]-p[1])*(q[0]-p[0])))
        sections.append(dict(z=z,y=y,x_intersections=sorted(xs)))
v0=t[:,1,:2]-t[:,0,:2]; v1=t[:,2,:2]-t[:,0,:2]
det=v0[:,0]*v1[:,1]-v0[:,1]*v1[:,0]; ok=abs(det)>1e-9
tri=t[ok];v0=v0[ok];v1=v1[ok];det=det[ok];ground=[]
for x in (2.25,2.55,2.85,3.15,3.45,3.75):
    for y in (4.5,5.25,5.55,5.85,6.5):
        v=np.array([x,y])-tri[:,0,:2]
        u=(v[:,0]*v1[:,1]-v[:,1]*v1[:,0])/det
        w=(v0[:,0]*v[:,1]-v0[:,1]*v[:,0])/det
        inside=(u>=-1e-8)&(w>=-1e-8)&(u+w<=1+1e-8)
        height=tri[:,0,2]+u*(tri[:,1,2]-tri[:,0,2])+w*(tri[:,2,2]-tri[:,0,2])
        ground.append(dict(x=x,y=y,vertical_intersection_z=np.unique(np.round(height[inside],7)).tolist()))
print(json.dumps(dict(mesh=str(a.mesh),units=[v.attrib for v in r.findall('.//c:asset/c:unit',ns)],
                     up_axis=[v.text for v in r.findall('.//c:asset/c:up_axis',ns)],
                     bounds=[pos.min(0).tolist(),pos.max(0).tolist()],
                     wall_sections=sections,ground_probes=ground),indent=2))
