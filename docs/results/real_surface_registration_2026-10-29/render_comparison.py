from pathlib import Path
import subprocess,json,numpy as np,matplotlib,imageio_ffmpeg
FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from matplotlib.patches import Polygon
O=Path(__file__).parent;B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc');plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False,'font.size':10})
fig,ax=plt.subplots(2,2,figsize=(16,9),dpi=120);fig.subplots_adjust(left=.045,right=.91,bottom=.09,top=.89,wspace=.18,hspace=.18);cm=plt.get_cmap('RdYlGn').copy();cm.set_bad('#70787e');hm=plt.get_cmap('terrain').copy();hm.set_bad('#70787e');images=[];foot=[]
for i,a in enumerate(ax.flat):
 im=a.imshow(np.zeros((291,291) if i<2 else (241,241)),origin='lower',cmap=hm if i<2 else cm,vmin=-.85 if i<2 else 0,vmax=-.55 if i<2 else 1,interpolation='nearest');images.append(im);poly=Polygon(np.zeros((4,2)),fill=False,edgecolor='#00d8ff',linewidth=1.1);a.add_patch(poly);foot.append(poly);a.set_xlabel('世界X / m');a.set_ylabel('世界Y / m')
fig.colorbar(images[0],ax=list(ax[0]),location='right',fraction=.03,pad=.02,label='局部高程 / m（超范围颜色饱和）');fig.colorbar(images[2],ax=list(ax[1]),location='right',fraction=.03,pad=.02,label='0° HT T：红0 → 黄0.5 → 绿1')
title=fig.suptitle('',fontsize=17);fig.text(.5,.025,'实际录包点云离线重算对照 | 灰=未知，青框=录包车体 | 模型/0.5门槛/过滤不变 | 非RViz、非实车闭环录像',ha='center',fontsize=11)
path=O/'HT_surface_registration_before_after.mp4';command=[FFMPEG,'-v','warning','-y','-f','rawvideo','-pixel_format','rgb24','-video_size','1920x1080','-framerate','10','-i','-','-an','-c:v','libx264','-preset','fast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',str(path)];log=(O/'video_encode.log').open('w');process=subprocess.Popen(command,stdin=subprocess.PIPE,stderr=log);frames=0;sections=[]
try:
 for key,folder,label in [('original_stationary',B/'rebuild_165317','静止录包'),('original_moving',B/'rebuild_170043','移动录包')]:
  new=O/('frozen_'+key);rows=json.load(open(folder/'RESULTS.json'))['frames'];out=json.load(open(new/'RESULTS.json'))['frames'];start=frames
  for n,(a,b) in enumerate(zip(rows,out)):
   aa=np.load(folder/'frames'/a['file']);bb=np.load(new/'frames'/b['file']);center=aa['center'];res=float(aa['resolution']);robot=aa['robot'];base=np.array([[-.4825,-.29],[.4825,-.29],[.4825,.29],[-.4825,.29]]);c,s=np.cos(robot[3]),np.sin(robot[3]);poly=base@np.array([[c,s],[-s,c]])+robot[:2]
   fields=[aa['local_elevation'],bb['local_elevation'],np.where(aa['ht_valid']>.5,aa['ht_dir_0'],np.nan),np.where(bb['ht_valid']>.5,bb['ht_dir_0'],np.nan)]
   titles=['修改前：局部高程','配准修正后：局部高程','修改前：0°可通过性','配准修正后：0°可通过性']
   for i,(im,h,axis) in enumerate(zip(images,fields,ax.flat)):
    half=h.shape[0]*res/2;extent=[center[0]-half,center[0]+half,center[1]-half,center[1]+half];im.set_data(h[::-1,::-1].T);im.set_extent(extent);axis.set_xlim(extent[:2]);axis.set_ylim(extent[2:]);axis.set_title(titles[i]);foot[i].set_xy(poly)
   title.set_text(label+f' | 源时间 t={a["t_s"]:.2f}s | 同一帧、同一世界坐标范围')
   fig.canvas.draw();pixels=np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy().tobytes();duration=rows[n+1]['t_s']-a['t_s'] if n+1<len(rows) else .5;repeat=max(1,round(duration*10))
   for _ in range(repeat):process.stdin.write(pixels)
   frames+=repeat
   if key=='original_moving' and n==52:fig.savefig(O/'video_failure_frame_29s.png',dpi=120)
   aa.close();bb.close()
  sections.append({'case':key,'start_s':start/10,'end_s':frames/10,'source_snapshot_frames':len(rows)})
finally:
 process.stdin.close();code=process.wait();log.close();assert code==0,code
subprocess.run([FFMPEG,'-v','error','-i',str(path),'-f','null','-'],check=True,capture_output=True)
reader=imageio_ffmpeg.read_frames(str(path));probe=next(reader);reader.close();(O/'VIDEO_CHECK.json').write_text(json.dumps({'type':'Matplotlib offline map comparison, not RViz or physical closed loop','frames':frames,'sections':sections,'full_decode_passed':True,'probe':probe},indent=2)+'\n');print('video decoded',frames,'frames',frames/10,'seconds',flush=True)
