from pathlib import Path
from lxml import etree
import numpy as np,json
p=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus/meshes/campus.dae');out=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');ns={'c':'http://www.collada.org/2005/11/COLLADASchema'};geos={};instances=[]
for event,e in etree.iterparse(str(p),events=['end'],tag=['{'+ns['c']+'}geometry','{'+ns['c']+'}visual_scene'],huge_tree=True):
 if e.tag.endswith('geometry'):
  mesh=e.find('c:mesh',ns)
  if mesh is not None:
   source={s.attrib['id']:s for s in mesh.findall('c:source',ns)};vertices={v.attrib['id']:v.find('c:input',ns).attrib['source'][1:] for v in mesh.findall('c:vertices',ns)};parts=[]
   for tri in mesh.findall('c:triangles',ns):
    inputs=tri.findall('c:input',ns);stride=max(int(i.attrib.get('offset',0)) for i in inputs)+1;vi=next(i for i in inputs if i.attrib['semantic']=='VERTEX');offset=int(vi.attrib.get('offset',0));sid=vertices[vi.attrib['source'][1:]];coords=np.fromstring(source[sid].find('c:float_array',ns).text,sep=' ',dtype=np.float32).reshape(-1,3);indices=np.fromstring(tri.find('c:p',ns).text,sep=' ',dtype=np.int32).reshape(-1,stride)[:,offset].reshape(-1,3);parts.append((coords,indices))
   geos[e.attrib['id']]=parts
 if e.tag.endswith('visual_scene'):
  def walk(node,parent):
   transform=parent.copy()
   for m in node.findall('c:matrix',ns):transform=transform@np.fromstring(m.text,sep=' ').reshape(4,4)
   for inst in node.findall('c:instance_geometry',ns):instances.append((inst.attrib['url'][1:],transform.copy()))
   for child in node.findall('c:node',ns):walk(child,transform)
  for n in e.findall('c:node',ns):walk(n,np.eye(4))
 e.clear()
 while e.getprevious() is not None:del e.getparent()[0]
vertices=[];faces=[];total=0
for gid,transform in instances:
 for coords,idx in geos[gid]:
  points=coords@transform[:3,:3].T+transform[:3,3];points[:,2]+=1.;vertices.append(points.astype(np.float32));faces.append(idx+total);total+=len(points)
v=np.concatenate(vertices);f=np.concatenate(faces);np.save(out/'mesh_vertices.npy',v);np.save(out/'mesh_faces.npy',f);summary={'geometry_objects':len(geos),'instances':len(instances),'vertices':len(v),'faces':len(f),'bounds':[v.min(0).tolist(),v.max(0).tolist()],'world_pose_z_m':1.,'transforms':[{'geometry':gid,'matrix':m.tolist()} for gid,m in instances]};(out/'MESH_INDEX.json').write_text(json.dumps(summary,indent=2));print(json.dumps({k:v for k,v in summary.items() if k!='transforms'},indent=2))
