from pathlib import Path
import json,html,subprocess,hashlib,shutil,textwrap
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
root=Path.cwd();out=root/'docs/results/ht_guide_handoff_10min_2026-10-19';hist=out/'history';raw=root/Path('/tmp/ht_guide38_run_path').read_text().strip();trial=raw/'garage';read=lambda p:json.loads(p.read_text());versions=read(root/'docs/version_history.json')
shutil.copy2(root/'docs/version_history.json',hist/'version_catalog.json')
plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
with PdfPages(hist/'introduction.pdf') as pdf:
 for title,lines in [
  ('HT 项目逐次修改与多角度验证',[
   '38个阶段说明 · 31组完整600秒记录 · 室内与车库分开比较',
   '本轮阶段38：修复全局巡游与局部窗口交接，不再因列表移除放弃未完成任务。',
   '阶段37 → 38：体积4522.625 → 5807.000m³（+28.4%），里程179.78 → 202.58m。',
   '末分钟新增8.375 → 553.750m³；原地转向27.0% → 20.3%。',
   '记录引导切换34 → 6次；1m格重复进入29.2% → 14.7%。',
   '退步：搜索超时47 → 81次，最长停车1.15 → 1.40s；仍低于阶段36的7900.375m³。',
   '13项采集核验、4项CTest通过；9000帧/600秒视频完整解码。',
   '技术采集通过不等于全场景探索完成。当前仍EXPLORING，仅一轮车库。']),
  ('如何解读这些图',[
   '单轮累计体积没有减少：它是历史自由体素并集；波动的是不同闭环试验的最终结果。',
   '轨迹不同、回访比例不同，里程相近也可能产生完全不同的新增观测。',
   '新增地图更快，不等于全局任务决策更高效；本轮只修复确定的交接语义错误。',
   '相同环境、近似相同起点、0.5m/s上限、源秒采样、0.5m自由体素近似口径。',
   '每版本一次闭环，不是多次统计，不证明所有提升来自单一机制。',
   '原地转向、完全停车、阻塞、返航与完成分开；失败轮保留，不只展示最好结果。',
   '早期未保存可统一展示的600秒曲线，保留原验证说明，不补造数字。',
   '附体积/里程曲线、每分钟新增、同尺度轨迹、任务状态、时延、资源、回访及版本表。',
   '完整数据与视频：github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-guide-handoff'])]:
  fig=plt.figure(figsize=(11.7,8.3));fig.text(.07,.90,title,fontsize=23,weight='bold');y=.80
  for line in lines:fig.text(.07,y,line,fontsize=12);y-=.075
  pdf.savefig(fig);plt.close(fig)
files=[hist/'introduction.pdf',out/'comparison/guide_handoff_comparison.pdf']
files += [hist/f'{scene}_{n:02}_{suffix}.pdf' for scene in ['garage','indoor'] for n,suffix in [(1,'overview'),(2,'curves'),(3,'minute_gain'),(4,'motion'),(5,'latency'),(6,'trajectories'),(7,'mission'),(8,'resources'),(9,'efficiency')]]
files += sorted(hist.glob('all_versions_*.pdf'))
assert all(p.exists() for p in files)
subprocess.run(['pdfunite',*[str(p) for p in files],str(hist/'all_comparisons.pdf')],check=True)
info=subprocess.check_output(['pdfinfo',str(hist/'all_comparisons.pdf')],text=True);(hist/'pdf_info.txt').write_text(info)
titles=['多指标总览','累计体积与里程','每分钟新增观测','停车、转向、倒车','规划与地图延迟分布','同尺度实际轨迹','探索、阻塞、返航、完成','CPU与内存','有效增益与回访']
figures=[('garage','../comparison/guide_handoff_comparison','阶段36/37/38任务交接与探索对比')]
for scene in ['garage','indoor']:
 for n,title in enumerate(titles,1):
  p=next(hist.glob(f'{scene}_{n:02}_*.png'));figures.append((scene,p.stem,('车库' if scene=='garage' else '室内')+' · '+title))
figures += [('versions',p.stem,'每版修改、验证和已知问题') for p in sorted(hist.glob('all_versions_*.png'))]
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>HT历次修改与阶段38结果</title><style>body{font:16px system-ui,sans-serif;margin:0;background:#f1f4f7;color:#183344}header,main{max-width:1200px;margin:auto;padding:28px}header,nav,figure{background:white}nav{position:sticky;top:0;padding:12px;z-index:1}button,a.pill{display:inline-block;margin:4px;padding:9px 15px;border:1px solid #b9c9d3;border-radius:7px;background:white;color:#173d53;text-decoration:none;cursor:pointer}.note{background:#fff3df;padding:15px}figure{margin:20px 0;padding:16px;border-radius:10px}img{width:100%;height:auto}figcaption{margin:10px 0;font-weight:600}a{color:#165f88}</style><header><h1>HT历次修改 · 多角度探索对比</h1><p>38个阶段说明、31组完整600秒记录、含本轮23张对比图。</p><p class="note">阶段38修复全局/局部任务交接：体积较37提高28.4%，回访与转向减少；仍低于36，搜索超时增多。单轮累计体积没有倒退，不宣称所有波动消失。</p><a class="pill" href="all_comparisons.pdf">合并PDF图册（25页）</a><a class="pill" href="../REPORT.md">本轮报告</a><a class="pill" href="measurements.csv">指标CSV</a><a class="pill" href="version_data_coverage.csv">全部版本表</a><a class="pill" href="../garage/camera_h264.mp4">600秒视频</a></header><nav><button onclick="pick('all')">全部</button><button onclick="pick('garage')">车库</button><button onclick="pick('indoor')">历次室内</button><button onclick="pick('versions')">每版改动与缺陷</button></nav><main>'''
for scene,stem,title in figures:page+=f'<figure data-scene="{scene}"><figcaption>{html.escape(title)} <a href="{stem}.png">PNG</a> · <a href="{stem}.pdf">PDF</a></figcaption><a href="{stem}.png"><img loading="lazy" src="{stem}.png" alt="{html.escape(title)}"></a></figure>'
page+='''</main><script>function pick(s){document.querySelectorAll('figure').forEach(x=>x.hidden=s!=='all'&&x.dataset.scene!==s)}</script></html>'''
(hist/'index.html').write_text(page)
with (hist/'REPORT.md').open('a') as f:f.write('\n## 阶段38任务交接修正\n\n[本轮报告](../REPORT.md) · [25页PDF](all_comparisons.pdf) · [浏览图册](index.html)。对比37体积+28.4%、回访减少，但搜索超时增多且仍低于36，不把性能或结果变动宣称全部消失。\n\n![目标、轨迹和新增观测](../comparison/guide_handoff_comparison.png)\n')
for name in ['plot_ht_revision_history.py','plot_ht_revision_efficiency.py']:
 shutil.copy2(root/'presentations'/name,out/name);shutil.copy2(root/'presentations'/name,trial/name)
shutil.copy2('/tmp/finalize_guide38_reports.py',out/'finalize_guide38_reports.py');shutil.copy2('/tmp/finalize_guide38_reports.py',trial/'finalize_guide38_reports.py')
checksums={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file() and p.name!='files_sha256.json'}
(out/'files_sha256.json').write_text(json.dumps(checksums,ensure_ascii=False,indent=2)+'\n')
print(info);print('SHA-indexed',len(checksums),'files')
