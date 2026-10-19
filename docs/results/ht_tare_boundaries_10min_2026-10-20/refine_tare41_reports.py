from pathlib import Path
import json,csv,hashlib,subprocess,shutil
import numpy as np
r=Path.cwd();out=r/'docs/results/ht_tare_boundaries_10min_2026-10-20';raw=r/Path('/tmp/ht_tare41_run_path').read_text().strip()/'garage';hist=out/'history'
gains=[];baselines=[]
for label,folder in [('39',r/'docs/results/ht_successor_pruning_10min_2026-10-20/garage'),('40',r/'docs/results/ht_tare_waypoint_10min_2026-10-20/garage'),('41',out/'garage')]:
 v=list(csv.DictReader((folder/'observation_volume.csv').open()));g=float(v[-1]['observed_free_volume_m3'])-float(np.interp(540,[float(x['time_s']) for x in v],[float(x['observed_free_volume_m3']) for x in v]));gains.append(g)
 first=next(x for x in v if float(x['observed_free_volume_m3'])>0);baselines.append(dict(stage=label,first_observation_time_s=float(first['time_s']),first_observation_volume_m3=float(first['observed_free_volume_m3'])))
p=out/'REPORT.md';s=p.read_text();s=s.replace('记录级违例0。','记录级违例0。683次HT尝试中592次到达，34次达时间上限、57次达展开上限；这些失败针对某个前缀，缩短同一分支后592个实际规划周期均发布了非空路线，不能把91次尝试失败当作91次停车。')
s=s.replace('## 验证范围与剩余问题\n\n',f'''## 验证范围与剩余问题

末60秒新增观测：阶段39为{gains[0]:.3f}m³、40为{gains[1]:.3f}m³、41为{gains[2]:.3f}m³。本轮累计量高于40，但末分钟收益和移动距离低于40，原地转向比例更高。地图年龄P95也由40的0.618s增至0.743s，最大值由1.592s降至1.246s；都是1Hz采样，不是所有时刻上界。

''')
s=s.replace('扣除首帧','扣除首个实际观测帧');p.write_text(s)
for dst in [out,raw]:
 shutil.copy2(r/'presentations/plot_tare_route_comparison.py',dst/'plot_tare_route_comparison.py');shutil.copy2('/tmp/refine_tare41_reports.py',dst/'refine_tare41_reports.py')
 (dst/'initial_observation_baselines.json').write_text(json.dumps(baselines,ensure_ascii=False,indent=2)+'\n')
files=[out/'tare_waypoint_audit/architecture.pdf',out/'tare_waypoint_audit/routes.pdf']+sorted((out/'comparison').glob('*.pdf'))
files += [hist/f'{scene}_{n:02}_{suffix}.pdf' for scene in ['garage','indoor'] for n,suffix in [(1,'overview'),(2,'curves'),(3,'minute_gain'),(4,'motion'),(5,'latency'),(6,'trajectories'),(7,'mission'),(8,'resources'),(9,'efficiency')]]
files+=sorted(hist.glob('all_versions_*.pdf'))
temp=hist/'all_comparisons.refined.pdf';subprocess.run(['pdfunite',*[str(p) for p in files],str(temp)],check=True);temp.replace(hist/'all_comparisons.pdf')
(hist/'pdf_info.txt').write_text(subprocess.check_output(['pdfinfo',str(hist/'all_comparisons.pdf')],text=True))
checks={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'files_sha256.json'};(out/'files_sha256.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(last60_gains=gains,initial_observation_baselines=baselines,checksummed_files=len(checks)),ensure_ascii=False,indent=2))
