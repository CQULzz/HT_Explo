from pathlib import Path
import json
r=Path('/home/lzz/ht_recovery_campus_1200s_20261118/runs/recovery_campus_1200s_01')
for n in ['ANALYSIS.json','PHASES.json','RECOVERY_ANALYSIS.json','BACKTRACKING.json','COMMAND_AUDIT.json','CLEANUP.json','RECORDING_VALIDATION.json']:
 p=r/n
 if not p.exists():print(n,'pending');continue
 a=json.loads(p.read_text())
 if n=='BACKTRACKING.json':a=a['repeat']
 elif n=='COMMAND_AUDIT.json':a={k:a[k] for k in ['counts','passed','violations']}
 elif n=='RECORDING_VALIDATION.json':a={k:a[k] for k in ['messages','frozen_files','available_crc_checks_passed','metadata_counts_match','frozen_archive_matches_manifest']}
 elif n=='CLEANUP.json':a={k:a[k] for k in ['clean_child_exit','relevant_processes_remaining','launcher_codes']}
 print(n,json.dumps(a,ensure_ascii=False))
p=r.parent.parent/'analysis/COVERAGE_ASSESSMENT.json';print('coverage',p.read_text() if p.exists() else 'pending')
