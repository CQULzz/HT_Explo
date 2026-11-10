from pathlib import Path
import sys,json,csv,io,subprocess,math
import numpy as np
sys.path.insert(0,'/home/lzz/pcd_physics_20261110/python')
import pybullet as p
from PIL import Image,ImageDraw,ImageFont
import test_physics as bench
ROOT=bench.ROOT;OUT=ROOT/'delivery';OUT.mkdir(exist_ok=True)
font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',20);small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',16)
items=[('Hpass_Gblock_07_historical_like_rev','图中反例：HT放行、几何包络拒绝','倒车通过；HT分数0.953'),('Hblock_Gclear_01_historical_like_fwd','另一反例：HT拒绝、几何未检出障碍','前进通过；HT分数0.450')]
p.connect(p.DIRECT);panels=[];stills=[]
for label,title,subtitle in items:
 run=ROOT/'runs_batch02'/label;result=json.loads((run/'RESULT.json').read_text());rows=list(csv.DictReader((run/'trace.csv').open()));bench.world(False);case=result['case'];cx,cy=case['xy'];ground=bench.height_at([[cx,cy]],bench.top)[0];body=p.loadURDF(str(bench.ASSET/'scout.urdf'),flags=p.URDF_USE_INERTIA_FROM_FILE)
 view=p.computeViewMatrixFromYawPitchRoll([cx,cy,ground+.15],2.1,case['heading_deg']+100,-38,0,2);proj=p.computeProjectionMatrixFOV(55,640/440,.01,50);vp=np.array(proj).reshape(4,4,order='F')@np.array(view).reshape(4,4,order='F');clip=vp@np.array([cx,cy,ground+.02,1]);ndc=clip[:3]/clip[3];pixel=(int((ndc[0]+1)*320),int((1-ndc[1])*220))
 frames=[]
 for row in rows:
  pos=[float(row[k]) for k in ['x','y','z']];rpy=[float(row[k]) for k in ['roll','pitch','yaw']];p.resetBasePositionAndOrientation(body,pos,p.getQuaternionFromEuler(rpy))
  for j in range(4):p.resetJointState(body,j,float(row[f'joint_{j}_angle']))
  data=p.getCameraImage(640,440,viewMatrix=view,projectionMatrix=proj,renderer=p.ER_TINY_RENDERER,lightDirection=[-1,-2,3],shadow=1)[2];im=Image.fromarray(np.asarray(data,dtype=np.uint8).reshape(440,640,4)[:,:,:3]);draw=ImageDraw.Draw(im);x,y=pixel;draw.line([(x-8,y),(x+8,y)],fill='#ef4444',width=2);draw.line([(x,y-8),(x,y+8)],fill='#ef4444',width=2);draw.text((x+10,y+4),'待测点',fill='#dc2626',font=small)
  canvas=Image.new('RGB',(640,560),'white');canvas.paste(im,(0,100));draw=ImageDraw.Draw(canvas);draw.text((10,5),title,fill='black',font=font);draw.text((10,34),subtitle,fill='#0f766e',font=small);draw.text((10,60),f't={float(row["time_s"]):.2f}s  进度={float(row["progress_m"]):.2f}m  车底接触={row["chassis_contacts"]}',fill='black',font=small);draw.text((10,541),'接触动力学记录状态回放，非实车录像',fill='#475569',font=small);frames.append(canvas)
 panels.append(frames)
 # Save three moments near start, center crossing, completion.
 stills.append([frames[min(range(len(rows)),key=lambda i:abs(float(rows[i]['time_s'])-t))] for t in [2.,6.2,11.]])
p.disconnect();process=subprocess.Popen(['/home/lzz/cmu_test_20261110/deps/usr/bin/ffmpeg','-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1280x560','-r','20','-i','-','-c:v','libx264','-threads','1','-preset','fast','-pix_fmt','yuv420p',str(OUT/'physical_conflict_crossings.mp4')],stdin=subprocess.PIPE)
for i in range(min(map(len,panels))):
 canvas=Image.new('RGB',(1280,560),'white');canvas.paste(panels[0][i],(0,0));canvas.paste(panels[1][i],(640,0));process.stdin.write(canvas.tobytes())
process.stdin.close();assert process.wait()==0
image=Image.new('RGB',(1280,1680),'white')
for j in range(3):
 for i in range(2):image.paste(stills[i][j],(i*640,j*560))
image.save(OUT/'physical_crossing_frames.png');print('rendered',len(panels[0]),len(panels[1]))
