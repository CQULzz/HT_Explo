from pathlib import Path
import json,numpy as np,matplotlib,subprocess,imageio_ffmpeg,os
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch,Rectangle,Polygon
O=Path(__file__).parent;L=Path('/media/lzz/My Passport/HT_texture_source_fix_2026-10-29');F=O/'figures';F.mkdir(exist_ok=True);font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc');plt.rcParams.update({'font.family':'Noto Sans CJK JP','font.size':11,'axes.unicode_minus':False,'pdf.fonttype':42});S=json.load(open(O/'SUMMARY.json'));A=json.load(open(O/'POINT_AUDIT.json'));pdf=PdfPages(O/'all_comparisons.pdf');names=[];colors=['#386fa6','#de7c2c']
def save(fig,name):fig.savefig(F/(name+'.png'),dpi=150);pdf.savefig(fig);plt.close(fig);names.append(name+'.png')
def sample(folder,index):
 row=json.load(open(folder/'RESULTS.json'))['frames'][index];z=np.load(folder/'frames'/row['file']);return z,row
cm=plt.get_cmap('RdYlGn').copy();cm.set_bad('#81878b');gx,gy=np.meshgrid(np.arange(-1.6,1.6001,.04),np.arange(-1.6,1.6001,.04),indexing='ij')
def body_map(z):
 robot=z['robot'];c,s=np.cos(robot[3]),np.sin(robot[3]);world=np.stack([gx,gy],axis=-1)@np.array([[c,s],[-s,c]])+robot[:2];ij=np.rint(120+(z['center']-world)/float(z['resolution'])).astype(int);i,j=ij[:,:,0],ij[:,:,1];inside=(i>=0)&(i<241)&(j>=0)&(j<241);out=np.full(gx.shape,np.nan);ii,jj=i[inside],j[inside];p=np.max(np.stack([z['ht_dir_'+str(k)] for k in range(8)]),axis=0);v=z['ht_valid']>.5;known=v[ii,jj];loc=np.flatnonzero(inside);out.ravel()[loc[known]]=p[ii[known],jj[known]];return out.T
fig,ax=plt.subplots(figsize=(15,7));ax.axis('off');boxes=[('旧规则：只看回波落点','落点在车外，就保留\n漏掉轮胎后方近场不可信回波'),('新增有限射线检查','现有轮胎模型＋原2cm裕量\n1.6m内，轮胎出口后3～50cm'),('保留两类证据','保护标定地面+3cm以下回波\n有更高可见结构支撑则保留'),('进入原建图与HT','默认实车过滤已开启\n模型、0.5门槛、TARE逻辑不变')]
for i,(t,b) in enumerate(boxes):
 x=.01+i*.25;ax.add_patch(FancyBboxPatch((x,.43),.22,.32,boxstyle='round,pad=.01',facecolor=['#e8edf3','#f6e9dd','#e4f0e0','#e4edf7'][i],edgecolor='#64717c'));ax.text(x+.11,.66,t,ha='center',fontsize=15);ax.text(x+.11,.53,b,ha='center',fontsize=12)
 if i<3:ax.add_patch(FancyArrowPatch((x+.22,.59),(x+.25,.59),arrowstyle='-|>',mutation_scale=20,color='#50606a'))
ax.text(.5,.25,'过滤发生在原始点云进入建图之前；不是给车辆周围的地图涂绿。',ha='center',fontsize=16);ax.text(.5,.14,'含2cm裕量的阴影不能直接等同于真实遮挡：必须保留可见的外部结构证据。',ha='center',fontsize=13);fig.suptitle('修复原理与边界：端点过滤补上有界轮胎阴影检查',fontsize=18);save(fig,'01_filter_logic')
z=np.load(O/'POINT_EVIDENCE_scan95.npz');p=z['body_xyz'];old=z['old_keep'];removed=old&~z['new_keep'];near=old&np.isfinite(p).all(1)&(np.linalg.norm(p-np.array([.1725,0,.5502]),axis=1)<1.6);idx=np.flatnonzero(near);fig=plt.figure(figsize=(15,7));a=fig.add_subplot(121,projection='3d');a.scatter(p[idx,0],p[idx,1],p[idx,2],s=2,c='#99b2a0',alpha=.25);a.scatter(p[removed,0],p[removed,1],p[removed,2],s=15,c='#e76f26',label='新增过滤回波');origin=np.array([.1725,0,.5502]);a.scatter(*origin,c='#2463ab',s=40,label='标定LiDAR原点')
for x in [-.249,.249]:
 for y in [-.29153,.29153]:
  theta=np.linspace(0,2*np.pi,70);yy=np.array([y-.078265,y+.078265]);th,ys=np.meshgrid(theta,yy);a.plot_wireframe(x+.18459*np.cos(th),ys,-.0702+.18459*np.sin(th),color='#58636c',alpha=.6,lw=.6)
for k in np.flatnonzero(removed)[::max(1,int(removed.sum()/6))][:6]:a.plot([origin[0],p[k,0]],[origin[1],p[k,1]],[origin[2],p[k,2]],c='#d0803c',lw=.7,alpha=.7)
a.set(xlabel='车体X / m',ylabel='车体Y / m',zlabel='车体Z / m',xlim=(-1,.9),ylim=(-.9,.9),zlim=(-.3,.7),title='原始点云示例：约9.5秒，体外回波仍可能落入模型阴影');a.view_init(23,-115);a.legend(fontsize=9)
b=fig.add_subplot(122);b.scatter(p[idx,1],p[idx,2],s=3,c='#9bac9e',alpha=.3,label='原保留回波');b.scatter(p[removed,1],p[removed,2],s=16,c='#e76f26',label='新增过滤');b.axhspan(-.26479,-.20479,color='#c6dfbe',alpha=.5,label='原保留地面±3cm带：新增删除0');b.axhline(-.23479,c='#537e4e',ls=':');b.set(xlabel='车体Y / m',ylabel='车体Z / m',xlim=(-1,1),ylim=(-.3,.4),title='只针对近场可疑阴影回波；不整体扩大20cm');b.legend(fontsize=10);b.grid(alpha=.2);fig.suptitle('同一批源点：先剔除不可信车体近场回波，再重新建图；不是HT分数后处理',fontsize=15);save(fig,'02_raw_return_geometry')
fig,ax=plt.subplots(2,2,figsize=(15,10),layout='constrained')
for row,case in enumerate(['default_moving','registered_moving']):
 rr=S['series'][case]
 for role,c,label in [('old',colors[0],'修改前'),('new',colors[1],'新默认过滤')]:
  ax[row,0].plot([r['t_s'] for r in rr],[r[role+'_rear_red'] for r in rr],c=c,label=label)
  ax[row,1].plot([r['t_s'] for r in rr],[r[role+'_near_unknown'] for r in rr],c=c,label=label+' 上下文未知')
  ax[row,1].plot([r['t_s'] for r in rr],[r[role+'_near_physical_unknown'] for r in rr],c=c,ls=':',label=label+' 物理支持未知')
 ax[row,0].set(title=('配准关闭' if row==0 else '配准开启')+'：车后侧体外全方向低分格',ylabel='格数',xlabel='源时间 / s');ax[row,1].set(title='车周1.5m未知格完整曲线',ylabel='格数',xlabel='源时间 / s')
 for a in ax[row]:a.grid(alpha=.2);a.legend(fontsize=9)
fig.suptitle('四组完整对照的移动部分：后侧中位数141→0、125.5→0\n低分指八方向均<0.5；真实障碍出现仍允许低分，不能强制所有帧为0',fontsize=15);save(fig,'03_full_moving_curves')
fig,ax=plt.subplots(2,3,figsize=(15,10),layout='constrained')
for col,index in enumerate([17,47,62]):
 for row,folder in enumerate([L/'frozen_original_moving',O/'frozen_registered_moving']):
  z,r=sample(folder,index);a=ax[row,col];im=a.imshow(body_map(z),origin='lower',extent=[-1.62,1.62,-1.62,1.62],interpolation='nearest',cmap=cm,vmin=0,vmax=1);a.add_patch(Rectangle((-.4825,-.37),.965,.74,fill=False,edgecolor='#00d5ff',lw=1.5));a.set(title=('修改前' if row==0 else '新默认过滤')+f' t={r["t_s"]:.2f}s',xlabel='车体X（前）/ m',ylabel='车体Y（左）/ m');a.grid(alpha=.12);z.close()
fig.colorbar(im,ax=list(ax.flat),shrink=.7,label='八方向最大T：红=所有方向都低分，灰=未知');fig.suptitle('车体坐标下放大：9.5s、26.6s与末段残余低分的34.9s\n只旋转显示，不修改推理网格；青框为模型外包范围，末段大范围低分仍在，未宣称消除',fontsize=15);save(fig,'04_body_closeups')
fig,ax=plt.subplots(1,3,figsize=(17,6),layout='constrained');labels=['静止录包','移动录包'];x=np.arange(2);g=A['summary']
ax[0].bar(x,[r['extra_removed'] for r in g],color=colors[1]);ax[0].set(xticks=x,xticklabels=labels,title='1001帧原始点云全部审计\n新增过滤10604 / 8375点',ylabel='点次（包含重复测量）')
ax[1].bar(x-.15,[r['body_ground_candidates'] for r in g],.3,label='原保留地面高度带');ax[1].bar(x+.15,[r['extra_ground_removed'] for r in g],.3,label='新增删除=0');ax[1].set(xticks=x,xticklabels=labels,title='标定地面±3cm保护带\n模型坐标统计，不是人工地形标签',ylabel='点次');ax[1].legend(fontsize=9)
ax[2].bar(['仅阴影判据','加可见结构保护'],[42,48],color=colors);ax[2].set(ylim=(0,50),title='同一48个外部障碍样本\n保留可见上部，避免误删下部',ylabel='保留样本数');ax[2].axhline(48,c='gray',ls=':')
for a in ax:a.grid(axis='y',alpha=.2)
fig.suptitle('地面与障碍保护：明确保留失败的“只按阴影删除”版本及其反例\n原轮胎几何/外参不变；没有把低于某高度的外部障碍统一删掉',fontsize=15);save(fig,'05_ground_and_obstacle_controls')
fig,ax=plt.subplots(1,3,figsize=(17,6),layout='constrained');s=next(r for r in S['summary'] if r['case']=='default_stationary' and r['period']=='whole');ax[0].bar(['修改前','修改后'],[s['old_near_red_median'],s['new_near_red_median']],color=colors);ax[0].set(title='静止包车周低分834→833\n并未因本修正全面消失',ylabel='中位格数');ax[1].bar(['修改前','修改后'],[s['old_near_unknown_median'],s['new_near_unknown_median']],color=colors);ax[1].set(title='静止包未知2096→2096\n中心117帧均无效，仍未解决',ylabel='中位格数');ax[2].axis('off');ax[2].text(.02,.92,'适用范围与未验证项',fontsize=16);ax[2].text(.02,.78,'✓ 移动录包的随车低分显著减少\n✓ 未增加模型地面带的删点\n✓ 默认实车安装文件与源码一致\n\n待验证：真实外参/轮廓误差、细小孤立物、\n非平地、不同安装姿态与实车闭环。\n\n已知未修：静止盲区/未知、\n新障碍融合接收迟滞。',va='top',fontsize=13)
fig.suptitle('保留限制：两段录包不是多场景实车验收，不能把所有车旁红色都当作噪声',fontsize=16);save(fig,'06_stationary_remaining_limits')
pdf.close();(O/'FIGURES.json').write_text(json.dumps(names,indent=2)+'\n');print('figures',len(names),flush=True)
if os.environ.get('HT_PLOT_ONLY'):raise SystemExit(0)
# Crisp comparison video, body-centred only; actual RViz is a separate artifact.
fig,ax=plt.subplots(2,2,figsize=(16,9),dpi=120,gridspec_kw={'height_ratios':[3,1]});fig.subplots_adjust(top=.88,bottom=.08,wspace=.18,hspace=.25);images=[]
for a,label in zip(ax[0],['修改前','新默认车体过滤']):
 images.append(a.imshow(np.zeros(gx.shape),origin='lower',extent=[-1.62,1.62,-1.62,1.62],interpolation='nearest',cmap=cm,vmin=0,vmax=1));a.add_patch(Rectangle((-.4825,-.37),.965,.74,fill=False,edgecolor='#00d5ff',lw=1.5));a.set(title=label,xlabel='车体X / m',ylabel='车体Y / m')
rr=S['series']['registered_moving'];times=[r['t_s'] for r in rr]
for role,c,label in [('old',colors[0],'修改前'),('new',colors[1],'修正后')]:ax[1,0].plot(times,[r[role+'_rear_red'] for r in rr],c=c,label=label);ax[1,1].plot(times,[r[role+'_near_unknown'] for r in rr],c=c,label=label)
ax[1,0].set(title='后侧体外八方向全低分格数',xlabel='源时间 / s');ax[1,1].set(title='车周1.5m未知格数',xlabel='源时间 / s');cursor=[a.axvline(0,c='black',lw=1) for a in ax[1]]
for a in ax[1]:a.legend(fontsize=9);a.grid(alpha=.2)
title=fig.suptitle('',fontsize=16);fig.text(.5,.015,'离线地图对照（非控制录像）| 八方向最大T：红0→黄0.5→绿1，灰=未知 | 青框=录包车体 | 配准两侧均开启',ha='center',fontsize=10)
ff=imageio_ffmpeg.get_ffmpeg_exe();video=O/'HT_body_filter_before_after.mp4';cmd=[ff,'-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r','10','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(video)];process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=(O/'video_encode.log').open('w'));old=L/'frozen_original_moving';new=O/'frozen_registered_moving';ar=json.load(open(old/'RESULTS.json'))['frames'];br=json.load(open(new/'RESULTS.json'))['frames'];count=0
try:
 for n,(a,b) in enumerate(zip(ar,br)):
  for im,folder,row in zip(images,[old,new],[a,b]):
   with np.load(folder/'frames'/row['file']) as z:im.set_data(body_map(z))
  for line in cursor:line.set_xdata([a['t_s'],a['t_s']])
  title.set_text(f'修复随车低分区 | 点云时间 t={a["t_s"]:.2f}s | 0.04m网格，车体居中显示')
  fig.canvas.draw();pixels=np.asarray(fig.canvas.buffer_rgba())[:,:,:3].copy().tobytes();duration=ar[n+1]['t_s']-a['t_s'] if n+1<len(ar) else .5;repeat=max(1,round(duration*10))
  for _ in range(repeat):process.stdin.write(pixels)
  count+=repeat
finally:process.stdin.close();assert process.wait()==0
subprocess.run([ff,'-v','error','-i',str(video),'-f','null','-'],check=True,capture_output=True);(O/'COMPARISON_VIDEO_CHECK.json').write_text(json.dumps({'type':'Offline body-centred Matplotlib grid comparison, not RViz or real vehicle control','frames':count,'duration_s':count/10,'full_decode_passed':True},indent=2)+'\n');print('comparison video',count,'frames',flush=True)
