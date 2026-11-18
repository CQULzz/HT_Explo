from pathlib import Path
from lxml import etree
import hashlib,json
r=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');p=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus/meshes/campus.dae');data=p.read_bytes();ns='{http://www.collada.org/2005/11/COLLADASchema}';bad=[]
for event,e in etree.iterparse(str(p),events=['end'],tag=ns+'visual_scene',huge_tree=True):
 def walk(node,parents):
  transforms=[c.tag.split('}')[-1] for c in node if c.tag.split('}')[-1] in ['matrix','rotate','translate','scale','lookat','skew']]
  if node.find(ns+'instance_geometry') is not None and any(t!='matrix' for t in parents+transforms):bad.append(node.attrib)
  for n in node.findall(ns+'node'):walk(n,parents+transforms)
 for n in e.findall(ns+'node'):walk(n,[])
old=json.loads(Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02/FREEZE.json').read_text());expected=next(v for k,v in old.items() if k.endswith('/campus.dae'));digest=hashlib.sha256(data).hexdigest();unsupported={name:data.count(('<'+name).encode()) for name in ['polylist','polygons','tristrips','trifans']};assert digest==expected and not bad and not any(unsupported.values())
proof={'mesh_sha256':digest,'matches_experiment_freeze':True,'unsupported_face_primitive_counts':unsupported,'unsupported_geometry_node_transform_count':len(bad),'mesh_parser_covers_all_used_primitive_and_transform_types':True};(r/'MESH_PARSER_AUDIT.json').write_text(json.dumps(proof,indent=2));print(json.dumps(proof,indent=2))
