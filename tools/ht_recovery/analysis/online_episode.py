from pathlib import Path
import json,math,csv,sys,subprocess
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry,Path as RosPath
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/home/lzz/ht_recovery_20261111');run=ROOT/'runs/cmu_recovery_300s_02';out=ROOT/'analysis/online_episode';out.mkdir(exist_ok=False);episode=json.loads((ROOT/'analysis/RECOVERY_EPISODES.json').read_text())['cmu_recovery_300s_02']['episodes'][0];begin=episode['start']['time'];end=episode['end']['time'];targetstamp=episode['start']['map_stamp'];reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local','/state_estimation','/ht_minimal/recovery_path']));reader.seek(int((begin-1.5)*1e9));grid=None;route=None;poses=[]
while reader.has_next():
 topic,data,received=reader.read_next()
 if received/1e9>end+.2:break
 if topic=='/ht_traversability/global_local':
  msg=deserialize_message(data,GridMap);stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
  if abs(stamp-targetstamp)<1e-6:grid=msg;(out/'start_map.cdr').write_bytes(data)
 elif topic=='/ht_minimal/recovery_path':
  msg=deserialize_message(data,RosPath);stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
  if begin-.1<=stamp<=begin+1:route=msg;(out/'planned_path.cdr').write_bytes(data)
 else:
  msg=deserialize_message(data,Odometry);stamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
  if begin<=stamp<=end:
   p=msg.pose.pose.position;q=msg.pose.pose.orientation;yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z));poses.append([stamp-begin,p.x,p.y,yaw])
assert grid is not None and route is not None and poses
poses=np.array(poses);np.savez_compressed(out/'trace.npz',poses=poses,columns=np.array(['elapsed_s','x','y','yaw']));sys.path.insert(0,'/home/lzz/HT_Explo_recovery_20261111/tools/cmu_minimal');from audit_commands import decode
m=decode(grid);rr,cc=np.where(m['occupied']);xx=m['cx']+(m['rows']/2-rr-.5)*m['res'];yy=m['cy']+(m['cols']/2-cc-.5)*m['res'];planned=np.array([[p.pose.position.x,p.pose.position.y] for p in route.poses]);xmin=min(poses[:,1].min(),planned[:,0].min())-.3;xmax=max(poses[:,1].max(),planned[:,0].max())+.3;ymin=min(poses[:,2].min(),planned[:,1].min())-.3;ymax=max(poses[:,2].max(),planned[:,1].max())+.3
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False});fig,ax=plt.subplots(figsize=(9,8));ax.scatter(xx,yy,s=1,c='#fecaca',label='恢复启动时HT膨胀占用');ax.plot(planned[:,0],planned[:,1],c='#64748b',ls='--',lw=2,label='实际发布的恢复计划');ax.plot(poses[:,1],poses[:,2],c='#0f766e',lw=2,label='随后实时里程计轨迹')
for i in range(0,len(poses),150):ax.arrow(poses[i,1],poses[i,2],.08*np.cos(poses[i,3]),.08*np.sin(poses[i,3]),width=.004,color='#334155')
ax.set(xlim=(xmin,xmax),ylim=(ymin,ymax),aspect='equal',xlabel='世界X / m',ylabel='世界Y / m',title='300秒复测中的在线恢复：转向、短移、再转向、前进');ax.legend(fontsize=9);fig.text(.5,.025,'11.18秒完成，净位移0.784m，向启动时目标推进0.763m；背景为启动时快照，逐命令新地图检查另见审计。',ha='center',fontsize=9);fig.tight_layout(rect=(0,.05,1,1));fig.savefig(ROOT/'delivery/online_recovery.png',dpi=170);plt.close(fig)
W,H=1000,800;span=max(xmax-xmin,ymax-ymin);cx=(xmin+xmax)/2;cy=(ymin+ymax)/2;scale=580/span
def pixel(x,y):return(500+(x-cx)*scale,420-(y-cy)*scale)
bg=Image.new('RGB',(W,H),'white');draw=ImageDraw.Draw(bg)
for x,y in zip(xx,yy):
 if xmin<x<xmax and ymin<y<ymax:draw.point(pixel(x,y),fill='#fecaca')
pix=[pixel(x,y) for x,y in planned];draw.line(pix,fill='#94a3b8',width=2);font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22);small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',17)
proc=subprocess.Popen(['/home/lzz/cmu_test_20261110/deps/usr/bin/ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','20','-i','-','-c:v','libx264','-threads','1','-preset','fast','-pix_fmt','yuv420p',str(ROOT/'delivery/online_recovery.mp4')],stdin=subprocess.PIPE)
for t in np.arange(0,poses[-1,0]+.049,.05):
 i=min(int(np.searchsorted(poses[:,0],t)),len(poses)-1);im=bg.copy();d=ImageDraw.Draw(im);d.text((20,10),'实时CMU仿真记录｜HT自主局部恢复片段',font=font,fill='#0f172a');d.text((20,45),'1倍速里程计轨迹可视化，非相机录像；背景为启动时HT图',font=small,fill='#475569');xy=[pixel(x,y) for x,y in poses[:i+1:2,1:3]]
 if len(xy)>1:d.line(xy,fill='#0f766e',width=4)
 u,v=pixel(poses[i,1],poses[i,2]);d.ellipse((u-5,v-5,u+5,v+5),fill='#ea580c');d.line((u,v,u+25*np.cos(poses[i,3]),v-25*np.sin(poses[i,3])),fill='#334155',width=4);d.text((20,745),f't={poses[i,0]:.2f}s，完成事件时净位移0.784m、向原目标推进0.763m',font=small,fill='#0f172a');proc.stdin.write(im.tobytes())
proc.stdin.close();assert proc.wait()==0;(out/'META.json').write_text(json.dumps({'episode':episode,'source_map_exact_stamp':targetstamp,'recorded_poses':len(poses),'actual_published_plan_poses':len(route.poses),'scope':'Real recorded Gazebo/CMU odometry during the recovery episode; background fixed to its starting HT map, actual per-command map audits are separate. Video is data visualization, not a camera recording.'},indent=2));print(out)
