from pathlib import Path
import json,numpy as np,matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
O=Path(__file__).parent;F=O/'figures';font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc';font_manager.fontManager.addfont(font);plt.rcParams.update({'font.family':font_manager.FontProperties(fname=font).get_name(),'axes.unicode_minus':False,'font.size':11,'pdf.fonttype':42});z=np.load(O/'MATCHED_CONTROL_OUTPUTS.npz');meta=json.loads((O/'MATCHED_CONTROL_SAMPLES.json').read_text());sample=meta[0]['sample'];i,j=np.indices((51,51));ramp=(i-25)*.04;ramp=ramp.astype(np.float32);ramp/=ramp.std();noise=z['exact_rms_noise_units'][0];a=ramp*.01;b=noise*.01;ga=np.r_[np.diff(a,axis=0).ravel(),np.diff(a,axis=1).ravel()];gb=np.r_[np.diff(b,axis=0).ravel(),np.diff(b,axis=1).ravel()];fig,ax=plt.subplots(2,2,figsize=(12,10),layout='constrained')
for x,h,t in [(ax[0,0],a,'同样高度RMS=1cm：平缓倾斜'),(ax[0,1],b,'同样高度RMS=1cm：IID细碎起伏')]:
 im=x.imshow(h.T*100,origin='lower',extent=[-1.02,1.02,-1.02,1.02],cmap='coolwarm',vmin=-3,vmax=3,interpolation='nearest');fig.colorbar(im,ax=x,shrink=.7,label='添加的高程扰动/cm');x.set(title=t,xlabel='局部坐标/m',ylabel='局部坐标/m')
ax[1,0].hist(abs(ga)*100,bins=np.linspace(0,4,41),histtype='step',linewidth=2,label='平缓倾斜');ax[1,0].hist(abs(gb)*100,bins=np.linspace(0,4,41),histtype='step',linewidth=2,label='细碎起伏');ax[1,0].set(yscale='log',xlabel='相邻4cm格子的高度差绝对值/cm',ylabel='相邻格对数（对数轴）',title='高度RMS相同，相邻高度差却不同');ax[1,0].legend();ax[1,0].grid(alpha=.2)
for kind,label,color in [('planar_tilt','平缓倾斜','#386cb0'),('iid_exact_rms','IID细碎起伏','#e66101')]:
 ids=[k for k,x in enumerate(meta) if x['sample']==sample and x['kind']==kind and x['sigma_m']==.01];p=z['predictions'][ids]
 for row in p:ax[1,1].plot(np.arange(8)*45,row,'o-',alpha=.5,color=color)
 ax[1,1].plot([],[],label=label,color=color)
ax[1,1].axhline(.5,color='black',linestyle='--');ax[1,1].set(xticks=np.arange(8)*45,xlabel='方向θ/deg',ylabel='类别分数T',ylim=(-.02,1.03),title='同一拟合坡面上，4种倾斜与5种随机起伏');ax[1,1].legend();ax[1,1].grid(alpha=.2)
fig.suptitle('示意图④：模型首先读取相邻高度差，高度RMS不是唯一决定因素\n因此试验支持“空间形态敏感”，不能仅凭1cm扰动就断言模型错误或地面不安全',fontsize=15);fig.savefig(F/'13_equal_rms_gradient_schematic.png',dpi=155);fig.savefig(O/'gradient_schematic.pdf');plt.close(fig)
metrics={'height_rms_m':[float(a.std()),float(b.std())],'adjacent_abs_p99_cm':[float(np.quantile(abs(ga),.99)*100),float(np.quantile(abs(gb),.99)*100)],'scope':'Illustration from already-run matched-control inputs, not a new physical experiment'};(O/'GRADIENT_SCHEMATIC_METRICS.json').write_text(json.dumps(metrics,indent=2)+'\n');print(metrics)
