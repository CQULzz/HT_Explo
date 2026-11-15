from pathlib import Path
import shutil
source=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/campus_pcd_20261114/source/video_tools')
root=Path('/mnt/d/HT-URDF-Compare-20261115');tools=root/'video_tools';tools.mkdir(exist_ok=True)
for name in ['prepare.py','player.py','configure.py','record.py','start.sh']:
    shutil.copy2(source/name,tools/name)
player=(tools/'player.py').read_text()
player=player.replace("ROOT=Path(os.environ['HT_VIDEO_ROOT'])","ROOT=Path(os.environ['HT_VIDEO_ROOT'])\nBODY=json.loads((ROOT/'BODY.json').read_text())\nTEXT=Path(os.environ['HT_VIDEO_TEXT_ROOT']);TEXT.mkdir(parents=True,exist_ok=True)")
for name in ['status.tmp','status.txt','hud.tmp','hud.txt']:
    player=player.replace("ROOT/'"+name+"'","TEXT/'"+name+"'")
player=player.replace("m.pose.position=self.point(x,y,z-.75+.28)","bx,by,bz=BODY['center'];m.pose.position=self.point(x+math.cos(yaw)*bx-math.sin(yaw)*by,y+math.sin(yaw)*bx+math.cos(yaw)*by,z-.75+bz)")
player=player.replace('m.scale.x=.6;m.scale.y=.6;m.scale.z=.45','m.scale.x,m.scale.y,m.scale.z=BODY[\'size\']')
(tools/'player.py').write_text(player)
record=(tools/'record.py').read_text().replace("'-i',':89'","'-i',os.environ['DISPLAY']")
record=record.replace("r=Path(os.environ['HT_VIDEO_ROOT'])","r=Path(os.environ['HT_VIDEO_ROOT'])\ntextroot=Path(os.environ['HT_VIDEO_TEXT_ROOT']);textroot.mkdir(parents=True,exist_ok=True)")
for name in ['left_title.txt','right_title.txt','legend.txt']:
    record=record.replace("r/'"+name+"'","textroot/'"+name+"'")
record=record.replace('r/file','textroot/file')
(tools/'record.py').write_text(record)
start=(tools/'start.sh').read_text().replace('source /home/lzz/ht_600s_20261114/env.sh','source /home/lzz/ht_urdf_compare_20261115/env.sh')
start=start.replace('export ROS_DOMAIN_ID=221 DISPLAY=:89','export ROS_DOMAIN_ID="$HT_VIDEO_DOMAIN" DISPLAY="$HT_VIDEO_DISPLAY"')
start=start.replace('export XDG_RUNTIME_DIR=/tmp/ht-rviz-video-runtime','export XDG_RUNTIME_DIR=/tmp/ht-urdf-video-$ROS_DOMAIN_ID')
start=start.replace('Xvfb :89','Xvfb "$DISPLAY"').replace('/mnt/d/HT-Execution-300s/campus_pcd_videos_20261114/tools/player.py',str(tools/'player.py'))
(tools/'start.sh').write_text(start)
print('Prepared two-view recording tools')
