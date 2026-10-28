from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch,Polygon
O=Path(__file__).parent;F=O/'figures';F.mkdir(exist_ok=False);font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc');plt.rcParams.update({'font.family':'Noto Sans CJK JP','font.size':11,'axes.unicode_minus':False,'pdf.fonttype':42})
S=json.load(open(O/'SUMMARY.json'));pairs=json.load(open(O/'FROZEN_SAMPLE_RESULTS.json'));targets=json.load(open(O/'TARGETS.json'));raw=json.load(open(O/'RAW_SUMMARY.json'));per=json.load(open(O/'PER_SCAN_GROUND_PLANES.json'));loo=json.load(open(O/'COMMON_MODE_PROBE.json'))['rows'];pdf=PdfPages(O/'all_comparisons.pdf');files=[]
B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');P=Path('/media/lzz/My Passport/HT_filter_expansion_2026-10-29');oldfolders={'original_moving':B/'rebuild_170043','plus20_moving':P/'pad020_170043','original_stationary':B/'rebuild_165317','plus20_stationary':P/'pad020_165317'}
col=['#3366a3','#df7727'];names=['修改前','配准修正后']
def save(fig,name):
 fig.savefig(F/(name+'.png'),dpi=155);pdf.savefig(fig);plt.close(fig);files.append(name+'.png')
def data(key,role,index):
 root=oldfolders[key] if role=='old' else O/('frozen_'+key);r=json.load(open(root/'RESULTS.json'))['frames'][index];z=np.load(root/'frames'/r['file']);return z,r
fig,ax=plt.subplots(figsize=(15,7));ax.axis('off');items=[('单帧原始回波','探查区域单帧拟合残差\n中位数约1～2毫米'),('多帧世界坐标投影','移动时同一4cm格内\n约2～3厘米离散'),('高程图拼接','不同格来自不同时刻\n共同高度/倾斜偏差变成纹理'),('HT八方向响应','网络读取相邻高差\n部分地面窗口分数下降')]
for i,(title,body) in enumerate(items):
 x=.015+i*.248;ax.add_patch(FancyBboxPatch((x,.49),.22,.29,boxstyle='round,pad=.01',facecolor=['#e4edf7','#fae4dc','#f7eed8','#e1f1df'][i],edgecolor='#67717b'));ax.text(x+.11,.69,title,ha='center',fontsize=15);ax.text(x+.11,.58,body,ha='center',fontsize=12)
 if i<3:ax.add_patch(FancyArrowPatch((x+.22,.63),(x+.248,.63),arrowstyle='-|>',mutation_scale=20,color='#52606a'))
ax.text(.5,.32,'修正：只从近期、已观测的历史表面估计一组整帧刚体高度/倾斜校正；用未参与拟合的格子检验实际变换。',ha='center',fontsize=14)
ax.text(.5,.22,'不使用HT颜色作拟合目标；不降低0.5；不平滑高程格；不把走过的位置涂绿。',ha='center',fontsize=13)
ax.text(.5,.10,'证据支持“帧间几何不一致”的可复现机制；尚未把物理来源唯一归到Fixposition、TF时序或支架。',ha='center',fontsize=12)
fig.suptitle('根因与修正示意：不能把多帧拼接纹理直接当成真实微地形',fontsize=18);save(fig,'01_cause_and_fix')
fig,ax=plt.subplots(1,2,figsize=(15,6),layout='constrained');x=np.arange(3);width=.18
for bi,bag in enumerate(['stationary','moving']):
 within=[next(r for r in per if r['bag']==bag and r['xy']==xy)['records'] for xy in [[-.48,12.24],[-3.,13.],[-1.,18.]]];values=[np.median([r['rms'] for r in rr])*100 for rr in within];ax[0].bar(x+(bi-.5)*width,values,width,label=['静止','移动'][bi],color=col[bi])
 rr=next(r for r in raw if r['bag']==bag)['raw_probe_stats'];values=[rr[str(i)]['within_4cm_cell_rms_m']*100 for i in range(3)];ax[1].bar(x+(bi-.5)*width,values,width,label=['静止','移动'][bi],color=col[bi])
for a in ax:a.set(xticks=x,xticklabels=['A (-0.48,12.24)','B (-3,13)','C (-1,18)'],ylabel='厘米');a.legend();a.grid(axis='y',alpha=.2)
ax[0].set_title('单帧内部：去平面残差RMS的帧间中位数');ax[1].set_title('跨帧：相同4cm格中重复回波的离散RMS')
fig.suptitle('三块实测低起伏区域：单帧较平整，移动多帧投影却对不齐\n原始回波与固定网格统计；不是人工地形标签，静止/移动也不是两个独立场景',fontsize=15);save(fig,'02_single_frame_vs_multiframe')
fig,ax=plt.subplots(figsize=(11,6),layout='constrained');x=np.arange(3)
for role,label,c,shift in [('raw_rms_m','修正前',col[0],-.16),('corrected_rms_m','用另外两区拟合共同偏差后',col[1],.16)]:
 val=[]
 for h in range(3):
  rr=[r for r in loo if r['heldout_roi']==h];val.append(np.sqrt(np.average([r[role]**2 for r in rr],weights=[r['heldout_n'] for r in rr]))*100)
 ax.bar(x+shift,val,.32,label=label,color=c)
ax.set(xticks=x,xticklabels=['未参与拟合的A区','未参与拟合的B区','未参与拟合的C区'],ylabel='对静止录包实测参考面的RMS / cm');ax.legend();ax.grid(axis='y',alpha=.2);fig.suptitle('排查：共同高度/倾斜偏差可解释相当部分跨帧不一致\n仅诊断用静止实测参考；第三块区域留出；不是运行时使用真实地形答案',fontsize=15);save(fig,'03_spatial_heldout_cause')
fig,ax=plt.subplots(1,2,figsize=(15,6),layout='constrained');prov=json.load(open(O/'baseline_moving_PROVENANCE.json'))['records']
vals=[]
for xy in [[-.48,12.24],[-3.,13.],[-1.,18.]]:
 rr=[p for r in prov for p in r['probes'] if p['world_xy']==xy];vals.append(100*sum(p['old_rejected'] for p in rr)/sum(p['points'] for p in rr))
ax[0].bar(['A区','B区','C区'],vals,color=col[0]);ax[0].set(title='原门限在问题区域实际拒绝率很低\n不能把量纲问题当成本轮变红主因',ylabel='旧门限拒绝点比例 / %');ax[0].grid(axis='y',alpha=.2)
t=json.load(open(O/'TIME_OFFSET_PROBE.json'))['rows']
for desk,label in [(False,'整帧同一位姿'),(True,'逐点时间补偿（时间定义假设）')]:
 rr=[r for r in t if r['deskew']==desk];ax[1].plot([r['offset_s'] for r in rr],[r['heldout_rms_clipped12cm_m']*100 for r in rr],label=label)
ax[1].axvline(0,c='gray',ls='--');ax[1].set(title='额外时间偏移没有在留出扫描上稳定改善',xlabel='额外位姿时间偏移 / s',ylabel='留出扫描截断RMS / cm');ax[1].legend();ax[1].grid(alpha=.2);fig.suptitle('保留排除证据：没有直接换门限或给时间戳加一个“最好看”的偏移',fontsize=16);save(fig,'04_alternatives_not_adopted')
fig,ax=plt.subplots(1,3,figsize=(17,6),layout='constrained');strata=['high_coverage_low_relief','partial_coverage_low_relief','high_relief_or_occupied_context'];labels=['高覆盖低起伏','部分覆盖低起伏','高差/结构邻域'];x=np.arange(3)
for role,label,c,shift in [('old_material_changes_joint','修改前',col[0],-.16),('new_material_changes_joint','修正后',col[1],.16)]:
 vals=[S['frozen_sample_groups']['main/'+st][role] for st in strata];ax[0].bar(x+shift,vals,.32,label=label,color=c)
ax[0].set(xticks=x,xticklabels=labels,ylabel='平均八方向绝对变化≥0.1的配对数',title='同一640组主样本：139 → 43');ax[0].legend();ax[0].tick_params(axis='x',rotation=15)
for st,label in zip(strata,labels):
 rr=[r for r in pairs if r['cohort']=='main' and r['stratum']==st and r['new_valid_both']];ax[1].scatter([r['old_change_mean_abs'] for r in rr],[r['new_change_mean_abs'] for r in rr],s=15,alpha=.5,label=label)
ax[1].plot([0,1],[0,1],'--',c='gray');ax[1].axhline(.1,c='gray',ls=':',lw=.8);ax[1].set(xlabel='修改前变化量',ylabel='修正后变化量',title='对角线上方是退步，必须保留');ax[1].legend(fontsize=9)
g=S['frozen_sample_groups']['main/all'];ax[2].bar(['明显变化→稳定','稳定→明显变化','仍明显变化'],[g['old_material_to_new_stable'],g['old_stable_to_new_material'],g['new_material_changes_joint']-g['old_stable_to_new_material']],color=['#488b63','#c65d4c','#d7ab59']);ax[2].set(title='101组改善，5组退步\n640/640对仍有效，没有靠改成未知减少计数',ylabel='配对数');ax[2].tick_params(axis='x',rotation=15)
for a in ax:a.grid(axis='y',alpha=.2)
fig.suptitle('冻结样本复查：不重新选“好看”的窗口；输出稳定性不等于真实通行准确率',fontsize=16);save(fig,'05_frozen_samples_before_after')
fig,ax=plt.subplots(3,1,figsize=(13,11),layout='constrained')
for a,xy in zip(ax,[[-.48,12.24],[-3.,13.],[-1.,18.]]):
 for case,style in [('original_moving','-'),('plus20_moving','--')]:
  for role,c,label in [('old',col[0],'修改前'),('new',col[1],'修正后')]:
   rr=[r for r in targets if r['case']==case and r['role']==role and r['xy']==xy];a.plot([r['t_s'] for r in rr],[r['min8'] if r['valid'] else np.nan for r in rr],style,c=c,label=label+(' 原过滤' if case=='original_moving' else ' +20cm'),lw=1.6)
 a.axhline(.5,c='gray',ls=':');a.axvspan(26,30,color='#e9e5da',alpha=.4);a.set(title='固定世界位置 '+str(xy)+' m',ylabel='八方向中最低T',ylim=(0,1.03));a.grid(alpha=.2)
ax[0].legend(ncol=2);ax[-1].set_xlabel('移动录包时间 / s');fig.suptitle('关注位置的完整可用时段：未知不连线；阴影是先前关注片段\n高分仅说明当前网络响应，不能替代车辆通过标签',fontsize=15);save(fig,'06_fixed_world_targets')
key='original_moving';xy=[-.48,12.24];indices=[47,52];fig,ax=plt.subplots(2,3,figsize=(16,10),layout='constrained')
for row,role in enumerate(['old','new']):
 probs=[]
 for colidx,index in enumerate(indices):
  z,r=data(key,role,index);i,j=np.rint(120+(z['center']-xy)/float(z['resolution'])).astype(int);h=z['local_elevation'][i:i+51,j:j+51];known=np.isfinite(h);ii,jj=np.indices(h.shape);A=np.c_[ii[known]*.04,jj[known]*.04,np.ones(known.sum())];res=h.copy();res[known]-=A@np.linalg.lstsq(A,h[known],rcond=None)[0];im=ax[row,colidx].imshow(res[::-1,::-1].T*100,origin='lower',extent=[-1.02,1.02,-1.02,1.02],vmin=-5,vmax=5,cmap='coolwarm',interpolation='nearest');ax[row,colidx].set(title=names[row]+f' t={r["t_s"]:.2f}s\n去平面残差，仅用于展示',xlabel='局部世界X / m',ylabel='局部世界Y / m');fig.colorbar(im,ax=ax[row,colidx],label='cm',shrink=.7);probs.append([float(z['ht_dir_'+str(k)][i,j]) for k in range(8)])
 for p,label in zip(probs,['前帧','后帧']):ax[row,2].plot(np.arange(8)*45,p,'o-',label=label)
 ax[row,2].axhline(.5,c='gray',ls='--');ax[row,2].set(xticks=np.arange(8)*45,xlabel='方向 / °',ylabel='实际发布T',ylim=(0,1.03),title=names[row]+'：同一点八方向');ax[row,2].legend();ax[row,2].grid(alpha=.2)
fig.suptitle('原关注样本：整帧位姿对齐降低拼接纹理，不是把残差图送回网络\n实际网络仍读取原流程高程；模型、0.5门槛、过滤范围均保持不变',fontsize=15);save(fig,'07_original_failure_patch')
cm=plt.get_cmap('RdYlGn').copy();cm.set_bad('#6f777c')
for role,name in [('old','08_before_eight_directions'),('new','09_after_eight_directions')]:
 z,r=data('plus20_moving',role,52);fig,ax=plt.subplots(2,4,figsize=(17,9),layout='constrained');valid=z['ht_valid']>.5;center=z['center'];res=float(z['resolution']);extent=[center[0]-4.82,center[0]+4.82,center[1]-4.82,center[1]+4.82]
 for k,a in enumerate(ax.flat):
  p=z['ht_dir_'+str(k)];im=a.imshow(np.where(valid,p,np.nan)[::-1,::-1].T,origin='lower',extent=extent,cmap=cm,vmin=0,vmax=1,interpolation='nearest');a.set(title=str(k*45)+'°',xlabel='世界X / m',ylabel='世界Y / m');robot=z['robot'];foot=np.array([[-.4825,-.29],[.4825,-.29],[.4825,.29],[-.4825,.29]]);c,s=np.cos(robot[3]),np.sin(robot[3]);foot=foot@np.array([[c,s],[-s,c]])+robot[:2];a.add_patch(Polygon(foot,fill=False,edgecolor='#00d8ff',linewidth=.8));a.plot(xy[0],xy[1],'o',ms=3,c='black')
 fig.colorbar(im,ax=list(ax.flat),shrink=.65,label='HT T：红0 → 黄0.5 → 绿1；灰=未知');fig.suptitle(('修改前' if role=='old' else '配准修正后')+f'：+20cm版本 t={r["t_s"]:.2f}s 的八方向图\n同一录包帧、同一世界范围；原生0.04m格，nearest显示；青框=记录车体，黑点=原关注位置',fontsize=15);save(fig,name)
regress=sorted([r for r in pairs if r['cohort']=='main' and r['old_change_mean_abs']<.1 and r['new_change_mean_abs']>=.1],key=lambda r:r['new_change_mean_abs']-r['old_change_mean_abs'],reverse=True);fig,ax=plt.subplots(1,3,figsize=(17,6),layout='constrained')
for a,sample in zip(ax,regress[:3]):
 for role,c in [('old',col[0]),('new',col[1])]:
  p=np.array(sample[role+'_prob8']);a.plot(np.arange(8)*45,p[0],'-',c=c,label=('修改前' if role=='old' else '修正后')+'·前帧');a.plot(np.arange(8)*45,p[1],'--',c=c,label=('修改前' if role=='old' else '修正后')+'·后帧')
 a.axhline(.5,c='gray',ls=':');a.set(title=f'样本{sample["sample"]} {sample["case"]}\nXY={sample["xy"]}\n变化量 {sample["old_change_mean_abs"]:.3f} → {sample["new_change_mean_abs"]:.3f}',xlabel='方向 / °',ylabel='T',xticks=np.arange(8)*45,ylim=(0,1.03));a.legend(fontsize=8);a.grid(alpha=.2)
fig.suptitle('反例必须展示：5组原本较稳定的主样本变得更不稳定，图示其中3组\n没有真实通行标注，不能把所有分数变化都判成感知错误；也不能宣称问题全部解决',fontsize=15);save(fig,'10_regressions_not_hidden')
obs=json.load(open(O/'OBSTACLE_CONTROL_REGRESSION.json'));fig,ax=plt.subplots(1,2,figsize=(15,6),layout='constrained');rr=obs['existing_feature_cases'];x=np.arange(len(rr));ax[0].bar(x-.16,[r['height_m']*100 for r in rr],.32,label='合成实际高度');ax[0].bar(x+.16,[r['existing_feature_peak_m']*100 for r in rr],.32,label='实际CUDA映射后高度');ax[0].set(xticks=x,xticklabels=[str(round(r['height_m']*100))+'cm' for r in rr],title='已经观测的窄障碍保留\n刚体对齐没有把高度栅格抹平',ylabel='cm');ax[0].legend()
rr=obs['new_feature_cases'];a=np.array([r['first_half_height_scan_zero_based'] for r in rr])*.1;ax[1].bar(x-.16,a[:,0],.32,label='完美位姿·旧融合');ax[1].bar(x+.16,a[:,1],.32,label='配准修正');ax[1].set(xticks=x,xticklabels=[str(round(r['height_m']*100))+'cm' for r in rr],title='另一个未解决问题：新障碍接收迟滞\n到达半高度的延迟，合成10Hz扫描',ylabel='s');ax[1].legend()
for a in ax:a.grid(axis='y',alpha=.2)
fig.suptitle('结构与反例检查：2～50cm合成窄障碍；不能用地面变绿代替安全验收\n新障碍融合迟滞是旧融合中已存在的独立缺陷，本轮未声称修好',fontsize=15);save(fig,'11_obstacle_preservation_and_latency')
fig,ax=plt.subplots(1,2,figsize=(15,6),layout='constrained');keys=list(S['cases']);labels=['静止原过滤','移动原过滤','静止+20cm','移动+20cm'];vals=[S['cases'][k]['registration_status_counts'].get('APPLIED',0) for k in keys];total=[S['cases'][k]['integrated_scans'] for k in keys];x=np.arange(4);ax[0].bar(x,vals,label='应用配准',color=col[1]);ax[0].bar(x,np.array(total)-vals,bottom=vals,label='门控保留原位姿',color='#bfc8ce');ax[0].set(xticks=x,xticklabels=labels,ylabel='完整源扫描数',title='无可靠配准证据时保留原输入\n静止两组没有应用修正');ax[0].legend()
med=[S['cases'][k]['registration_ms_p50_p95'][0] for k in keys];p95=[S['cases'][k]['registration_ms_p50_p95'][1] for k in keys];ax[1].bar(x,med,label='中位',color=col[0]);ax[1].plot(x,p95,'o-',label='P95',c=col[1]);ax[1].set(xticks=x,xticklabels=labels,ylabel='ms',title='本机新增配准计算耗时\nx86离线值，不是ARM或在线实时性验收');ax[1].legend()
for a in ax:a.tick_params(axis='x',rotation=15);a.grid(axis='y',alpha=.2)
fig.suptitle('四组均完整处理：117＋64＋117＋64张输出；原始两段录包约64.3s和35.7s\n关闭开关的64帧逐数组复现原结果；没有车辆闭环或探索收益结论',fontsize=15);save(fig,'12_scope_coverage_and_timing')
pdf.close();(O/'FIGURES.json').write_text(json.dumps(files,indent=2)+'\n');print('figures',len(files),flush=True)
