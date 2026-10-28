from pathlib import Path
import numpy as np,json
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from matplotlib.colors import TwoSlopeNorm
O=Path('/media/lzz/My Passport/HT_newbags_replay_20261028/red_region_audit');B=O.parent;R=json.loads((B/'rebuild_170043/RESULTS.json').read_text());qfiles=sorted((O/'contexts').glob('*.npz'));font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc';font_manager.fontManager.addfont(font);plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();plt.rcParams['axes.unicode_minus']=False
q=np.load(O/'frame17_probe_fields.npz');fig,axes=plt.subplots(2,3,figsize=(17,10),layout='constrained')
z=np.load(B/'rebuild_170043/frames/frame_0017.npz');rob=z['robot'];center=z['center'];r=.04
# World coordinates translated to the recorded robot; the height field itself is unchanged.
def plotfield(ax,field,center,cmap,vmin,vmax,title):
 n,m=field.shape;i,j=np.indices(field.shape);x=center[0]+(n//2-i)*r-rob[0];y=center[1]+(m//2-j)*r-rob[1]
 p=ax.pcolormesh(x,y,field,cmap=cmap,vmin=vmin,vmax=vmax,shading='nearest',rasterized=True);ax.set_aspect('equal');ax.set(xlim=(-2,2),ylim=(-2,2),title=title,xlabel='相对车辆的世界 X / m',ylabel='相对车辆的世界 Y / m');ax.scatter([0],[0],c='deepskyblue',s=30,edgecolors='black');return p
p=plotfield(axes[0,0],(q['height']-q['plane'])*100,center,'coolwarm',-15,15,'9.50秒：真正送入HT的高度（相对地面/cm）');fig.colorbar(p,ax=axes[0,0],shrink=.7,label='相对拟合地面 / cm')
x=q['bx'][q['bump']];y=q['by'][q['bump']];axes[0,1].scatter(x,y,c=(q['height']-q['plane'])[q['bump']]*100,cmap='Reds',vmin=6,vmax=15,s=55,marker='s');axes[0,1].plot([-.4825,.4825,.4825,-.4825,-.4825],[-.21,-.21,.21,.21,-.21],c='black');axes[0,1].set(xlim=(-1.5,1),ylim=(-1,1),xlabel='车体 X / m（前方为正）',ylabel='车体 Y / m（左侧为正）',title='23个直接观测的高程凸起格：车体右后侧');axes[0,1].set_aspect('equal');axes[0,1].grid(alpha=.2)
p=plotfield(axes[0,2],np.max(q['original'],axis=0),center,'RdYlGn',0,1,'原始HT：即便取八方向最高分，车旁仍有低分');fig.colorbar(p,ax=axes[0,2],shrink=.7,label='maxθ T')
p=plotfield(axes[1,0],np.max(q['diagnostic_replace_only_6to25cm_measured_bumps'],axis=0),center,'RdYlGn',0,1,'仅用于归因：移除23个凸起后，275个红格中266个跨过0.5\n该修改未部署；不能据此直接删除这些点');fig.colorbar(p,ax=axes[1,0],shrink=.7,label='maxθ T')
# Fixed world point: no heading changes or moving-cell comparison.
f=next(x for x in json.loads((O/'WORLD_FLIPS.json').read_text()) if x['before']==10 and x['after']==15)
patches=[]
for ax,idx,ind,label in [(axes[1,1],10,f['old_index'],'5.60秒，T0=0.047'),(axes[1,2],15,f['new_index'],'8.40秒，T0=0.991')]:
 c=np.load(qfiles[idx]);i,j=ind;patch=c['height'][i:i+51,j:j+51];patches.append(patch);p=ax.imshow(patch.T,origin='lower',extent=[-1.02,1.02,-1.02,1.02],cmap='terrain',vmin=-.8,vmax=-.58,interpolation='nearest');ax.scatter([0],[0],c='red',marker='+',s=100);ax.set(title=f'同一世界点 (−3.28, 5.52)m：{label}\n该点自身高程变化仅2.3mm，周围输入改变约12.5cm',xlabel='相对该地面点的 X / m',ylabel='相对该地面点的 Y / m');fig.colorbar(p,ax=ax,shrink=.7,label='输入绝对高程 / m')
fig.suptitle('随车红斑来源核验：原始近车高回波 → 高程凸起 → 约2米感受野内的HT低分\n对原始64帧输出逐层精确复现；所有反事实仅用于诊断，无生产代码或车辆指令修改',fontsize=17)
fig.savefig(O/'red_region_evidence.png',dpi=170);plt.close(fig)
print(O/'red_region_evidence.png')
