from pathlib import Path
import importlib.util,xml.etree.ElementTree as E,numpy as np,json
repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes')
s=importlib.util.spec_from_file_location('g',repo/'tools/vehicle_envelope/from_urdf.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
r=Path('/home/lzz/ht_helios_collision_20261115');root=E.parse(r/'common_sensor/robot.sdf').getroot();out=[]
for c in root.findall('.//collision'):
 m=c.find('geometry/mesh')
 if m is None:continue
 path=Path(m.findtext('uri').replace('file://',''))
 if path.suffix.lower()!='.stl':continue
 v=g.mesh_vertices(path);pose=c.findtext('pose').split();o=E.Element('origin',xyz=' '.join(pose[:3]),rpy=' '.join(pose[3:]));t=g.transform(o);tri=(v@t[:3,:3].T+t[:3,3]).reshape(-1,3,3)
 for zoffset in [0,.0635]:
  for az in [0,np.pi/2,np.pi,-np.pi/2]:
   angle=-55*np.pi/180;start=np.array([.051*np.cos(az),.051*np.sin(az),zoffset]);d=np.array([np.cos(angle)*np.cos(az),np.cos(angle)*np.sin(az),np.sin(angle)])
   edge1=tri[:,1]-tri[:,0];edge2=tri[:,2]-tri[:,0];h=np.cross(d,edge2);det=np.einsum('ij,ij->i',edge1,h);ok=abs(det)>1e-10;inv=np.divide(1.,det,out=np.zeros_like(det),where=ok);delta=start-tri[:,0];u=inv*np.einsum('ij,ij->i',delta,h);q=np.cross(delta,edge1);vv=inv*(q@d);dist=inv*np.einsum('ij,ij->i',edge2,q);valid=ok&(u>=0)&(vv>=0)&(u+vv<=1)&(dist>0)
   if valid.any():out.append({'collision':c.get('name'),'offset':zoffset,'az':round(float(az),3),'distance':float(dist[valid].min())})
print(json.dumps(out,indent=2));(r/'mesh_ray_probe.json').write_text(json.dumps(out,indent=2))
