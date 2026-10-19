from pathlib import Path
import json,html,subprocess,hashlib,shutil,textwrap
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
root=Path.cwd();out=root/'docs/results/ht_successor_pruning_10min_2026-10-20';hist=out/'history';raw=root/Path('/tmp/ht_prune39_run_path').read_text().strip();trial=raw/'garage';read=lambda p:json.loads(p.read_text());versions=read(root/'docs/version_history.json')
shutil.copy2(root/'docs/version_history.json',hist/'version_catalog.json')
plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
experiment=read(out/'EXPERIMENT.json');metrics=experiment['metrics'];search=experiment['search'];manifest=read(out/'garage/manifest.json');summary=read(out/'garage/summary.json')
with PdfPages(hist/'introduction.pdf') as pdf:
 for title,lines in [
  ('为什么当前HT仍落后于原版TARE',[
   '代码确认的结构差异：HT分支绕过原局部TSP，改为到单个目标的XYθ路线。',
   '原版优化一组视点访问顺序；当前单点收益/到达时间没有完整保留多视点覆盖。',
   '全局引导多按直线距离评分，必要绕行可能先远离目标，缺少拓扑路线接力。',
   '车库视点候选格约48×48m；当前实际HT约9.87×9.87m，中转主要1～4m。',
   '小窗口需要全局接力；这不是认定HT窗口小就必然低效。',
   '历史原版角速度/倒车/加速度更宽松；旧180秒51.7%不是当前准确比率。',
   '硬约束会改变可用边，是否误拒、各项损失多少仍需同条件消融。',
   '后续优先：多视点覆盖排序 + 拓扑接力 + 可执行XYθ成本与硬验证。']),
  ('阶段39：搜索开销优化与完整600秒结果',[
   '把原来最终也会丢弃的支配边提前剪掉；所有可接受边仍逐段硬检查。',
   '冻结公开输入：相同256展开，查询约11700→3800；成功路线另有18组合成对照。',
   '反例保留：4个目标在原预算下新旧仍均超时，不能把加速当作可达性修复。',
   f"实际代码{manifest['git_head'][:7]}；车库600秒{summary['distance_m']:.2f}m / {metrics['observed_free_volume_m3']:.3f}m³。",
   f"本轮搜索超时{search['termination'].get('TIME_LIMIT',0)}次，累计剪去{int(search['dominated_edges_pruned'])}条边。",
   f"最长完全停车{metrics['longest_zero_command_s']:.3f}s；末分钟里程{metrics['distance_last60_m']:.3f}m。",
   '13项采集检查、4项CTest及视频完整解码通过；改善和退步均见后续图表。',
   '每版本一次闭环；本轮没有恢复多视点/拓扑覆盖结构，不能宣称追平原版。'])]:
  fig=plt.figure(figsize=(11.7,8.3));fig.text(.07,.90,title,fontsize=23,weight='bold');y=.80
  for line in lines:fig.text(.07,y,line,fontsize=12);y-=.075
  pdf.savefig(fig);plt.close(fig)
files=[hist/'introduction.pdf',out/'comparison/pruning_comparison.pdf']
files += [hist/f'{scene}_{n:02}_{suffix}.pdf' for scene in ['garage','indoor'] for n,suffix in [(1,'overview'),(2,'curves'),(3,'minute_gain'),(4,'motion'),(5,'latency'),(6,'trajectories'),(7,'mission'),(8,'resources'),(9,'efficiency')]]
files += sorted(hist.glob('all_versions_*.pdf'))
assert all(p.exists() for p in files)
subprocess.run(['pdfunite',*[str(p) for p in files],str(hist/'all_comparisons.pdf')],check=True)
info=subprocess.check_output(['pdfinfo',str(hist/'all_comparisons.pdf')],text=True);(hist/'pdf_info.txt').write_text(info)
titles=['多指标总览','累计体积与里程','每分钟新增观测','停车、转向、倒车','规划与地图延迟分布','同尺度实际轨迹','探索、阻塞、返航、完成','CPU与内存','有效增益与回访']
figures=[('garage','../comparison/pruning_comparison','阶段36/38/39：搜索剪枝与实际探索对比')]
for scene in ['garage','indoor']:
 for n,title in enumerate(titles,1):
  p=next(hist.glob(f'{scene}_{n:02}_*.png'));figures.append((scene,p.stem,('车库' if scene=='garage' else '室内')+' · '+title))
figures += [('versions',p.stem,'每版修改、验证和已知问题') for p in sorted(hist.glob('all_versions_*.png'))]
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>HT历次修改与阶段39结果</title><style>body{font:16px system-ui,sans-serif;margin:0;background:#f1f4f7;color:#183344}header,main{max-width:1200px;margin:auto;padding:28px}header,nav,figure{background:white}nav{position:sticky;top:0;padding:12px;z-index:1}button,a.pill{display:inline-block;margin:4px;padding:9px 15px;border:1px solid #b9c9d3;border-radius:7px;background:white;color:#173d53;text-decoration:none;cursor:pointer}.note{background:#fff3df;padding:15px}figure{margin:20px 0;padding:16px;border-radius:10px}img{width:100%;height:auto}figcaption{margin:10px 0;font-weight:600}a{color:#165f88}</style><header><h1>HT历次修改 · 多角度探索对比</h1><p>39个阶段说明、32组完整600秒记录、含本轮23张对比图。</p><p class="note">阶段39：减少支配边的冗余硬检查。与原版TARE的多视点覆盖/拓扑接力结构差距尚未解决；本轮实际改善与退步见报告。旧180秒51.7%不是当前准确比率。</p><a class="pill" href="all_comparisons.pdf">合并PDF图册（25页）</a><a class="pill" href="../REPORT.md">本轮报告</a><a class="pill" href="measurements.csv">指标CSV</a><a class="pill" href="version_data_coverage.csv">全部版本表</a><a class="pill" href="../garage/camera_h264.mp4">600秒视频</a></header><nav><button onclick="pick('all')">全部</button><button onclick="pick('garage')">车库</button><button onclick="pick('indoor')">历次室内</button><button onclick="pick('versions')">每版改动与缺陷</button></nav><main>'''
for scene,stem,title in figures:page+=f'<figure data-scene="{scene}"><figcaption>{html.escape(title)} <a href="{stem}.png">PNG</a> · <a href="{stem}.pdf">PDF</a></figcaption><a href="{stem}.png"><img loading="lazy" src="{stem}.png" alt="{html.escape(title)}"></a></figure>'
page+='''</main><script>function pick(s){document.querySelectorAll('figure').forEach(x=>x.hidden=s!=='all'&&x.dataset.scene!==s)}</script></html>'''
(hist/'index.html').write_text(page)
with (hist/'REPORT.md').open('a') as f:f.write('\n## 阶段39支配边搜索优化与TARE差距\n\n[本轮报告](../REPORT.md) · [25页PDF](all_comparisons.pdf) · [浏览图册](index.html)。本轮仅改搜索支配检查的顺序；多视点覆盖序列和拓扑接力尚未恢复，同控制约束的原版配对仍缺。\n\n![目标、轨迹和新增观测](../comparison/pruning_comparison.png)\n')
for name in ['plot_ht_revision_history.py','plot_ht_revision_efficiency.py']:
 shutil.copy2(root/'presentations'/name,out/name);shutil.copy2(root/'presentations'/name,trial/name)
shutil.copy2('/tmp/finalize_prune39_reports.py',out/'finalize_prune39_reports.py');shutil.copy2('/tmp/finalize_prune39_reports.py',trial/'finalize_prune39_reports.py')
checksums={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p!=out/'files_sha256.json'}
(out/'files_sha256.json').write_text(json.dumps(checksums,ensure_ascii=False,indent=2)+'\n')
print(info);print('SHA-indexed',len(checksums),'files')
