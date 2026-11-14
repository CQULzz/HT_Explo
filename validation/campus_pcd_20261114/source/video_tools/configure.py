from pathlib import Path
import yaml,json,os,math
import numpy as np
r=Path(os.environ['HT_VIDEO_ROOT']);r.mkdir(exist_ok=True)
traj=np.load(r/'trajectory.npy');lo=traj[:,1:3].min(0)-10;hi=traj[:,1:3].max(0)+10;center=(lo+hi)/2;distance=max(42.,float(max(hi-lo))*1.3/(2*math.tan(math.pi/8)));floor_z=float(np.median(traj[:,3])-.75)
for local in [False,True]:
 name='detail' if local else 'overview'
 d={'Panels':[],'Preferences':{'PromptSaveOnExit':False},'Visualization Manager':{'Class':'','Displays':[
 {'Class':'rviz_default_plugins/Grid','Name':'Metric grid','Enabled':True,'Cell Size':1.,'Plane Cell Count':200,'Color':'50; 60; 74','Alpha':.22,'Line Style':{'Value':'Lines','Line Width':.01},'Reference Frame':'map','Offset':{'X':0.,'Y':0.,'Z':float(traj[:,3].min()-.95)}},
 {'Class':'rviz_default_plugins/PointCloud2','Name':'Observed surfaces','Enabled':True,'Topic':{'Value':'/visual/surfaces','Depth':1,'Reliability Policy':'Reliable','Durability Policy':'Transient Local'},'Position Transformer':'XYZ','Color Transformer':'FlatColor','Color':'105; 186; 235','Alpha':.9,'Style':'Squares','Size (Pixels)':2,'Size (m)':.10,'Decay Time':0.,'Use Fixed Frame':True},
 {'Class':'rviz_default_plugins/MarkerArray','Name':'Recorded exploration','Enabled':True,'Topic':{'Value':'/visual/markers','Depth':1,'Reliability Policy':'Reliable','Durability Policy':'Transient Local'}}],
 'Enabled':True,'Global Options':{'Fixed Frame':'map','Background Color':'20; 25; 34','Frame Rate':30},'Tools':[{'Class':'rviz_default_plugins/Interact'},{'Class':'rviz_default_plugins/MoveCamera'}],
 'Views':{'Current':{'Class':'rviz_default_plugins/Orbit','Distance':25. if local else distance,'Focal Point':{'X':0. if local else float(center[0]),'Y':0. if local else float(center[1]),'Z':0. if local else floor_z},'Pitch':1.35 if local else 1.5707,'Yaw':1.5708,'Target Frame':'replay_camera' if local else 'map','Near Clip Distance':.01,'Name':'Current View','Invert Z Axis':False}}},
 'Window Geometry':{'Width':800 if local else 1120,'Height':960,'X':1120 if local else 0,'Y':60,'Hide Left Dock':True,'Hide Right Dock':True}}
 (r/f'{name}.rviz').write_text(yaml.safe_dump(d,sort_keys=False))
(r/'control.json').write_text(json.dumps({'mode':'hold','time':300,'rate':4}))
print('RViz overview and follow-camera configurations ready')
