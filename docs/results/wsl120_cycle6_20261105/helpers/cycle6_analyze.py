from pathlib import Path
import argparse,subprocess,sys,json,csv,collections,hashlib
R=Path('/home/w_lzz/ht-iterations-20261105');C=R/'cycle6';P=R/'repo';ap=argparse.ArgumentParser();ap.add_argument('label');ap.add_argument('--comparison');a=ap.parse_args();run=C/a.label
assert (run/'RUN_RESULT.json').exists()
commands=[('bag',[sys.executable,str(R/'navigation-fix/verify_bag.py'),str(run)]),('video',['/usr/bin/python3',str(R/'navigation-fix/verify_video.py'),str(run)]),('analysis',[sys.executable,str(P/'tools/pcd_sim/analyze_runs.py'),a.label,'--root',str(C)]+(['--comparison',a.comparison] if a.comparison else []))]
for name,cmd in commands:
 with (R/'setup'/f'cycle6-{a.label}-{name}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
for name in ['delivery_age','state_diagnostics']:
 old=Path('/mnt/d/HT-Resume')/('cycle2_'+name+'.py');target=Path('/mnt/d/HT-Resume')/('cycle6_'+name+'.py');target.write_text(old.read_text().replace('ht-iterations-20261105/cycle2','ht-iterations-20261105/cycle6'))
 with (R/'setup'/f'cycle6-{a.label}-{name}.log').open('w') as f:subprocess.run([sys.executable,str(target),a.label],stdout=f,stderr=subprocess.STDOUT,check=True)
summary=json.loads((C/'reports'/a.label/'SUMMARY.json').read_text());manifest=json.loads((run/'manifest.json').read_text());result=json.loads((run/'RUN_RESULT.json').read_text());mapper=json.loads((run/'mapper_stats.json').read_text()) if (run/'mapper_stats.json').exists() else None
rows=list(csv.DictReader((run/'metrics.csv').open()));diag=json.loads((run/'STATE_DIAGNOSTICS.json').read_text())
context={'tested_commit':manifest['project_head'],'mapper_mode':manifest['mapper_executor_mode'],'seed':manifest['seed'],'local_raw':str(run),'primary_metric':'unchanged 1Hz HT producer source_age_at_publish_s','auxiliary_full_rate_delivery_age':'DELIVERY_AGE.json, not pure publisher timing or replacement metric','sim_duration':result['actual_duration_sim_s'],'command':next(x['command'] for x in json.loads((C/'BUDGET.json').read_text())['runs'] if x['label']==a.label),'frozen_config_sha256':{str(Path(k).name):v for k,v in manifest['frozen_hashes'].items() if k.startswith(str(R/'runtime'))},'first_internal_completed_s':diag['first_completed_elapsed_s'],'raw_publication_status':'LOCAL_ONLY_NO_RELEASE; DO_NOT_PRUNE'}
(run/'EXPERIMENT_CONTEXT.json').write_text(json.dumps(context,indent=2))
compact={'label':a.label,'mode':manifest['mapper_executor_mode'],'seed':manifest['seed'],'collection':{'duration_s':result['actual_duration_sim_s'],'error':result['error'],'nonzero':result['managed_shutdown_nonzero'],'changed':result['frozen_files_changed']},'age':summary['map_source_age_at_publish_s'],'callback_s':summary['ht_callback_service_s'],'distance_m':summary['done']['distance'],'volume_m3':summary['done']['free_volume'],'mission_completed':summary['done']['mission_completed'],'first_completed_s':diag['first_completed_elapsed_s'],'final_reason':diag['final_runtime_reason'],'wall_s':result['wall_elapsed'],'mapper':mapper}
(run/'COMPACT.json').write_text(json.dumps(compact,indent=2));print(json.dumps(compact,indent=2))
