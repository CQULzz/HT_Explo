#!/usr/bin/env python3
import json,hashlib
from pathlib import Path
import cv2,numpy as np
HERE=Path(__file__).resolve().parent
out=HERE/'assets';out.mkdir(exist_ok=True)
p=Path('/home/lzz/下载/data_scout/traversability_sim_data_train_height/version2_mountain_z12_use_n47_height_200_distancex_2050_distancey_2050.png')
h=cv2.resize(cv2.imread(str(p),0),(513,513)).astype(float)/255*2
# Image rows point south, columns east. Retain physical 21 m training extent.
x=np.linspace(-10.5,10.5,513);xx,yy=np.meshgrid(x,-x)
np.savez_compressed(out/'terrain.npz',height=h,x=x)
mesh=out/'terrain.obj'
with mesh.open('w') as f:
 for row in range(0,513,2):
  for col in range(0,513,2):f.write(f'v {xx[row,col]:.6f} {yy[row,col]:.6f} {h[row,col]:.6f}\n')
 for r in range(256):
  for c in range(256):
   i=r*257+c+1;f.write(f'f {i} {i+258} {i+1}\nf {i} {i+257} {i+258}\n')
plugins=''.join(f'<plugin filename="gz-sim-{a}-system" name="gz::sim::systems::{b}">{extra}</plugin>' for a,b,extra in [('physics','Physics',''),('sensors','Sensors','<render_engine>ogre2</render_engine>'),('scene-broadcaster','SceneBroadcaster',''),('user-commands','UserCommands','')])
geom=f'<geometry><mesh><uri>{mesh}</uri></mesh></geometry>'
world=f'<sdf version="1.7"><world name="default">{plugins}<gravity>0 0 -9.8</gravity><scene><ambient>0.7 0.7 0.7 1</ambient></scene><light name="sun" type="directional"><pose>0 0 20 0 0 0</pose><diffuse>0.8 0.8 0.8 1</diffuse><direction>-0.5 0.2 -1</direction></light><model name="mountain"><static>true</static><link name="terrain"><collision name="ground">{geom}</collision><visual name="ground">{geom}<material><ambient>0.5 0.6 0.4 1</ambient><diffuse>0.5 0.6 0.4 1</diffuse></material></visual></link></model></world></sdf>'
walls=''
for i,(wx,wy,sx,sy) in enumerate([(-10.6,0,.2,21.4),(10.6,0,.2,21.4),(0,-10.6,21.4,.2),(0,10.6,21.4,.2)]):
 box=f'<geometry><box><size>{sx} {sy} 4</size></box></geometry>'
 walls+=f'<model name="boundary_{i}"><static>true</static><pose>{wx} {wy} 2 0 0 0</pose><link name="wall"><collision name="wall">{box}</collision><visual name="wall">{box}</visual></link></model>'
world=world.replace('</world>',walls+'</world>')
(out/'mountain.world').write_text(world)
# Pick lowest local slope in a fixed 2 m square near (-6,-6), solely from geometry.
grad=np.hypot(*np.gradient(h,21/512));mask=(xx>-7)&(xx<-5)&(yy>-7)&(yy<-5);score=np.where(mask,cv2.GaussianBlur(grad,(25,25),0),np.inf);r,c=np.unravel_index(np.argmin(score),h.shape)
spawn=[float(xx[r,c]),float(yy[r,c]),float(h[r,c])]
meta={'source':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'extent_m':21,'spawn_ground_xyz':spawn,'slope_degrees_percentiles':np.percentile(np.degrees(np.arctan(grad)),[50,75,95]).tolist(),'model_resolution_m':21/513,'mesh_resolution_m':21/256,'note':'Supplied training-domain mountain; simplified CMU kinematic robot, not Scout dynamics.'};(out/'terrain.json').write_text(json.dumps(meta,indent=2)+'\n')
# Scoring surface: geometric exposure is a proxy, not collision/success ground truth.
import sys
sys.path.insert(0,str(HERE.parent))
from coverage_metrics import voxel_keys
np.savez_compressed(out/'reference.npz',keys=voxel_keys(np.c_[xx.ravel(),yy.ravel(),h.ravel()]))
print(meta)

# Explicit sensor adaptation for a separate paired experiment; stock profile is preserved.
lidar=Path('/home/lzz/my test/autonomous_exploration_development_environment/src/vehicle_simulator/urdf/lidar.sdf').read_text()
import re
lidar=re.sub(r'(<vertical>.*?<samples>)\d+(</samples>)',r'\g<1>64\2',lidar,flags=re.S).replace('<min_angle>-0.261799</min_angle>','<min_angle>-1.308997</min_angle>')
(out/'lidar_downward.sdf').write_text(lidar)
# Idealized downward sensing: exclude robot visuals from GPU lidar ray rendering.
# This is a simulation adaptation, not a claim about real sensor observability.
import xml.etree.ElementTree as ET
for source_name,target_name in [('robot.sdf','robot_sensor_mask.sdf'),('camera.sdf','camera_sensor_mask.sdf'),('lidar.sdf','lidar_downward.sdf')]:
 text=(out/target_name).read_text() if source_name=='lidar.sdf' else (Path('/home/lzz/my test/autonomous_exploration_development_environment/src/vehicle_simulator/urdf')/source_name).read_text()
 tree=ET.fromstring(text);tree.set('version','1.10')
 for visual in tree.iter('visual'):
  ET.SubElement(visual,'visibility_flags').text='1'
 if source_name=='lidar.sdf':ET.SubElement(next(tree.iter('lidar')),'visibility_mask').text='2'
 (out/target_name).write_text(ET.tostring(tree,encoding='unicode'))
