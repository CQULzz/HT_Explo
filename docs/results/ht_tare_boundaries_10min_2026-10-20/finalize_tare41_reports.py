from pathlib import Path
import json,html,hashlib,shutil,subprocess
root=Path.cwd();out=root/'docs/results/ht_tare_boundaries_10min_2026-10-20';hist=out/'history';raw=root/Path('/tmp/ht_tare41_run_path').read_text().strip();trial=raw/'garage'
shutil.copy2(root/'docs/version_history.json',hist/'version_catalog.json')
files=[out/'tare_waypoint_audit/architecture.pdf',out/'tare_waypoint_audit/routes.pdf']
files += sorted((out/'comparison').glob('*.pdf'))
files += [hist/f'{scene}_{n:02}_{suffix}.pdf' for scene in ['garage','indoor'] for n,suffix in [(1,'overview'),(2,'curves'),(3,'minute_gain'),(4,'motion'),(5,'latency'),(6,'trajectories'),(7,'mission'),(8,'resources'),(9,'efficiency')]]
files += sorted(hist.glob('all_versions_*.pdf'))
assert all(p.exists() for p in files)
subprocess.run(['pdfunite',*[str(p) for p in files],str(hist/'all_comparisons.pdf')],check=True)
(hist/'pdf_info.txt').write_text(subprocess.check_output(['pdfinfo',str(hist/'all_comparisons.pdf')],text=True))
figures=[('../tare_waypoint_audit/architecture.png','本轮：原TARE多视点TSP和HT执行分工'),('../tare_waypoint_audit/routes.png','本轮：原访问序列、分支、原航点、HT局部目标和执行路线'),('../comparison/tare_architecture_comparison.png','同车库阶段39/40/41：累计、每分钟新增、速度、运动组成与每米观测'),('../comparison/tare_trajectories.png','阶段39/40/41：同尺度实际轨迹与每分钟位置')]
figures += [(p.name,p.stem) for p in sorted(hist.glob('*.png'))]
records=json.loads((hist/'measurements.json').read_text())
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>HT历次修改与原TARE访问顺序对比</title><style>body{font:16px system-ui,sans-serif;margin:0;background:#f1f4f7;color:#183344}header,main{max-width:1250px;margin:auto;padding:24px}header,figure{background:white}figure{margin:20px 0;padding:16px;border-radius:10px}img{width:100%;height:auto}figcaption{margin:10px 0;font-weight:600}a{color:#165f88}.note{background:#fff3df;padding:15px}</style><header><h1>HT历次修改 · 多角度探索对比</h1>'''
page+=f'<p>41个阶段说明，{len(records)}组完整600秒记录。</p><p class="note">阶段41保留原TARE覆盖/TSP访问顺序，HT只路由当前航点。保留退步和失败轮；每版一次闭环不证明统计优越；尚未补齐同运动约束的新原版配对。</p>'
page+='<p><a href="all_comparisons.pdf">完整PDF图册</a> · <a href="../REPORT.md">本轮报告</a> · <a href="measurements.csv">指标CSV</a> · <a href="version_data_coverage.csv">每版改动与问题表</a> · <a href="../garage/camera_h264.mp4">600秒视频</a></p></header><main>'
for file,title in figures:page+=f'<figure><figcaption>{html.escape(title)}</figcaption><a href="{file}"><img loading="lazy" src="{file}" alt="{html.escape(title)}"></a></figure>'
(hist/'index.html').write_text(page+'</main></html>')
for filename in ['plot_ht_revision_history.py','plot_ht_revision_efficiency.py']:
 shutil.copy2(root/'presentations'/filename,hist/filename);shutil.copy2(root/'presentations'/filename,trial/filename)
for filename in ['finalize_tare41_reports.py','ht_tare41_afterrun.sh']:
 shutil.copy2(Path('/tmp')/filename,out/filename);shutil.copy2(Path('/tmp')/filename,trial/filename)
# Keep download helpers on the tested software-decoder defaults.
p=root/'scripts/play_ht_multiscene.sh';s=p.read_text();old='ht_tare_waypoint_10min_2026-10-20';new='ht_tare_boundaries_10min_2026-10-20'
# Keep the previous version available by an explicit flag; only replace default.
pos=s.rfind('else\n');head=s[:pos];tail=s[pos:]
e=json.loads((out/'EXPERIMENT.json').read_text());m=e['metrics'];summary=json.loads((out/'garage/summary.json').read_text())
old_block=tail[:tail.index('\nfi')]
previous=old_block.replace('else\n',"elif [[ \"${1:-}\" == '--tare-waypoint' ]]; then\n",1)
new_block='else\n  ht_playlist="$ht_repo_root/docs/results/'+new+'/videos.m3u"\n'
new_block+=f"  printf '阶段41：原TARE多视点TSP + HT航点路由，600秒{summary['distance_m']:.2f}米、{m['observed_free_volume_m3']:.3f}立方米。\\n'\n"
new_block+="  printf '阶段40加 --tare-waypoint，阶段39加 --successor-pruning；更早选项保留。\\n'"
p.write_text(head+previous+'\n'+new_block+tail[len(old_block):])
for name in ['播放HT视频.sh','查看HT历次修改对比图.sh']:
 p=Path('/home/lzz/下载')/name;p.write_text(p.read_text().replace(old,new))
# List the exact artifact hashes after every report and plot is final.
checks={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file() and p!=out/'files_sha256.json'}
(out/'files_sha256.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(artifact_count=len(checks),record_count=len(records),pdf_files=len(files),output=str(out)),ensure_ascii=False,indent=2))
