from pathlib import Path
import json,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path('/home/lzz/ht_only_20261111');r=json.loads((ROOT/'analysis/source_rejections/RESULT.json').read_text());start=json.loads((ROOT/'runs/a_user_pcd_600s_02/observations/START.json').read_text())['clock'];frames=r['frames'];t=np.array([f['stamp']-start for f in frames]);v=np.array([[c['variance_m2'] for c in f['cells']] for f in frames]);z=np.array([[c['source_elevation_m'] for c in f['cells']] for f in frames]);at=r['rejection_observation_time']-start
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False});fig,axes=plt.subplots(2,1,figsize=(10,7),sharex=True)
for k in range(v.shape[1]):axes[0].plot(t,v[:,k],lw=1);axes[1].plot(t,(z[:,k]-z[0,k])*1000,lw=1)
axes[0].axhline(.25,c='red',ls='--',label='质量拒绝门限：方差 > 0.25m²');axes[0].set_ylabel('源地图方差 / m²');axes[0].legend();axes[1].set_ylabel('相对首帧高度变化 / mm');axes[1].set_xlabel('任务时间 / s')
for ax in axes:ax.axvline(at,c='#334155',ls=':');ax.grid(alpha=.2)
fig.suptitle('8个后来成为硬占用的格点：高度变化小，方差跨门限后被质量拒绝');fig.text(.5,.015,'精确原始高程消息的离线复核，未修改参数；直接解释拒绝链路，尚未确定源方差突增的上游原因。',ha='center',fontsize=10);fig.tight_layout(rect=(0,.04,1,.94));fig.savefig(ROOT/'delivery/source_variance_rejection.png',dpi=170)
print('max per-cell height change during window (m)',float(np.max(np.abs(z-z[0]))))
