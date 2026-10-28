from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch,FancyArrowPatch
O=Path(__file__).parent;F=O/'figures';F.mkdir(exist_ok=False);font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc';font_manager.fontManager.addfont(font);plt.rcParams.update({'font.family':font_manager.FontProperties(fname=font).get_name(),'axes.unicode_minus':False,'font.size':11,'axes.titlesize':12,'pdf.fonttype':42})
samples=json.loads((O/'SAMPLES.json').read_text());metrics=json.loads((O/'METRICS.json').read_text());S=json.loads((O/'SUMMARY.json').read_text());selection=json.loads((O/'SELECTION_SUMMARY.json').read_text());z=np.load(O/'OUTPUTS.npz');inp=np.load(O/'INPUTS.npz');p=z['predictions'];vn=json.loads((O/'VARIANTS.json').read_text());v={k:p[:,i] for i,k in enumerate(vn)};N=len(samples);main=np.array([s['cohort']=='main' for s in samples]);datasets=[d['id'] for d in json.loads((O/'DATASETS.json').read_text())];dnames=['静止·原过滤','静止·+20cm','移动·原过滤','移动·+20cm'];strata=['high_coverage_low_relief','partial_coverage_low_relief','high_relief_or_occupied_context'];snames=['高覆盖/低起伏','部分覆盖/低起伏','高差/结构邻域'];colors=['#386cb0','#7fc97f','#fdc086'];delta=np.array([m['mean_abs_delta'] for m in metrics]);er=np.array([m['mean_abs_residual_effect'] for m in metrics]);ep=np.array([m['mean_abs_plane_effect'] for m in metrics]);inter=np.array([m['mean_abs_interaction'] for m in metrics]);changed=delta>=.1
pdf=PdfPages(O/'all_figures.pdf');saved=[]
def save(fig,name):
 fig.savefig(F/(name+'.png'),dpi=155);pdf.savefig(fig);plt.close(fig);saved.append(name+'.png')
def masks(dataset=None,stratum=None,cohort='main'):
 return np.array([(dataset is None or s['dataset']==dataset) and (stratum is None or s['stratum']==stratum) and (cohort is None or s['cohort']==cohort) for s in samples])
def hshow(ax,h,title,unit='m',bounds=None):
 if bounds is None:bounds=(float(h.min()),float(h.max()))
 im=ax.imshow(h[::-1,::-1].T,origin='lower',extent=[-1.02,1.02,-1.02,1.02],cmap='coolwarm' if unit=='cm' else 'terrain',vmin=bounds[0],vmax=bounds[1],interpolation='nearest');ax.set(title=title,xlabel='相对目标世界X / m',ylabel='相对目标世界Y / m');fig=ax.figure;fig.colorbar(im,ax=ax,shrink=.72,label=unit);return im
# Choose representative via an already recorded rule, not a new handpicked success.
reps=json.loads((O/'REPRESENTATIVE_CASES.json').read_text());ref=next(x['sample'] for x in reps if x['role']=='allgreen_to_allred');ha,hb=inp['height'][ref];pa,pb=z['plane'][ref];ra,rb=z['residual'][ref]
fig,ax=plt.subplots(2,2,figsize=(12,10),layout='constrained');fields=[ha,pa+rb,pb+ra,hb];keys=['actual_before','old_plane_new_residual','new_plane_old_residual','actual_after'];titles=['Pa＋Ra：实际前帧','Pa＋Rb：只换局部起伏','Pb＋Ra：只换拟合平面','Pb＋Rb：实际后帧'];lo=min(float(h.min()) for h in fields);hi=max(float(h.max()) for h in fields)
for a,h,k,t in zip(ax.flat,fields,keys,titles):hshow(a,h,t+f'\n八方向均分={v[k][ref].mean():.3f}','m',(lo,hi))
fig.suptitle('示意图①：完整2×2输入对换，位置/模型/门槛不变\n横向改变R，纵向改变P；R是去平面局部起伏，不能预先认定为噪声',fontsize=16);save(fig,'01_factorial_design')
fig,ax=plt.subplots(1,3,figsize=(16,5.6),layout='constrained');hshow(ax[0],hb,'实际输入H','m',(float(hb.min()),float(hb.max())));hshow(ax[1],pb,'最小二乘拟合平面P','m',(float(hb.min()),float(hb.max())));mx=max(.5,float(abs(rb).max()*100));hshow(ax[2],rb*100,'局部起伏R＝H−P\n包含真实微地形、边缘及误差','cm',(-mx,mx));fig.suptitle('示意图②：同一个真实窗口的高度分解 H＝P＋R\n平面与原高程用米，残差用厘米；示例从新增对照中按中位变化选择',fontsize=16);save(fig,'02_height_decomposition')
fig,ax=plt.subplots(1,3,figsize=(17,6),layout='constrained');x=np.arange(4);bottom=np.zeros(4)
for st,name,c in zip(strata,snames,colors):
 counts=[S['by_dataset'][d]['strata'][st]['samples'] for d in datasets];ax[0].bar(x,counts,bottom=bottom,label=name,color=c);bottom+=counts
ax[0].set(xticks=x,xticklabels=dnames,title='640对主样本：按输入条件抽样',ylabel='窗口对数');ax[0].tick_params(axis='x',rotation=20);ax[0].legend(fontsize=9)
ctrl=['allgreen_to_allgreen','allred_to_allred','allgreen_to_allred','allred_to_allgreen'];cn=['全绿→全绿','全红→全红','全绿→全红','全红→全绿'];bottom=np.zeros(4)
for g,label in zip(ctrl,cn):
 counts=[sum(s['dataset']==d and s['cohort']!='main' and s['outcome']==g for s in samples) for d in datasets];ax[1].bar(x,counts,bottom=bottom,label=label);bottom+=counts
ax[1].set(xticks=x,xticklabels=dnames,title='192对附加对照：按输出类别抽样\n不用于估计自然发生比例',ylabel='窗口对数');ax[1].tick_params(axis='x',rotation=20);ax[1].legend(fontsize=9)
for d,label in zip(datasets,dnames):
 a=np.array([s['coverage_min'] for s in samples if s['dataset']==d and s['cohort']=='main']);ax[2].hist(a,bins=np.linspace(0,1,21),histtype='step',label=label,linewidth=1.5)
ax[2].set(title='两帧中较低的有效观测覆盖率',xlabel='51×51窗口中观测比例',ylabel='主样本数');ax[2].legend(fontsize=9);fig.suptitle('抽样覆盖：2份真实录包 × 2种处理；四个版本不是四次独立实车实验\n静止包没有符合≥98%覆盖的低起伏窗口；如实留空，没有人为补齐',fontsize=15);save(fig,'03_sampling_coverage')
fig,ax=plt.subplots(2,2,figsize=(13,10),layout='constrained');stable=[];change=[]
for d in datasets:
 ids=masks(d);stable.append(int((ids&~changed).sum()));change.append(int((ids&changed).sum()))
ax[0,0].bar(x,stable,label='八方向平均绝对变化<0.1',color='#bdbdbd');ax[0,0].bar(x,change,bottom=stable,label='平均绝对变化≥0.1',color='#e66101');ax[0,0].set(xticks=x,xticklabels=dnames,ylabel='主样本对',title='多数窗口没有发生大变化');ax[0,0].tick_params(axis='x',rotation=15);ax[0,0].legend(fontsize=9)
for st,label,c in zip(strata,snames,colors):
 ids=masks(stratum=st);ax[0,1].scatter(np.maximum(er[ids],1e-7),np.maximum(ep[ids],1e-7),s=12,alpha=.55,label=label,c=c)
q=np.geomspace(1e-7,1,100);ax[0,1].plot(q,q,'k--',lw=1);ax[0,1].plot(q,q/2,'k:',lw=1);ax[0,1].set(xscale='log',yscale='log',xlabel='局部起伏影响：八方向平均|E_R|',ylabel='平面影响：八方向平均|E_P|',title='原对换：实测残差变化影响较大');ax[0,1].legend(fontsize=9)
for i,st in enumerate(strata):
 ids=masks(stratum=st)&changed;ax[1,0].bar(i,int((ids&(er>=2*ep)).sum()),color=colors[i]);ax[1,0].text(i,int(ids.sum())+.5,f'{int(ids.sum())}/{int(masks(stratum=st).sum())}',ha='center')
ax[1,0].set(xticks=range(3),xticklabels=snames,ylabel='有明显变化且R影响≥2P的窗口对',title='139对明显变化：均满足预定“R主导”判据\n但原始P/R变化幅度并不相同，需额外公平对照')
ax[1,1].boxplot([er[main&changed],ep[main&changed],inter[main&changed]],labels=['起伏效应|E_R|','平面效应|E_P|','交互项|I|'],showfliers=True);ax[1,1].set(ylabel='八方向平均绝对分数变化',title='仅139个明显变化主样本\n没有I≥0.1的大交互，不能外推到所有地形');ax[1,1].grid(axis='y',alpha=.2);fig.suptitle('主结果：支持“本次窗口变化主要随局部起伏走”\n不等于证明这些起伏是噪声，也不等于证明真实地面不可通过',fontsize=15);save(fig,'04_factorial_effects')
fig,ax=plt.subplots(2,2,figsize=(13,9),layout='constrained')
for a,d,label in zip(ax.flat,datasets,dnames):
 for lag,mark in zip([.5,2.5,5.],['o','s','^']):
  ids=np.array([s['dataset']==d and s['cohort']=='main' and s['target_lag_s']==lag for s in samples]);a.scatter([s['t_before'] for i,s in enumerate(samples) if ids[i]],delta[ids],s=18,alpha=.55,marker=mark,label=f'间隔约{lag}s')
 a.axhline(.1,color='black',linestyle='--',linewidth=1);a.set(title=label,xlabel='前帧雷达源时间/s',ylabel='八方向平均绝对分数变化');a.legend(fontsize=9);a.grid(alpha=.2)
fig.suptitle('按时段和时间间隔展开：变化集中在部分移动窗口\n同一路段、相邻窗口会重叠；散点不是独立实车试验',fontsize=15);save(fig,'05_time_lag_variation')
fig,ax=plt.subplots(1,4,figsize=(17,5.5),layout='constrained')
for a,g,title in zip(ax,ctrl,cn):
 ids=np.array([s['cohort']!='main' and s['outcome']==g for s in samples]);a.boxplot([v[k][ids].mean(1) for k in ['actual_before','actual_after','new_plane_old_residual','old_plane_new_residual']],labels=['实际前','实际后','新P旧R','旧P新R'],showfliers=True);a.set(title=f'{title}，n={int(ids.sum())}',ylim=(-.03,1.03),ylabel='八方向平均分数');a.tick_params(axis='x',rotation=30);a.axhline(.5,color='grey',linestyle='--');a.grid(axis='y',alpha=.2)
fig.suptitle('按输出类别追加的对照：验证“稳定”“翻转”“反向恢复”\n这是有意分组的对照，不得与主样本混合估计发生率',fontsize=15);save(fig,'06_output_controls')
fig,ax=plt.subplots(1,3,figsize=(17,5.6),layout='constrained');alpha=np.array([0,.25,.5,.75,1,1.25,1.5]);curve=np.load(O/'EFFECTS.npz')['alpha_predictions']
for a,st,label in zip(ax,strata,snames):
 ids=np.flatnonzero(masks(stratum=st));c=curve[ids]
 for row in c[::max(1,len(c)//25)]:a.plot(alpha,row,c='grey',alpha=.15,lw=.7)
 q=np.quantile(c,[.25,.5,.75],axis=0);a.fill_between(alpha,q[0],q[2],alpha=.2);a.plot(alpha,q[1],'o-',label='中位数与四分位范围');a.axhline(.5,color='black',linestyle='--');a.set(title=f'{label}，n={len(ids)}',xlabel='保留的原始后帧起伏幅值 α',ylabel='八方向平均分数',ylim=(-.02,1.02));a.grid(alpha=.2);a.legend(fontsize=8)
fig.suptitle('幅值试验：H＝P_after＋αR_after，α=1是原始输入\n高差/结构邻域中36/256主样本出现α增加时分数反升>0.05；不能把R都当成噪声',fontsize=15);save(fig,'07_residual_amplitude')
fig,ax=plt.subplots(1,2,figsize=(12,6),layout='constrained')
for a,st,title in [(ax[0],'high_coverage_low_relief','高覆盖/低起伏'),(ax[1],None,'全部主样本')]:
 ids=masks(stratum=st)&z['equal_rms_valid'];xx=v['actual_after'][ids].mean(1);yy=v['equal_rms_old_pattern'][ids].mean(1);a.scatter(xx,yy,s=16,alpha=.5);a.plot([0,1],[0,1],'k--');a.set(xlim=(0,1),ylim=(0,1),xlabel='实际后帧：新P＋新R',ylabel='同RMS：新P＋旧R×(σ_new/σ_old)',title=title+f'，n={int(ids.sum())}');a.set_aspect('equal');a.grid(alpha=.2)
fig.suptitle('相同起伏RMS，不同空间分布：分数不必相同\n同一模型/新坡面；幅值匹配不能证明残差属于测量噪声',fontsize=15);save(fig,'08_equal_rms_patterns')
fig,ax=plt.subplots(1,3,figsize=(17,5.6),layout='constrained')
for a,st,label in zip(ax,strata,snames):
 ids=masks(stratum=st)&changed
 if not ids.any():a.text(.5,.5,'无满足条件样本',ha='center');continue
 vals=[np.mean(abs(v[k][ids]-v['actual_before'][ids]),axis=1) for k in ['actual_after','new_plane_old_residual','observed_only_restore','padding_only_restore']];a.boxplot(vals,labels=['实际变化','全换旧R','只换共同观测','只换后帧填值']);a.tick_params(axis='x',rotation=25);a.set(title=f'{label}，n={int(ids.sum())}',ylabel='相对原前帧剩余分数差，越小越接近');a.grid(axis='y',alpha=.2)
fig.suptitle('输入来源对照：保持其余后帧输入，只替换指定位置\n“共同观测”含有效历史；填值影响需按覆盖分层，不能只看整图缺测数量',fontsize=15);save(fig,'09_observed_vs_padding')
meta=json.loads((O/'NOISE_SAMPLES.json').read_text());npred=np.load(O/'NOISE_OUTPUTS.npz')['predictions'];ameta=json.loads((O/'MATCHED_CONTROL_SAMPLES.json').read_text());ap=np.load(O/'MATCHED_CONTROL_OUTPUTS.npz')['predictions'];fig,ax=plt.subplots(2,2,figsize=(13,10),layout='constrained');sigmas=[0,.005,.01,.015,.02,.03]
for a,base,title in [(ax[0,0],'actual_new','给实际输入叠加IID扰动'),(ax[0,1],'fitted_plane','给拟合平面叠加IID扰动')]:
 for d,label in zip(datasets[2:],dnames[2:]):
  med=[];q1=[];q3=[]
  for sig in sigmas:
   aa=npred[[i for i,s in enumerate(meta) if s['dataset']==d and s['base']==base and s['sigma_m']==sig]].mean(1);med.append(np.median(aa));q1.append(np.quantile(aa,.25));q3.append(np.quantile(aa,.75))
  a.plot(np.array(sigmas)*100,med,'o-',label=label);a.fill_between(np.array(sigmas)*100,q1,q3,alpha=.15)
 a.set(title=title,xlabel='添加扰动标准差/cm',ylabel='八方向平均分数',ylim=(0,1.04));a.axhline(.5,color='grey',linestyle='--');a.legend(fontsize=9);a.grid(alpha=.2)
for kind,label in [('planar_tilt','平缓倾斜，同RMS'),('iid_exact_rms','细碎IID，同RMS')]:
 med=[];green=[];red=[]
 for sig in sigmas:
  a=ap[[i for i,s in enumerate(ameta) if s['kind']==kind and s['sigma_m']==sig]];med.append(np.median(a.mean(1)));green.append(np.mean(a.min(1)>=.5));red.append(np.mean(a.max(1)<.5))
 ax[1,0].plot(np.array(sigmas)*100,med,'o-',label=label);ax[1,1].plot(np.array(sigmas)*100,np.array(green)*100,'o-',label=label+'：八方向全≥0.5');ax[1,1].plot(np.array(sigmas)*100,np.array(red)*100,'s--',label=label+'：八方向全<0.5')
ax[1,0].set(title='追加公平对照：高度RMS相同，组织方式不同',xlabel='添加高度RMS/cm',ylabel='八方向平均分数中位数',ylim=(0,1.04));ax[1,0].legend(fontsize=9);ax[1,0].grid(alpha=.2);ax[1,1].set(title='不要混淆“有方向低分”与“全部低分”',xlabel='添加高度RMS/cm',ylabel='受控输入占比/%',ylim=(-2,102));ax[1,1].legend(fontsize=8);ax[1,1].grid(alpha=.2)
fig.suptitle('受控扰动：32个记录窗口＋5种扰动种子，不是1920次实车试验\nIID未证明等同真实雷达误差；同RMS对照为看完主结果后预先冻结的追加试验',fontsize=15);save(fig,'10_noise_and_matched_control')
# Add a transparently selected nonmonotonic counterexample if available.
rises=np.diff(curve,axis=1).max(axis=1);idx=np.flatnonzero(main&(rises>.05))
if len(idx):reps.append({'role':'nonmonotonic_structural_counterexample','sample':int(idx[np.argmax(rises[idx])]),'selection':'post-hoc illustrative largest alpha score rise among main samples; not representative'})
(O/'PLOTTED_CASES.json').write_text(json.dumps(reps,indent=2)+'\n')
rolelabels={'allgreen_to_allred':'对照：全绿→全红','allgreen_to_allgreen':'对照：始终全绿','allred_to_allred':'对照：始终全红','allred_to_allgreen':'对照：全红→全绿','nonmonotonic_structural_counterexample':'反例：增加起伏，分数反而上升'}
for k,record in enumerate(reps):
 sample=record['sample'];s=samples[sample];h0,h1=inp['height'][sample];r0,r1=z['residual'][sample];maxres=max(.5,float(max(abs(r0).max(),abs(r1).max())*100));fig,ax=plt.subplots(2,3,figsize=(16,10),layout='constrained');low=min(h0.min(),h1.min());high=max(h0.max(),h1.max());hshow(ax[0,0],h0,'前帧完整输入','m',(low,high));hshow(ax[0,1],h1,'后帧完整输入','m',(low,high));hshow(ax[0,2],inp['observed'][sample,1].astype(float),'后帧观测历史掩码\n白/深色是数值1/0，不是新增地面','0/1',(0,1));hshow(ax[1,0],r0*100,'前帧去平面起伏','cm',(-maxres,maxres));hshow(ax[1,1],r1*100,'后帧去平面起伏','cm',(-maxres,maxres));x8=np.arange(8)
 for j,(key,label) in enumerate([('actual_before','实际前'),('actual_after','实际后'),('new_plane_old_residual','新P旧R'),('old_plane_new_residual','旧P新R')]):ax[1,2].plot(x8,v[key][sample],'o-',label=label)
 ax[1,2].axhline(.5,color='grey',linestyle='--');ax[1,2].set(xticks=x8,xticklabels=[f'{i*45}°' for i in x8],ylim=(-.02,1.02),ylabel='T分数',title='八方向完整输出');ax[1,2].legend(fontsize=9);ax[1,2].grid(alpha=.2)
 fig.suptitle(rolelabels.get(record['role'],record['role'])+f'｜样本#{sample}，{s["dataset"]}\n世界({s["world_x"]:.0f},{s["world_y"]:.0f})m，{s["t_before"]:.2f}→{s["t_after"]:.2f}s，覆盖≥{s["coverage_min"]:.1%}，'+('按组内中位变化选取' if 'counterexample' not in record['role'] else '明确标记的极端反例，不代表群体比例'),fontsize=15);save(fig,f'11_case_{k+1:02d}')
fig,ax=plt.subplots(figsize=(14,8));ax.axis('off');stages=[('原始点云/位姿','厘米起伏的物理来源\n本轮没有隔离证明'),('CuPy＋历史高程','已知输入起伏及覆盖\n真实微地形/误差尚未区分'),('HT模型分数','本轮直接干预与复现\n可检验输入响应'),('车辆真实通过','未重新开车、无通行真值\n不能由分数变化推定')]
for i,(a,b) in enumerate(stages):
 x=.02+i*.245;rect=FancyBboxPatch((x,.60),.22,.26,boxstyle='round,pad=.008',transform=ax.transAxes,facecolor=['#eeeeee','#d7e9f7','#d8f1df','#eeeeee'][i],edgecolor='#555555');ax.add_patch(rect);ax.text(x+.11,.79,a,transform=ax.transAxes,ha='center',fontsize=14,weight='bold');ax.text(x+.11,.69,b,transform=ax.transAxes,ha='center',va='center',fontsize=11)
 if i<3:ax.add_patch(FancyArrowPatch((x+.225,.73),(x+.24,.73),transform=ax.transAxes,arrowstyle='->',mutation_scale=15))
text='已得到的证据：640对主样本中139对平均变化≥0.1，均满足预定的R影响≥2P判据。\n需要保留的反证：501/640变化不足0.1；主样本只有1对“八方向全绿→全红”；36/640幅值变化非单调。\n公平对照说明：同样1cm高度RMS，平缓倾斜与IID细碎扰动的输出显著不同，空间组织很重要。\n不能得出的结论：残差一定是噪声；所有红区都是误报；某阈值已安全；这些窗口等于独立实车实验。\n下一步真正要验证：原始点云→高程的误差来源、真实小障碍保持，以及有标签的车辆通行表现。'
ax.text(.03,.45,text,transform=ax.transAxes,va='top',fontsize=13,linespacing=1.9);fig.suptitle('示意图③：证据到了哪一层，哪些因果链还没有闭合',fontsize=18);save(fig,'12_evidence_boundary')
pdf.close();(O/'FIGURES.json').write_text(json.dumps(saved,ensure_ascii=False,indent=2)+'\n');print('saved',len(saved),'PNGs and PDF',flush=True)
