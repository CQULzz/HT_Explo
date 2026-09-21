#!/usr/bin/env python3
"""Independent geometry/coverage/stall scoring, not neural self-scoring."""
import argparse,json
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter,map_coordinates
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
HERE=Path(__file__).resolve().parent

def main():
 ap=argparse.ArgumentParser();ap.add_argument('results',type=Path);a=ap.parse_args();terrain=np.load(HERE/'assets/terrain.npz');h=terrain['height'];slope=np.degrees(np.arctan(np.hypot(*np.gradient(gaussian_filter(h,2),21/512))))
 rows=[];tracks={};protocol=json.loads((a.results/'protocol.json').read_text())
 for condition,rep in protocol['order']:
  case=a.results/f'{condition}_{rep}';d=json.loads((case/'metrics.json').read_text());samples=d['samples'];
  if not d['final']:raise ValueError(f'Incomplete trial: {case}')
  xy=np.array([r['position'][:2] for r in samples]);t=np.array([r['t'] for r in samples]);ds=np.linalg.norm(np.diff(xy,axis=0),axis=1);angle=map_coordinates(slope,[(10.5-xy[:,1])*512/21,(xy[:,0]+10.5)*512/21],order=1,mode='nearest');steep=angle[1:]>15
  outside=(np.abs(xy)>10.5).any(axis=1);stationary=np.zeros(len(t),bool)
  for i in range(len(t)):
   j=np.searchsorted(t,t[i]-10)
   if t[i]-t[j]>=9.5:stationary[i]=ds[j:i].sum()<.2
  row={'condition':condition,'rep':rep,'planning_median_ms':float(np.median([v['overall_ms'] for v in d['planning_cycles']])) if d['planning_cycles'] else None,'final':d['final'],'duration_s':float(t[-1]),'initial_xy':xy[0].tolist(),'new_surface_voxels':samples[-1]['new_reference_hits'],'total_surface_voxels':samples[-1]['reference_hits'],'surface_coverage_pct':samples[-1]['reference_hit_pct'],'distance_m':float(ds.sum()),'steep_distance_m':float(ds[steep].sum()),'steep_distance_fraction':float(ds[steep].sum()/ds.sum()) if ds.sum()>0 else None,'stationary_window_fraction':float(stationary.mean()),'active_stationary_s':float(np.sum(np.diff(t,prepend=t[0])*stationary*np.array([not r.get('mission_completed',r['finished']) for r in samples]))),'outside_samples':int(outside.sum()),'final_home_distance_m':float(np.linalg.norm(xy[-1]-np.array(protocol['terrain']['spawn_ground_xyz'][:2]))),'mission_completed':d.get('mission_completed'),'mission_completion_time_s':d.get('mission_completion_time_s'),'fallback_s':float(sum((samples[i+1]['t']-v['t']) for i,v in enumerate(samples[:-1]) if v.get('execution_status')=='GEOMETRIC_FALLBACK')),'startup_prior_s':float(sum((samples[i+1]['t']-v['t']) for i,v in enumerate(samples[:-1]) if v.get('execution_status')=='STARTUP_PRIOR')),'final_execution_status':samples[-1].get('execution_status'),'finished':d['finished'],'finish_time_s':d['finish_time_s'],'scans':samples[-1]['scans'],'ht_allowed_fraction':sum(r['allowed'] is True for r in samples)/len(samples) if condition=='ht' else None};rows.append(row);tracks[f'{condition}_{rep}']=(xy,t,np.array([r['new_reference_hits'] for r in samples]))
 summary={'runs':rows,'means':{c:{k:float(np.mean([r[k] for r in rows if r['condition']==c])) for k in ['new_surface_voxels','total_surface_voxels','surface_coverage_pct','distance_m','steep_distance_m','stationary_window_fraction','active_stationary_s','final_home_distance_m']} for c in sorted({r['condition'] for r in rows})}};a.results.joinpath('summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 plt.rcParams['font.family']=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc').get_name();plt.rcParams['axes.unicode_minus']=False
 fig,axs=plt.subplots(1,2,figsize=(12,5));im=axs[0].imshow(h,extent=(-10.5,10.5,-10.5,10.5),cmap='terrain',origin='upper');fig.colorbar(im,ax=axs[0],label='高程（m）');axs[0].contour(np.linspace(-10.5,10.5,513),np.linspace(10.5,-10.5,513),slope,levels=[15],colors='gray',linewidths=.4)
 for name,(xy,t,coverage) in tracks.items():
  color='#bf25b0' if name.startswith('ht') else '#e67e22';style='-' if name.endswith('1') else '--';label=name.replace('baseline','TARE').replace('ht','TARE+HT');axs[0].plot(xy[:,0],xy[:,1],style,color=color,label=label,linewidth=2);axs[0].scatter(*xy[-1],color=color,s=30,edgecolors='white',zorder=5);axs[1].plot(t,coverage,style,color=color,label=label)
 axs[0].set(title='山地闭环轨迹（灰线：15°坡度）',xlabel='X（m）',ylabel='Y（m）');axs[0].legend(fontsize=8);axs[1].set(title='计时开始后新增地形表面体素',xlabel='时间（s）',ylabel='0.5 m 参考体素数');axs[1].legend(fontsize=8);axs[1].grid(alpha=.2);fig.suptitle('真实八方向学生模型 + TARE：山地闭环试验');fig.tight_layout();fig.savefig(a.results/'comparison.png',dpi=170);plt.close(fig)
 lines=['# 山地真实 HT 闭环验证','','CMU 仿真；在线雷达输入真实八方向学生模型，两组均运行推理。配置与源码差异见 protocol.json。','','|组别|重复|新增地形体素|总覆盖率|轨迹 m|结束距起点 m|真正完成|降级秒|结束执行状态|','|---|---:|---:|---:|---:|---:|---|---:|---|']
 for r in rows:lines.append(f'|{r["condition"]}|{r["rep"]}|{r["new_surface_voxels"]}|{r["surface_coverage_pct"]:.2f}%|{r["distance_m"]:.2f}|{r["final_home_distance_m"]:.2f}|{r["mission_completed"]}|{r["fallback_s"]:.1f}|{r["final_execution_status"]}|')
 lines+=['','## 解释边界','','- /exploration_finish 只表示探索阶段结束；/mission_completed 才表示返航到家且停车确认。旧数据没有后者时显示 None，不能据旧布尔值判定返航成功。','- 短轨迹或零陡坡暴露不能单独当成效率/安全提升。必须结合完成情况、覆盖与停滞判断。','- 几何降级时间从 0.2 秒采样估算；启动先验不算网络预测。','- 本轮传感器：'+('向下扩展且屏蔽自身回波，属于理想化配置。' if protocol.get('downward_lidar') else 'CMU 原始窄垂直视场雷达。'),'- 仅一个训练域地形、少量重复，且 TARE 内部随机源未固定，不用于显著性或泛化结论。','- 坡度 >15° 为独立几何描述，不是实车失效标签。CMU 位姿驱动车辆不能验证打滑、翻车或轮胎接触。','- HT 开关还影响局部路径求解与航点逻辑，整体对照不能把差异全部归因于学习代价；可额外用 --weight 0 做相同 HT 图/执行逻辑消融。','']
 conclusions=[]
 if 'baseline' in summary['means'] and 'ht' in summary['means']:
  b=summary['means']['baseline'];h=summary['means']['ht'];delta=h['surface_coverage_pct']-b['surface_coverage_pct']
  conclusions=['## 数值对照','',f'平均总覆盖率：TARE {b["surface_coverage_pct"]:.2f}%，TARE+HT {h["surface_coverage_pct"]:.2f}%，变化 {delta:+.2f} 个百分点。']
  if b['new_surface_voxels']>0:conclusions+=[f'新增地形体素：{b["new_surface_voxels"]:.1f} → {h["new_surface_voxels"]:.1f}，相对变化 {(h["new_surface_voxels"]/b["new_surface_voxels"]-1)*100:+.2f}%。']
  conclusions+=['这只是当前小样本结果；是否改善必须同时查看上表任务完成情况。']
 a.results.joinpath('REPORT.md').write_text('\n'.join(lines+conclusions));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
