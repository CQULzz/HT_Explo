from pathlib import Path
import xml.etree.ElementTree as E
import numpy as np,json,hashlib,sys
ROOT=Path('/home/lzz/pcd_physics_20261110');ROOT.mkdir(exist_ok=True);ASSET=ROOT/'assets';ASSET.mkdir(exist_ok=True)
SOURCE=Path('/home/lzz/pcd_test_20261110/source');ns={'c':'http://www.collada.org/2005/11/COLLADASchema'}
for name in ['ground','obstacles']:
 root=E.parse(SOURCE/f'model_assets/environment/{name}.dae').getroot();mesh=root.find('.//c:mesh',ns);verts=mesh.find('c:vertices/c:input',ns).get('source')[1:];array=mesh.find(f"c:source[@id='{verts}']/c:float_array",ns);vertices=np.fromstring(array.text,sep=' ').reshape(-1,3);tri=mesh.find('c:triangles',ns);inputs=tri.findall('c:input',ns);stride=1+max(int(x.get('offset')) for x in inputs);off=int(next(x for x in inputs if x.get('semantic')=='VERTEX').get('offset'));indices=np.fromstring(tri.findtext('c:p',namespaces=ns),sep=' ',dtype=np.int64).reshape(-1,stride)[:,off].reshape(-1,3)
 with (ASSET/f'{name}.obj').open('w') as f:
  for v in vertices:f.write('v %.9g %.9g %.9g\n'%tuple(v))
  for face in indices+1:f.write('f %d %d %d\n'%tuple(face))
 np.savez_compressed(ASSET/f'{name}.npz',vertices=vertices,triangles=indices)
scene=E.parse(SOURCE/'runtime/scene.sdf').find(".//model[@name='scout']");robot=E.Element('robot',name='archived_scout_collision_model')
for link in scene.findall('link'):
 dest=E.SubElement(robot,'link',name=link.get('name'));inertial=E.SubElement(dest,'inertial');old=link.find('inertial');E.SubElement(inertial,'origin',xyz='0 0 0',rpy='0 0 0');E.SubElement(inertial,'mass',value=old.findtext('mass'));E.SubElement(inertial,'inertia',**{k:old.findtext('inertia/'+k,'0') for k in ['ixx','ixy','ixz','iyy','iyz','izz']})
 for col in link.findall('collision'):
  pose=col.findtext('pose','0 0 0 0 0 0').split()
  for tag in ['collision','visual']:
   item=E.SubElement(dest,tag);E.SubElement(item,'origin',xyz=' '.join(pose[:3]),rpy=' '.join(pose[3:]));geo=E.SubElement(item,'geometry');g=col.find('geometry')
   if g.find('box') is not None:E.SubElement(geo,'box',size=g.findtext('box/size'))
   else:E.SubElement(geo,'cylinder',length=g.findtext('cylinder/length'),radius=g.findtext('cylinder/radius'))
   if tag=='visual':E.SubElement(E.SubElement(item,'material',name=link.get('name')+'_color'),'color',rgba='0.12 0.14 0.18 1' if 'wheel' in link.get('name') else '0.15 0.55 0.8 1')
for j in scene.findall('joint'):
 dest=E.SubElement(robot,'joint',name=j.get('name'),type='continuous');pose=j.findtext('pose').split();E.SubElement(dest,'origin',xyz=' '.join(pose[:3]),rpy=' '.join(pose[3:]));E.SubElement(dest,'parent',link=j.findtext('parent'));E.SubElement(dest,'child',link=j.findtext('child'));E.SubElement(dest,'axis',xyz=j.findtext('axis/xyz'));E.SubElement(dest,'limit',effort=j.findtext('axis/limit/effort'),velocity=j.findtext('axis/limit/velocity'));E.SubElement(dest,'dynamics',damping='0',friction='0')
E.ElementTree(robot).write(ASSET/'scout.urdf',encoding='unicode')
comparison=json.load(open('/home/lzz/pcd_test_20261110/analysis/ht_geometry/exact/RESULT.json'));cases=[];seen=set()
for i,e in enumerate(comparison['counterexamples']):
 key=(round(e['x'],2),round(e['y'],2))
 if key in seen:continue
 seen.add(key);k=3 if 59<e['ht_source_elapsed_s']<60 else e['allowed_channels'][0]
 cases.append({'id':f'Hpass_Gblock_{len(cases)+1:02d}','class':'HT_allow_geometry_proxy_reject','xy':[e['x'],e['y']],'heading_deg':k*45,'ht_score':e['eight_scores'][k],'frame_source_elapsed_s':e['ht_source_elapsed_s'],'geometric_obstacle_voxels':e['geometry_obstacle_centroids_within_0_45m']})
for frame_num in [1,7,15]:
 f=np.load(f'/home/lzz/pcd_test_20261110/analysis/ht_geometry/exact/frame_{frame_num:02d}.npz');ff=comparison['frames'][frame_num-1];origin=np.array(ff['robot_xy']);good=f['common']&f['physical']&(f['geometry_count']==0);bad=np.isfinite(f['scores'])&(f['scores']<.5);mask=good&bad.any(0);rs,cs=np.where(mask)
 if not len(rs):continue
 order=np.argsort(np.hypot(f['x'][rs,cs]-origin[0],f['y'][rs,cs]-origin[1]));r,c=rs[order[0]],cs[order[0]];k=int(np.argmin(f['scores'][:,r,c]));xy=[float(f['x'][r,c]),float(f['y'][r,c])]
 cases.append({'id':f'Hblock_Gclear_{frame_num:02d}','class':'HT_neural_reject_geometry_proxy_clear','xy':xy,'heading_deg':k*45,'ht_score':float(f['scores'][k,r,c]),'frame_source_elapsed_s':ff['ht_source_elapsed_s'],'geometric_obstacle_voxels':0})
manifest={'source':'Archived Scout SDF mass/inertia/collisions/joints converted to URDF; exact environment Collada vertices/indices exported to OBJ, no extra ground plane in map trials.',
 'vehicle':{'body_box_m':[.925,.38,.21],'total_mass_kg':48,'wheel_radius_m':.16459,'wheel_track_m':.58306,'wheel_base_m':.498,'wheel_torque_limit_Nm':80},
 'selected_cases':cases,'selection':'One closest-robot HT-allow/geometry-reject counterexample per unique XY from prior 15-frame comparison; choose first allowed heading except image case uses135deg. Other class: closest-robot geometrically clear/physically supported position with a neural-rejected heading in saved frames1/7/15; lowest score heading. Frozen before dynamics results.',
 'probe':{'distance_each_side_m':.8,'command_speed_m_s':.2,'settle_s':2,'drive_s':12,'post_s':1,'dt_s':1/240,'forward_and_reverse':True,'friction_modes':['historical_like','isotropic_0_4','isotropic_0_8']},
 'friction_note':'historical_like: lateralFriction .8 and wheel-local anisotropic [1,1,.125] approximates archive longitudinal .8/lateral .1. ODE slip .03 not exactly transferable; isotropic .4/.8 are sensitivity cases, not calibrated vehicle truth.',
 'assets':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in ASSET.iterdir() if p.is_file()}}
(ROOT/'MANIFEST.json').write_text(json.dumps(manifest,indent=2));print(json.dumps(manifest,indent=2))
