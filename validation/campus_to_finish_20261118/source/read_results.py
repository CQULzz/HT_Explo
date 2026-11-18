from pathlib import Path
import json
r=Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01')
for name in ['ANALYSIS.json','RECOVERY_ANALYSIS.json','COMMAND_AUDIT.json','RECORDING_VALIDATION.json','CLEANUP.json','PHASES.json']:
 p=r/name
 if not p.exists():print(name,'pending');continue
 a=json.loads(p.read_text())
 if name=='COMMAND_AUDIT.json':a={k:a[k] for k in ['counts','passed','violations']}
 if name=='RECORDING_VALIDATION.json':a={k:a[k] for k in ['messages','frozen_files','available_crc_checks_passed','metadata_counts_match','frozen_archive_matches_manifest']}
 if name=='CLEANUP.json':a={k:a[k] for k in ['clean_child_exit','relevant_processes_remaining','launcher_codes']}
 print(name,json.dumps(a))
p=r.parent.parent/'analysis/COVERAGE_ASSESSMENT.json';print('coverage',p.read_text() if p.exists() else 'pending')
