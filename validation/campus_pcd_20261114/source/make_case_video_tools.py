"""Prepare height-aware copies of the accepted RViz video layout; starts no nodes."""
from pathlib import Path
import os
base=Path('/mnt/d/HT-Execution-300s/setup');dst=Path('/mnt/d/HT-Execution-300s/campus_pcd_videos_20261114/tools');dst.mkdir(parents=True,exist_ok=True)
s=(base/'prepare_rviz_video.py').read_text()
s=s.replace('import json,csv,time','import json,csv,time,os')
s=s.replace("root=Path('/mnt/d/HT-Execution-300s/rviz_video_20261114')", "root=Path(os.environ['HT_VIDEO_ROOT'])")
s=s.replace("run=Path('/home/lzz/ht_600s_20261114/runs/execution_600s_01')", "run=Path(os.environ['HT_VIDEO_RUN'])")
s=s.replace('surface=set();free=set();snapshots=[]','surface=set();free=set();ground={};snapshots=[]')
s=s.replace("walls=points[(points[:,2]>=.15)&(points[:,2]<=2.5)]", "floor=float(origin[2]-.75)\n    near=points[np.linalg.norm(points[:,:2]-origin[:2],axis=1)<=12.]\n    low=near[np.abs(near[:,2]-floor)<=.35]\n    for p in low:\n        k=tuple(np.floor(p[:2]/.5).astype(int));ground[k]=min(ground.get(k,float('inf')),float(p[2]))\n    walls=near[(near[:,2]>=floor+.15)&(near[:,2]<=floor+2.5)]")
s=s.replace("cells=cells[cells[:,2]==0];free.update(map(tuple,cells[:,:2]))", "cells=cells[(cells[:,2]*.5+.25>=floor+.05)&(cells[:,2]*.5+.25<=floor+.85)];free.update(map(tuple,cells[:,:2]))")
s=s.replace("free=(np.array(list(free),np.float32)+.5)*.5", "free=np.array([[float(k[0])*.5+.25,float(k[1])*.5+.25,ground[k]+.02] for k in free if k in ground],np.float32).reshape(-1,3)")
s=s.replace("'surface_display':'Actual registered scans; 0.20m voxel sampling, z in [0.15,2.5]m.'", "'surface_display':'Actual scans within 12m of sensor; 0.20m display voxels, +0.15 to +2.5m relative to scan-pose ground reference (sensor_z-0.75m).'" )
s=s.replace("'green_display':'Projection of observed ray free voxels with z index 0 (0..0.5m), 0.5m grid, 1Hz/1024 endpoints/12m. This is observation only, not traversability or ground truth.'", "'green_display':'Near-ground ray-free XY projection, shown only where a low measured return exists. Tile display height uses the lowest measured return near that scan ground reference; no terrain is invented in unmeasured cells. Observation visualization only, not traversability or terrain truth.'")
(dst/'prepare.py').write_text(s)
with (dst/'prepare.py').open('a') as f:
 f.write('''\n# Keep the recorded gate/recovery status visible in the video.
status=[];last=None;gate='WAITING';recovery='';invalid_goal=False
for line in (run/'observations/events.jsonl').open():
    e=json.loads(line);d=e['data'];t=e['time']-start
    if t<0:continue
    if e['kind']=='/ht_minimal/command_audit' and 'reason' in d:gate=d['reason']
    if e['kind']=='/ht_minimal/recovery':recovery=d.get('state','') if d.get('active') else ''
    if e['kind']=='waypoint':invalid_goal=not all(isinstance(d.get(k),(float,int)) and np.isfinite(d[k]) for k in ['x','y','z'])
    value='INVALID_WAYPOINT' if invalid_goal else ('RECOVERY: '+recovery if recovery else gate)
    if value!=last:status.append({'elapsed_s':t,'value':value});last=value
(root/'status.json').write_text(json.dumps(status))
''')
s=(base/'rviz_video_player.py').read_text().replace('import time,json,math,argparse','import time,json,math,argparse,os').replace("ROOT=Path('/mnt/d/HT-Execution-300s/rviz_video_20261114')", "ROOT=Path(os.environ['HT_VIDEO_ROOT'])")
s=s.replace("self.traj=np.load(ROOT/'trajectory.npy');", "self.status=json.loads((ROOT/'status.json').read_text());self.status_times=np.array([v['elapsed_s'] for v in self.status]);self.traj=np.load(ROOT/'trajectory.npy');")
s=s.replace("  hud=ROOT/'hud.tmp';", "  si=max(0,min(len(self.status)-1,int(np.searchsorted(self.status_times,elapsed,side='right')-1)));status=ROOT/'status.tmp';status.write_text('HT门禁：'+self.status[si]['value'],encoding='utf-8');status.replace(ROOT/'status.txt')\n  hud=ROOT/'hud.tmp';")
s=s.replace("tf.transform.translation.y=float(y);tf.transform.rotation.w=1.", "tf.transform.translation.y=float(y);tf.transform.translation.z=float(z-.75);tf.transform.rotation.w=1.")
s=s.replace("m.points=[self.point(px,py,.015) for px,py in data['free'].reshape(-1,2)]", "m.points=[self.point(px,py,pz) for px,py,pz in data['free'].reshape(-1,3)]")
s=s.replace("self.point(v[1],v[2],.08)","self.point(v[1],v[2],v[3]-.75+.08)")
s=s.replace("m.pose.position=self.point(x,y,.28)", "m.pose.position=self.point(x,y,z-.75+.28)")
s=s.replace("self.point(x,y,.65),self.point(x+1.5*math.cos(yaw),y+1.5*math.sin(yaw),.65)", "self.point(x,y,z-.75+.65),self.point(x+1.5*math.cos(yaw),y+1.5*math.sin(yaw),z-.75+.65)")
s=s.replace("self.point(p[0],p[1],.12)","self.point(p[0],p[1],p[2]+.05)")
(dst/'player.py').write_text(s)
s=(base/'configure_rviz_video.py').read_text().replace('import yaml,json','import yaml,json,os,math\nimport numpy as np').replace("r=Path('/mnt/d/HT-Execution-300s/rviz_video_20261114')", "r=Path(os.environ['HT_VIDEO_ROOT'])")
s=s.replace('for local in [False,True]:', "traj=np.load(r/'trajectory.npy');lo=traj[:,1:3].min(0)-10;hi=traj[:,1:3].max(0)+10;center=(lo+hi)/2;distance=max(42.,float(max(hi-lo))*1.3/(2*math.tan(math.pi/8)));floor_z=float(np.median(traj[:,3])-.75)\nfor local in [False,True]:")
s=s.replace("'Reference Frame':'map'},", "'Reference Frame':'map','Offset':{'X':0.,'Y':0.,'Z':float(traj[:,3].min()-.95)}},")
s=s.replace("25. if local else 112.","25. if local else distance")
s=s.replace("'X':0. if local else 18.,'Y':0. if local else 20.,'Z':0.", "'X':0. if local else float(center[0]),'Y':0. if local else float(center[1]),'Z':0. if local else floor_z")
(dst/'configure.py').write_text(s)
s=(base/'start_rviz_video.sh').read_text().replace('ROS_DOMAIN_ID=217','ROS_DOMAIN_ID=221').replace('R=/mnt/d/HT-Execution-300s/rviz_video_20261114','R="$HT_VIDEO_ROOT"').replace('/mnt/d/HT-Execution-300s/setup/rviz_video_player.py','/mnt/d/HT-Execution-300s/campus_pcd_videos_20261114/tools/player.py')
(dst/'start.sh').write_text(s)
s=(base/'record_rviz_video.py').read_text().replace('import json,time,subprocess','import json,time,subprocess,os').replace("r=Path('/mnt/d/HT-Execution-300s/rviz_video_20261114')", "r=Path(os.environ['HT_VIDEO_ROOT'])")
s=s.replace("'整体探索范围与车辆轨迹'", "os.environ.get('HT_VIDEO_TITLE','探索')+'：整体范围与轨迹'")
s=s.replace('绿：观测自由空间投影（不代表可通行性判定）','绿：近地观测投影（不代表可通行性判定）')
s=s.replace("text('left_title.txt',25,12,30),", "text('left_title.txt',25,12,30),text('status.txt',580,18,22),")
s=s.replace("record('rviz_recovery_detail_1x.mp4',200,245,1)", '')
(dst/'record.py').write_text(s)
print('Prepared height-aware RViz render tools:',dst)
