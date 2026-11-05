from pathlib import Path
import json,csv,shutil,sys,hashlib
R=Path('/home/w_lzz/ht-iterations-20261105');P=R/'repo';root=R/'cycle2';summaryroot=root/'reports';destroot=P/'docs/results/wsl120_cycle2_20261105'
for label in sys.argv[1:]:
 run=root/label;summary=json.loads((summaryroot/label/'SUMMARY.json').read_text());manifest=json.loads((run/'manifest.json').read_text());dest=destroot/label;dest.mkdir(exist_ok=True)
 rows=list(csv.DictReader((run/'metrics.csv').open()));complete=next((float(x['elapsed_sim']) for x in rows if x['mission_completed']=='1'),None)
 audit=[x for x in (run/'navigation.log').read_text().splitlines() if any(k in x for k in ['TARE_SELECTION ','TARE_COMPLETION ','TARE_RANDOM '])]
 context={'tested_commit':manifest['project_head'],'seed':manifest.get('seed'),'seed_scope':manifest.get('seed_scope'),'requested_duration':manifest['requested_duration_sim_s'],'mode':manifest['ht_processing_mode'],'render_backend':manifest['render_backend'],'actual_renderer':summary['run_result'].get('actual_gl_renderers'),'local_raw':str(run),'publication_status':'LOCAL_ONLY_NO_RELEASE_OR_DEPLOYMENT','first_internal_completed_s':complete,'config_sha256':{name:hashlib.sha256((R/'runtime'/name).read_bytes()).hexdigest() for name in ['scene.sdf','mapper_core.yaml','mapper_setup.yaml','candidate_extrinsics.yaml']},'run_command':next((x.get('command') for x in json.loads((root/'BUDGET.json').read_text())['formal_runs'] if x['id']==label),None)}
 (run/'EXPERIMENT_CONTEXT.json').write_text(json.dumps(context,indent=2));(dest/'EXPERIMENT_CONTEXT.json').write_text(json.dumps(context,indent=2))
 for name in ['RUN_RESULT.json','BAG_VERIFICATION.json','VIDEO_VERIFICATION.json','manifest.json']:shutil.copy2(run/name,dest/name)
 for file in (summaryroot/label).glob('*'):
  if file.is_file():shutil.copy2(file,dest/file.name)
 (dest/'completion_evidence.log').write_text('\n'.join(audit)+'\n')
 age=summary['map_source_age_at_publish_s'];svc=summary['ht_callback_service_s'];done=summary['done'];res=summary['run_result']
 (dest/'REPORT.md').write_text(f'''# {label}\n\n实测代码 `{manifest['project_head']}`，TARE/Gazebo种子{manifest.get('seed')}；配置哈希、原始采集和完整命令见EXPERIMENT_CONTEXT/manifest。ROS/GPU调度仍随机，不视为逐帧确定性。\n\n请求120秒，实录{done['elapsed_sim']}秒，总墙钟{res['wall_elapsed']:.3f}秒；冻结变化{res['frozen_files_changed']}；采集错误{res['error']}，非零退出{res['managed_shutdown_nonzero']}。退出异常不隐去，不宣称干净通过。\n\nHT回调P50/P95 {svc['p50']*1000:.3f}/{svc['p95']*1000:.3f}ms；发布源龄P50/P95 {age['p50']:.4f}/{age['p95']:.4f}s；GT累计里程{done['distance']:.4f}m，自由体积{done['free_volume']:.4f}m³；内部完成={done['mission_completed']}，首次完成遥测{complete}s。里程含初始化沉降，体积是采样射线体素近似，内部COMPLETED不是全场景真值覆盖证书。\n\nMCAP消息计数/可用CRC/SHA256、视频完整解码检查分别见核验JSON。完整原始录包/视频/CSV/快照/资源日志留在本机，未发布Release，未远端备份前不清理。只把精简记录提交Git。候选应与同种子基线配对，不把两种子的轨迹差异或单次体积当成因果收益。\n''')
 for f in dest.iterdir():
  if f.is_file():f.chmod(0o644)
 print(label,'P95 age',age['p95'],'nonzero shutdown',res['managed_shutdown_nonzero'])
shutil.copy2(root/'BUDGET.json',destroot/'BUDGET.json');(destroot/'BUDGET.json').chmod(0o644)
