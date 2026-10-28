from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from matplotlib.patches import Rectangle
O=Path(__file__).parent;B=Path('/media/lzz/My Passport/HT_filter_expansion_2026-10-29');p=np.load(O/'ground_patch_probe_fields.npz');r=json.loads((O/'PATCH_PROBE.json').read_text());t=r['target'];font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc';font_manager.fontManager.addfont(font);plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();plt.rcParams['axes.unicode_minus']=False
fig,ax=plt.subplots(2,3,figsize=(17,10),layout='constrained')
for a,key,title in [(ax[0,0],'old_residual','26.61秒：输入去平面后的厘米起伏\n0°分数0.982，八方向均>0.8'),(ax[0,1],'new_residual','29.20秒：同一世界点的厘米起伏\n0°分数0.164，八方向均<0.34')]:
 im=a.imshow(p[key].T*100,origin='lower',extent=[-1.02,1.02,-1.02,1.02],vmin=-5,vmax=5,cmap='coolwarm',interpolation='nearest');a.set(title=title,xlabel='相对目标点X / m',ylabel='相对目标点Y / m');a.scatter(0,0,c='black',s=30,marker='+');fig.colorbar(im,ax=a,shrink=.7,label='相对各自拟合平面 / cm')
res=json.loads((B/'pad020_170043/RESULTS.json').read_text());z=np.load(B/'pad020_170043/frames'/res['frames'][52]['file']);T=z['ht_dir_0'].copy();T[z['ht_valid']<.5]=np.nan;center=z['center'];cmap=plt.colormaps['RdYlGn'].copy();cmap.set_bad('#777777');im=ax[0,2].imshow(T[::-1,::-1].T,origin='lower',extent=[center[0]-4.82,center[0]+4.82,center[1]-4.82,center[1]+4.82],vmin=0,vmax=1,cmap=cmap,interpolation='nearest');wx,wy=t['world_xy'];ax[0,2].add_patch(Rectangle((wx-1.02,wy-1.02),2.04,2.04,fill=False,color='black',linewidth=2));ax[0,2].scatter(wx,wy,c='black',marker='+',s=80);ax[0,2].scatter(*z['robot'][:2],c='deepskyblue',s=35,edgecolors='black');ax[0,2].set(title='扩大20cm后的0°图：黑框是核查邻域\n两套过滤在此处的输入与输出完全相同',xlabel='世界X / m',ylabel='世界Y / m');fig.colorbar(im,ax=ax[0,2],shrink=.7,label='T(θ=0°)')
x=np.arange(8);v=r['results']
for a,keys,names,title in [(ax[1,0],['actual_before','actual_after'],['前帧实际输入','后帧实际输入'],'同位置的八方向输出：全部从绿变红'),(ax[1,1],['diagnostic_new_plane_old_texture','diagnostic_old_plane_new_texture'],['新坡面＋旧纹理','旧坡面＋新纹理'],'仅诊断的对换试验：输出跟随纹理变化')]:
 for k,(key,name) in enumerate(zip(keys,names)):a.bar(x+(k-.5)*.36,v[key],width=.34,label=name)
 a.axhline(.5,color='black',linestyle='--');a.set(xticks=x,xticklabels=[str(k*45)+'°' for k in x],ylim=(0,1.05),ylabel='HT类别分数',title=title);a.legend(fontsize=9);a.grid(axis='y',alpha=.2)
keys=['actual_after','diagnostic_new_plane_only','diagnostic_gauss_sigma_0p5_cell','diagnostic_gauss_sigma_1_cell'];names=['原始后帧','仅拟合平面','0.5格平滑','1格平滑'];ax[1,2].bar(np.arange(4),[v[k][0] for k in keys],color=['#d95f02','#66a61e','#1b9e77','#7570b3']);ax[1,2].set(xticks=np.arange(4),xticklabels=names,ylim=(0,1.05),ylabel='0° HT分数',title='仅诊断的输入改动：说明对细碎起伏敏感\n平滑可能损伤真实小障碍，未部署');ax[1,2].axhline(.5,color='black',linestyle='--');ax[1,2].grid(axis='y',alpha=.2)
fig.suptitle('对比视频中的明确地面反例：世界点(−0.48, 12.24)m\n变化已经在CuPy原生高程出现；融合后仅1/2601格需最近邻填值；不是仅靠缺测或附近墙体就能解释',fontsize=16);fig.savefig(O/'ground_texture_causal.png',dpi=160);plt.close(fig)
