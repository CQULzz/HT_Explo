from pathlib import Path
import json,numpy as np,matplotlib,yaml
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
O=Path('/media/lzz/My Passport/HT_filter_expansion_2026-10-29');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');D=R/'docs/results/real_filter_expansion_2026-10-29';D.mkdir(parents=True,exist_ok=True)
font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc';font_manager.fontManager.addfont(font);plt.rcParams['font.family']=font_manager.FontProperties(fname=font).get_name();plt.rcParams['axes.unicode_minus']=False
p=json.loads((O/'FILTER_COMPARISON.json').read_text());raw=json.loads((O/'POINT_REMOVAL_AUDIT.json').read_text());labels=['baseline','pad005','pad010','pad020'];names=['原过滤','水平+5cm','水平+10cm','水平+20cm'];colors=['#1f77b4','#ff9900','#aa5599','#228855'];fig,ax=plt.subplots(2,3,figsize=(17,10),layout='constrained')
for label,name,color in zip(labels,names,colors):
 s=p['series']['170043_'+label];t=[x['t_s'] for x in s];ax[0,0].plot(t,[x['near_all8_red_cells'] for x in s],label=name,color=color);ax[0,1].plot(t,[x['near_native_bump_cells'] for x in s],label=name,color=color);ax[0,2].plot(t,[x['red_fraction_direction_cells']*100 for x in s],label=name,color=color)
 s=p['series']['165317_'+label];ax[1,0].plot([x['t_s'] for x in s],[x['near_context_unknown_cells'] for x in s],label=name,color=color);ax[1,1].plot([x['t_s'] for x in s],[x['near_physical_unknown_cells'] for x in s],label=name,color=color)
for a,title,ylabel in [(ax[0,0],'移动包：车周1.5m内八方向全部低分','格数（maxθT<0.5）'),(ax[0,1],'移动包：车周原生高程偏高6～25cm','格数，相对同一基准拟合地面'),(ax[0,2],'移动包：有效输出中全部方向低分占比','方向×格，占比%'),(ax[1,0],'静止包：扩大后神经上下文未知增加','车周1.5m内格数'),(ax[1,1],'静止包：扩大后物理支持未知增加','车周1.5m内格数')]:a.set(title=title,xlabel='雷达源时间 / s',ylabel=ylabel);a.grid(alpha=.2);a.legend(fontsize=9)
for k,scene in enumerate(['165317','170043']):
 g=[x for x in raw['summary'] if x['scene']==scene];ax[1,2].bar(np.arange(3)+k*.36,[x['removed_candidate_ground_points'] for x in g],width=.34,label='静止包' if k==0 else '移动包')
ax[1,2].set(xticks=np.arange(3)+.18,xticklabels=['+5cm','+10cm','+20cm'],title='采样原始扫描：附带删去的近地面候选点',ylabel='重复观测点数，非地面真值');ax[1,2].legend();fig.suptitle('只扩大水平自过滤：随车红斑减少，但静止盲区增大；大面积变红仍存在\n两份录包、三种扩大量，共六次完整重算；高度边界、模型、0.5硬门槛与轨迹均未改变',fontsize=16);fig.savefig(O/'filter_expansion_comparison.png',dpi=160);plt.close(fig)
fig,ax=plt.subplots(2,2,figsize=(12,11),layout='constrained');cmap=plt.colormaps['RdYlGn'].copy();cmap.set_bad('#777777')
for row,frame in enumerate([17,52]):
 for col,label in enumerate(['baseline','pad020']):
  f=B/'rebuild_170043' if label=='baseline' else O/'pad020_170043';r=json.loads((f/'RESULTS.json').read_text());z=np.load(f/'frames'/r['frames'][frame]['file']);v=np.where(z['ht_valid']>.5,z['ht_dir_0'],np.nan);center=z['center'];n=v.shape[0];extent=[center[0]-4.82,center[0]+4.82,center[1]-4.82,center[1]+4.82];im=ax[row,col].imshow(v[::-1,::-1].T,origin='lower',extent=extent,vmin=0,vmax=1,cmap=cmap,interpolation='nearest');robot=z['robot'];ax[row,col].scatter(robot[0],robot[1],c='deepskyblue',edgecolors='black',s=35);ax[row,col].set(title=f'{"原过滤" if label=="baseline" else "水平+20cm"}：t={r["frames"][frame]["t_s"]:.2f}s，固定0°',xlabel='世界X / m',ylabel='世界Y / m');fig.colorbar(im,ax=ax[row,col],shrink=.75,label='T(θ=0°)')
fig.suptitle('同位置、同一θ对比：9.5秒近车红斑改善，29.2秒较大低分区并未消失\n青点为录包车辆位置；灰色为无效。不是本轮车辆执行路径。',fontsize=14);fig.savefig(O/'same_direction_before_after.png',dpi=160);plt.close(fig)
# Export explicit experimental profiles, preserving production configuration.
for margin in [.05,.1,.2]:
 profile=yaml.safe_load((R/'src/ht_scout_bridge/config/scout_extrinsics.yaml').read_text());profile['lidar_self_filter']['horizontal_padding_m']=margin;profile['lidar_self_filter']['horizontal_padding_status']='Offline experiment only; not physically verified vehicle geometry';(O/f'scout_filter_trial_{int(margin*100):02d}cm.yaml').write_text(yaml.safe_dump(profile,allow_unicode=True,sort_keys=False))
print('figures and explicit trial profiles saved')
