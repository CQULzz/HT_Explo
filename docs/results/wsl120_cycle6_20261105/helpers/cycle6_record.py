from pathlib import Path
import json,csv,shutil,statistics,hashlib
R=Path('/home/w_lzz/ht-iterations-20261105');P=R/'repo';C=R/'cycle6';D=P/'docs/results/wsl120_cycle6_20261105';ledger=json.loads((C/'BUDGET.json').read_text());assert len(ledger['runs'])==6 and all(x['state']!='RUNNING' for x in ledger['runs'])
data={};frozen=[]
for entry in ledger['runs']:
 label=entry['label'];run=C/label;dest=D/label;dest.mkdir(exist_ok=True);x=json.loads((run/'COMPACT.json').read_text());data[label]=x
 manifest=json.loads((run/'manifest.json').read_text());frozen.append(manifest['frozen_hashes'])
 for name in ['COMPACT.json','RUN_RESULT.json','BAG_VERIFICATION.json','VIDEO_VERIFICATION.json','ARRAY_VERIFICATION.json','DELIVERY_AGE.json','STATE_DIAGNOSTICS.json','EXPERIMENT_CONTEXT.json','mapper_stats.json','manifest.json']:
  if (run/name).exists():shutil.copy2(run/name,dest/name)
 for f in (C/'reports'/label).glob('*'):
  if f.is_file():shutil.copy2(f,dest/f.name)
 audit=[s for s in (run/'navigation.log').read_text().splitlines() if any(k in s for k in ['TARE_SELECTION ','TARE_COMPLETION ','TARE_RANDOM '])]
 (dest/'completion_evidence.log').write_text('\n'.join(audit)+'\n')
 cpu=[];rss=[]
 for line in (run/'resources.jsonl').read_text().splitlines():
  for row in json.loads(line)['ps'].splitlines():
   fields=row.split(None,4)
   if len(fields)==5 and '/runtime/mapper_strict.py' in fields[4] and Path(fields[4].split()[0]).name.startswith('python'):
    cpu.append(float(fields[1]));rss.append(int(fields[3]))
 resource={'scope':'ps %CPU samples are process lifetime-average estimates at each sample, not instantaneous CPU or the offline benchmark process_time; RSS in KiB. Includes TF worker threads in the mapper process.','samples':len(cpu),'mapper_cpu_lifetime_percent_median':statistics.median(cpu) if cpu else None,'mapper_cpu_lifetime_percent_last':cpu[-1] if cpu else None,'mapper_peak_sampled_rss_kib':max(rss) if rss else None}
 (run/'RESOURCE_SUMMARY.json').write_text(json.dumps(resource,indent=2));(dest/'RESOURCE_SUMMARY.json').write_text(json.dumps(resource,indent=2));x['resource']=resource
 (dest/'REPORT.md').write_text(f'''# {label}

实测提交{manifest['project_head']}，种子{entry['seed']}，mapper={entry['mode']}，HT=worker；完整命令、冻结配置/二进制哈希、原始目录见EXPERIMENT_CONTEXT/manifest。ROS/GPU仍有调度波动。

实录{x['collection']['duration_s']}s，墙钟{x['wall_s']:.3f}s，采集错误{x['collection']['error']}，非零退出{x['collection']['nonzero']}，冻结变化{x['collection']['changed']}。状态账本{entry['state']}，退出异常不算干净通过。

原主指标发布源龄P50/P95 {x['age']['p50']:.4f}/{x['age']['p95']:.4f}s，HT回调P95 {x['callback_s']['p95']*1000:.3f}ms。里程{x['distance_m']:.4f}m，采样射线体积{x['volume_m3']:.3f}m³，内部完成{x['mission_completed']}，末态{x['final_reason']}。里程含初始沉降，体积非独立真值覆盖，内部COMPLETED非全场景验收证书。

MCAP计数/可用CRC/SHA及视频解码单独核验，生产者性能为既有1Hz遥测；全率录包端年龄单列，不能替代主口径。resources为ps采样估计，服务时间含锁/调度等待。原始大文件仅在本机{run}，没有Release/完整远端备份，不清理。没有实车或部署。
''')
comparison=[('seed42 first','multi42_b01','single42_c01'),('seed99','multi99_b02','single99_c02'),('seed42 repeat','multi42_r01','single42_r01')]
rows=['| pair | metric | multi | single | absolute delta | relative delta |','|---|---|---:|---:|---:|---:|']
for name,b,c in comparison:
 for metric,fn in [('HT source age P95 s',lambda x:x['age']['p95']),('GT distance m',lambda x:x['distance_m']),('Free volume m3',lambda x:x['volume_m3']),('Mapper service mean s',lambda x:x['mapper']['processing_mean_s']),('Mapper input age P95 s',lambda x:x['mapper']['queue_age_p95_s']),('Wall s',lambda x:x['wall_s'])]:
  u,v=fn(data[b]),fn(data[c]);rows.append(f'| {name} | {metric} | {u:.6f} | {v:.6f} | {v-u:+.6f} | {(v/u-1)*100:+.2f}% |')
(D/'PAIRED_COMPARISON.md').write_text('# Same-navigation paired comparison\n\n'+'\n'.join(rows)+'\n\nThree pairs, only two unique seeds. Seed42 has two repeats, seed99 one. ROS/GPU scheduling remains stochastic. No significance/generalization claim. Full captured window and teardown success are separate; all failures are listed in STATUS and BUDGET.\n')
assert all(x==frozen[0] for x in frozen),'Cross-run frozen artifacts differ; do not claim controlled comparison'
(D/'FROZEN_EQUIVALENCE.json').write_text(json.dumps({'all_six_frozen_hash_maps_equal':True,'tested_commits':sorted({x['tested_commit'] for x in ledger['runs']}),'mode_is_only_intended_changed_configuration':'mapper_executor_mode / CUPY_MAPPER_EXECUTOR_MODE; Gazebo/TARE seeds paired','frozen_file_count':len(frozen[0])},indent=2))
shutil.copy2(C/'BUDGET.json',D/'BUDGET.json');helpers=D/'helpers';helpers.mkdir(exist_ok=True)
for name in ['cycle6_run.py','cycle6_analyze.py','cycle6_delivery_age.py','cycle6_state_diagnostics.py','cycle6_record.py','cycle6_array_check.py','cycle6_plot.py']:shutil.copy2(Path('/mnt/d/HT-Resume')/name,helpers/name)
(D/'ALL_COMPACT.json').write_text(json.dumps(data,indent=2));print(json.dumps({label:{'p95':x['age']['p95'],'distance':x['distance_m'],'volume':x['volume_m3'],'reason':x['final_reason'],'nonzero':x['collection']['nonzero'],'resource':x['resource']} for label,x in data.items()},indent=2))
