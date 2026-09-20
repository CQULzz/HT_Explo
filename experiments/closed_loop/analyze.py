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
  row={'condition':condition,'rep':rep,'planning_median_ms':float(np.median([v['overall_ms'] for v in d['planning_cycles']])) if d['planning_cycles'] else None,'final':d['final'],'duration_s':float(t[-1]),'initial_xy':xy[0].tolist(),'new_surface_voxels':samples[-1]['new_reference_hits'],'total_surface_voxels':samples[-1]['reference_hits'],'surface_coverage_pct':samples[-1]['reference_hit_pct'],'distance_m':float(ds.sum()),'steep_distance_m':float(ds[steep].sum()),'steep_distance_fraction':float(ds[steep].sum()/ds.sum()) if ds.sum()>0 else None,'stationary_window_fraction':float(stationary.mean()),'active_stationary_s':float(np.sum(np.diff(t,prepend=t[0])*stationary*np.array([not r['finished'] for r in samples]))),'outside_samples':int(outside.sum()),'final_home_distance_m':float(np.linalg.norm(xy[-1]-np.array(protocol['terrain']['spawn_ground_xyz'][:2]))),'finished':d['finished'],'finish_time_s':d['finish_time_s'],'scans':samples[-1]['scans'],'ht_allowed_fraction':sum(r['allowed'] is True for r in samples)/len(samples) if condition=='ht' else None};rows.append(row);tracks[f'{condition}_{rep}']=(xy,t,np.array([r['new_reference_hits'] for r in samples]))
 summary={'runs':rows,'means':{c:{k:float(np.mean([r[k] for r in rows if r['condition']==c])) for k in ['new_surface_voxels','total_surface_voxels','surface_coverage_pct','distance_m','steep_distance_m','stationary_window_fraction','active_stationary_s','final_home_distance_m']} for c in ['baseline','ht']}};a.results.joinpath('summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 plt.rcParams['font.family']=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc').get_name();plt.rcParams['axes.unicode_minus']=False
 fig,axs=plt.subplots(1,2,figsize=(12,5));im=axs[0].imshow(h,extent=(-10.5,10.5,-10.5,10.5),cmap='terrain',origin='upper');fig.colorbar(im,ax=axs[0],label='高程（m）');axs[0].contour(np.linspace(-10.5,10.5,513),np.linspace(10.5,-10.5,513),slope,levels=[15],colors='gray',linewidths=.4)
 for name,(xy,t,coverage) in tracks.items():
  color='#bf25b0' if name.startswith('ht') else '#e67e22';style='-' if name.endswith('1') else '--';label=name.replace('baseline','TARE').replace('ht','TARE+HT');axs[0].plot(xy[:,0],xy[:,1],style,color=color,label=label,linewidth=2);axs[0].scatter(*xy[-1],color=color,s=30,edgecolors='white',zorder=5);axs[1].plot(t,coverage,style,color=color,label=label)
 axs[0].set(title='山地闭环轨迹（灰线：15°坡度）',xlabel='X（m）',ylabel='Y（m）');axs[0].legend(fontsize=8);axs[1].set(title='计时开始后新增地形表面体素',xlabel='时间（s）',ylabel='0.5 m 参考体素数');axs[1].legend(fontsize=8);axs[1].grid(alpha=.2);fig.suptitle('真实八方向学生模型 + TARE：山地闭环试验');fig.tight_layout();fig.savefig(a.results/'comparison.png',dpi=170);plt.close(fig)
 lines=['# 山地真实 HT 闭环试验','','同一 CMU 山地场景，在线激光高程图，真实八方向学生网络；两组运行相同推理负载，仅改变 ht_enabled。HT 权重 1，地图超时 3 秒，其余参数一致。','','|组别|重复|新增地形体素|总地形覆盖率|路径 m|陡坡路径 m|未完成时停滞秒|结束距起点 m|','|---|---:|---:|---:|---:|---:|---:|---:|']
 for r in rows:lines.append(f'|{r["condition"]}|{r["rep"]}|{r["new_surface_voxels"]}|{r["surface_coverage_pct"]:.1f}%|{r["distance_m"]:.2f}|{r["steep_distance_m"]:.2f}|{r["active_stationary_s"]:.1f}|{r["final_home_distance_m"]:.2f}|')
 lines+=['','## 限制','',('- 本轮两组均使用向下扩展至 −75° 的 64 线配置，正式对照还通过渲染掩码屏蔽机器人自身视觉几何。这是理想化近地面感知条件，不是 CMU 默认雷达或真实 Scout 传感器配置。未读取地形真值作为 HT 输入。' if protocol.get('downward_lidar') else '- 本轮使用 CMU 原始窄垂直视场雷达；HT 启动区域高程缺测，按未知区域门控停车。'),'- 这是小样本试运行，TARE 内部随机源未固定，不能当作稳定提升百分比。','- 陡坡是独立场景高程在约 0.08 m 高斯尺度平滑后坡度 >15° 的描述性指标，不是 Scout 实际失效阈值；CMU 车辆由位姿服务驱动，车体/运动学也未校准成训练数据的 Scout 平台，无法用这轮结果证明碰撞、翻车或打滑率。','- 地形来自现有训练域，不代表未见地形泛化。只使用一个地形。','- 关闭 HT 与开启 HT 也使用各自既有的路径/航点逻辑；本试验测当前集成整体效果，不能独立归因于学习网络。','- 参考覆盖只统计地形表面，不含围墙。停滞定义为过去约 10 秒累计位移 <0.2 m，起始不足 10 秒不计停滞，主表仅累计尚未宣布完成时的停滞秒数；不会把不动造成的陡坡距离下降称为成功。','- 初始可见表面已经计入总覆盖；新增体素单独扣除计时起点的观测。','']
 b=summary['means']['baseline'];h=summary['means']['ht']
 conclusions=['## 本轮结论','',f'各 {sum(r["condition"]=="ht" for r in rows)} 次、每次 {protocol["duration_s"]:g} 秒的适配传感器对照中，平均总地形覆盖率 TARE {b["surface_coverage_pct"]:.2f}%、TARE+HT {h["surface_coverage_pct"]:.2f}%，相差 {h["surface_coverage_pct"]-b["surface_coverage_pct"]:.2f} 个百分点。平均新增表面体素从 {b["new_surface_voxels"]:.1f} 降到 {h["new_surface_voxels"]:.1f}，相对变化 {(h["new_surface_voxels"]/b["new_surface_voxels"]-1)*100:.2f}%。', '', '这轮没有显示当前 HT 集成提升探索效果。两组陡坡暴露都为零，无法从该指标判断筛选改善。本轮 HT 返航表现需结合表中结束距起点判断；较短路径可能包含未返航因素，不能直接称为效率提升。TARE 的重复间差异也较大，因此不作统计显著性结论。', '', '返航代码线索：sensor_coverage_planner_ground.cpp:988 在 HT 开启时直接返回局部路径，绕过后面的返航拼接。此轮未修改被测 TARE 算法。默认窄视场雷达下另有起点高程盲区问题，见 closed_loop/README.md 与 pilot3/4。',''] if protocol.get('downward_lidar') else []
 a.results.joinpath('REPORT.md').write_text('\n'.join(lines+conclusions));print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
