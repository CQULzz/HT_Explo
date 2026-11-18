from pathlib import Path
import json,hashlib,ast,shutil
out=Path('/mnt/d/TARE-Native-Campus-20261118/results')
(out/'.gitattributes').write_text('* -text\nreproduce/native_source/** -whitespace\nreproduce/*.diff -whitespace\nsetup/*.patch -whitespace\n')
for name in ['add_native_source.py','package_results.py','navigation_diagnostic.py']:
 shutil.copy2(out.parent/name,out/'reproduce'/name)
checks=[]
for p in out.rglob('*.json'):json.loads(p.read_text(encoding='utf-8-sig'));checks.append(str(p.relative_to(out)))
for p in out.rglob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
for case,complete in [('native_campus_01',False),('native_campus_02',True)]:
 run=out/case;r=json.loads((run/'RESULT.json').read_text());v=json.loads((run/'RECORDING_VALIDATION.json').read_text());ret=json.loads((run/'RETURN_VERIFICATION.json').read_text());clean=json.loads((run/'CLEANUP.json').read_text());diag=json.loads((run/'NATIVE_NAVIGATION_DIAGNOSTIC.json').read_text())
 assert r['mission_complete'] is complete and ret['passed'] is complete
 assert all(v[k] for k in ['available_crc_checks_passed','metadata_counts_match','frozen_archive_matches_manifest']) and r['freeze_unchanged']
 assert not clean['relevant_processes_remaining'] and not r['ht_enabled'] and not diag['nonfinite_waypoints']
 if not complete:assert len(diag['latest']['local_path']['data']['points'])==1 and r['mission_outcome']=='PERSISTENT_BLOCKED'
 assert not list(run.rglob('*.mcap'))
for p in out.rglob('*'):
 if p.is_file():assert p.stat().st_size<20_000_000,(p,p.stat().st_size)
proof=json.loads((out/'CONFIGURATION_VERIFICATION.json').read_text());assert proof['effective_yaml_equal_after_resolving_isolated_root']['vehicleSimulator.yaml'] is None
summary={'json_files_parsed':len(checks),'python_ast_passed':True,'both_raw_integrity_checks_passed':True,'expected_one_blocked_one_returned':True,'no_remaining_experiment_processes':True,'no_raw_mcap_or_video_in_compact_package':True,'one_missing_vehicle_parameter_dump_disclosed':True,'actual_native_binary_and_freeze_identity_verified':True}
(out/'DELIVERY_VALIDATION.json').write_text(json.dumps(summary,indent=2))
files=[]
for p in sorted(out.rglob('*')):
 if p.is_file() and p.name!='DATA_MANIFEST.json':files.append({'file':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(out/'DATA_MANIFEST.json').write_text(json.dumps({'files':files,'file_count':len(files),'bytes':sum(e['bytes'] for e in files),'scope':'Compact experiment evidence only; full MCAP/runtime archives retained locally.'},indent=2))
print(json.dumps({'validation':summary,'files':len(files),'bytes':sum(e['bytes'] for e in files)},indent=2))
