"""Generate opaque Scout geometry and a nominal nonuniform Helios32 sensor.

Never modifies an existing historical simulation profile. All visual meshes are
also made opaque collisions because rack/sensor URDF visuals lack collision tags.
"""
from pathlib import Path
import argparse,copy,hashlib,importlib.util,json,math,shutil,subprocess
import xml.etree.ElementTree as ET
import numpy as np

def element(parent,tag,text=None,**attrs):
    e=ET.SubElement(parent,tag,attrs)
    if text is not None:e.text=str(text)
    return e

def pose_string(t):
    r=t[:3,:3];pitch=math.atan2(-r[2,0],math.hypot(r[0,0],r[1,0]));roll=math.atan2(r[2,1],r[2,2]);yaw=math.atan2(r[1,0],r[0,0])
    return ' '.join(f'{x:.15g}' for x in [*t[:3,3],roll,pitch,yaw])

def prepare(package_dir,out,profile):
    out.mkdir(parents=True,exist_ok=False);(out/'meshes').mkdir()
    helper=Path(__file__).resolve().parents[1]/'vehicle_envelope/from_urdf.py';spec=importlib.util.spec_from_file_location('urdf_geometry',helper);geometry=importlib.util.module_from_spec(spec);spec.loader.exec_module(geometry)
    source=package_dir/'urdf/scout_sensor_rack.urdf.xacro'
    expanded=subprocess.check_output(['xacro',str(source)]);(out/'scout_expanded.urdf').write_bytes(expanded);tree=ET.fromstring(expanded)
    parents={j.find('child').get('link'):(j.find('parent').get('link'),geometry.transform(j.find('origin'))) for j in tree.findall('joint')}
    if any(j.get('type')!='fixed' for j in tree.findall('joint')):raise ValueError('Only the pinned fixed Scout model is supported')
    def absolute(name):
        if name not in parents:return np.eye(4)
        p,t=parents[name];return absolute(p)@t
    # This source URDF aliases rslidar to the mechanical mounting frame at the
    # rack top. Use the manual's nominal optical datum, not that mounting plane.
    optical=absolute('rslidar').copy();optical[:3,3]+=optical[:3,:3]@np.array([0.,0.,.0635])
    to_sensor=np.linalg.inv(optical);base_to_sensor=np.linalg.inv(absolute('base_link'))@optical
    model=ET.Element('sdf',version='1.7');body=element(model,'model',name='robot');element(body,'static','false');link=element(body,'link',name='body');element(link,'gravity','false');element(link,'kinematic','true')
    inertial=element(link,'inertial');element(inertial,'mass','40');inertia=element(inertial,'inertia')
    for name,value in [('ixx',10),('iyy',10),('izz',10),('ixy',0),('ixz',0),('iyz',0)]:element(inertia,name,value)
    inventory={};collisions=[]
    def sdf_geometry(source_geometry):
        g=ET.Element('geometry');part=list(source_geometry)[0]
        if part.tag=='mesh':
            uri=part.get('filename');prefix='package://ele_scout_kit/'
            if not uri.startswith(prefix):raise ValueError('Unresolved mesh URI: '+uri)
            path=package_dir/uri[len(prefix):];target=out/'meshes'/path.name
            if not target.exists():shutil.copy2(path,target)
            inventory[uri]=hashlib.sha256(path.read_bytes()).hexdigest();mesh=element(g,'mesh');element(mesh,'uri',target.resolve().as_uri());element(mesh,'scale',part.get('scale','1 1 1'))
        elif part.tag=='box':element(element(g,'box'),'size',part.get('size'))
        elif part.tag=='cylinder':
            c=element(g,'cylinder');element(c,'radius',part.get('radius'));element(c,'length',part.get('length'))
        else:raise ValueError('Unsupported opaque geometry: '+part.tag)
        return g
    for source_link in tree.findall('link'):
        name=source_link.get('name')
        for tag in ['visual','collision']:
            for index,item in enumerate(source_link.findall(tag)):
                transform=to_sensor@absolute(name)@geometry.transform(item.find('origin'));g=sdf_geometry(item.find('geometry'))
                if tag=='visual':
                    v=element(link,'visual',name=f'{name}_visual_{index}');element(v,'pose',pose_string(transform));v.append(copy.deepcopy(g))
                collision_name=f'opaque_{name}_{tag}_{index}';c=element(link,'collision',name=collision_name);element(c,'pose',pose_string(transform));c.append(g);collisions.append(collision_name)
    ET.ElementTree(model).write(out/'robot.sdf',encoding='unicode')
    # A ray starts immediately OUTSIDE its own optical window. Its casing is
    # still an opaque collision mesh. Starting at output_min_range would let
    # near obstructions disappear, so trace-min stays zero and clipping is last.
    housing=geometry.mesh_vertices(package_dir/'meshes/rs_helios.STL');window=float(np.linalg.norm(housing[:,:2],axis=1).max()+.001)
    lidar=ET.Element('sdf',version='1.7');m=element(lidar,'model',name='lidar');l=element(m,'link',name='sensor');element(l,'gravity','false');element(l,'kinematic','true')
    inertial=element(l,'inertial');element(inertial,'mass','.01');inertia=element(inertial,'inertia')
    for name,value in [('ixx',.0001),('iyy',.0001),('izz',.0001),('ixy',0),('ixz',0),('iyz',0)]:element(inertia,name,value)
    s=element(l,'sensor',name='helios32',type='ray');element(s,'always_on','true');element(s,'update_rate',profile['update_rate_hz']);element(s,'visualize','false');ray=element(s,'ray');scan=element(ray,'scan')
    h=element(scan,'horizontal');n=profile['horizontal_samples'];element(h,'samples',n);element(h,'resolution',1);element(h,'min_angle',-math.pi);element(h,'max_angle',math.pi-2*math.pi/n)
    v=element(scan,'vertical');element(v,'samples',32);element(v,'resolution',1);element(v,'min_angle',math.radians(min(profile['vertical_angles_deg'])));element(v,'max_angle',math.radians(max(profile['vertical_angles_deg'])))
    bounds=element(ray,'range');element(bounds,'min',0);element(bounds,'max',150);element(bounds,'resolution',.0025)
    p=element(s,'plugin',name='helios32_ray',filename='libhelios32_ray.so');element(p,'vertical_angles_deg',' '.join(map(str,profile['vertical_angles_deg'])));element(p,'channel_max_ranges_m',' '.join(map(str,profile['channel_max_ranges_m'])));element(p,'optical_window_radius_m',window);element(p,'output_min_range_m',profile['output_min_range_m']);element(p,'frame_name','rslidar')
    ET.ElementTree(lidar).write(out/'lidar.sdf',encoding='unicode')
    # CMU's carrier updates a camera pose entity even with RGB disabled. The
    # real camera mesh is already in robot.sdf; this is only an empty pose anchor.
    camera=ET.Element('sdf',version='1.7');cm=element(camera,'model',name='camera');cl=element(cm,'link',name='pose_anchor');element(cl,'gravity','false');element(cl,'kinematic','true');ET.ElementTree(camera).write(out/'camera.sdf',encoding='unicode')
    description=ET.Element('robot',name='helios32_frames');element(description,'link',name='sensor');element(description,'link',name='rslidar');joint=element(description,'joint',name='sensor_to_rslidar',type='fixed');element(joint,'parent',link='sensor');element(joint,'child',link='rslidar');element(joint,'origin',xyz='0 0 0',rpy='0 0 0')
    element(description,'link',name='base_link');joint=element(description,'joint',name='sensor_to_scout_base',type='fixed');element(joint,'parent',link='sensor');element(joint,'child',link='base_link');values=pose_string(np.linalg.inv(base_to_sensor)).split();element(joint,'origin',xyz=' '.join(values[:3]),rpy=' '.join(values[3:]));ET.ElementTree(description).write(out/'lidar.urdf',encoding='unicode')
    metadata={'source_repository':'CQULzz/eletranskit_scout','source_commit':'cf0b73d7d01b4b6a2718c7ff3124f4b7a3368c36','urdf_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'mesh_sha256':inventory,'opaque_collisions':collisions,'collision_count':len(collisions),'base_link_to_lidar_xyz':base_to_sensor[:3,3].tolist(),'lidar_height_above_ground_m':float(optical[2,3]),'mount_to_optical_z_m':.0635,'optical_window_radius_m':window,'optical_scope':'Nominal manual optical origin 63.5mm above mounting base; source alias treated as mounting datum at rack top. Exit window just outside housing mesh. Not recovered physical extrinsic calibration. No general vehicle collision exclusion.','profile':profile}
    (out/'MANIFEST.json').write_text(json.dumps(metadata,indent=2));return metadata

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--package-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--profile',type=Path,default=Path(__file__).with_name('helios_5515.json'));a=p.parse_args();metadata=prepare(a.package_dir,a.output,json.loads(a.profile.read_text()));print(json.dumps({k:metadata[k] for k in ['collision_count','base_link_to_lidar_xyz','lidar_height_above_ground_m','optical_window_radius_m']},indent=2))
