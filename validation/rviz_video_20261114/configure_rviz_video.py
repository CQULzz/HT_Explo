from pathlib import Path
import yaml,json
r=Path('/mnt/d/HT-Execution-300s/rviz_video_20261114');r.mkdir(exist_ok=True)
for local in [False,True]:
 name='detail' if local else 'overview'
 d={'Panels':[],'Preferences':{'PromptSaveOnExit':False},'Visualization Manager':{'Class':'','Displays':[
 {'Class':'rviz_default_plugins/Grid','Name':'Metric grid','Enabled':True,'Cell Size':1.,'Plane Cell Count':200,'Color':'50; 60; 74','Alpha':.22,'Line Style':{'Value':'Lines','Line Width':.01},'Reference Frame':'map'},
 {'Class':'rviz_default_plugins/PointCloud2','Name':'Observed surfaces','Enabled':True,'Topic':{'Value':'/visual/surfaces','Depth':1,'Reliability Policy':'Reliable','Durability Policy':'Transient Local'},'Position Transformer':'XYZ','Color Transformer':'FlatColor','Color':'105; 186; 235','Alpha':.9,'Style':'Squares','Size (Pixels)':2,'Size (m)':.10,'Decay Time':0.,'Use Fixed Frame':True},
 {'Class':'rviz_default_plugins/MarkerArray','Name':'Recorded exploration','Enabled':True,'Topic':{'Value':'/visual/markers','Depth':1,'Reliability Policy':'Reliable','Durability Policy':'Transient Local'}}],
 'Enabled':True,'Global Options':{'Fixed Frame':'map','Background Color':'20; 25; 34','Frame Rate':30},'Tools':[{'Class':'rviz_default_plugins/Interact'},{'Class':'rviz_default_plugins/MoveCamera'}],
 'Views':{'Current':{'Class':'rviz_default_plugins/Orbit','Distance':25. if local else 112.,'Focal Point':{'X':0. if local else 18.,'Y':0. if local else 20.,'Z':0.},'Pitch':1.35 if local else 1.5707,'Yaw':1.5708,'Target Frame':'replay_camera' if local else 'map','Near Clip Distance':.01,'Name':'Current View','Invert Z Axis':False}}},
 'Window Geometry':{'Width':800 if local else 1120,'Height':960,'X':1120 if local else 0,'Y':60,'Hide Left Dock':True,'Hide Right Dock':True}}
 (r/f'{name}.rviz').write_text(yaml.safe_dump(d,sort_keys=False))
(r/'control.json').write_text(json.dumps({'mode':'hold','time':300,'rate':4}))
print('RViz overview and follow-camera configurations ready')
