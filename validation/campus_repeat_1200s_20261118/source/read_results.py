import json,pathlib
r=pathlib.Path('/home/lzz/ht_campus_repeat_1200s_20261118'); p=r/'runs/explicit_labels_campus_repeat_1200s_01'
for n in ['ANALYSIS.json','PHASES.json','COMMAND_AUDIT.json','RECORDING_VALIDATION.json','CLEANUP.json']:
 print(n);print(json.dumps(json.loads((p/n).read_text()),ensure_ascii=False)[:15000])
print('coverage', (r/'analysis/COVERAGE_ASSESSMENT.json').read_text());print('budget',(r/'BUDGET.json').read_text())
print('logs');print((r/'setup/coverage.log').read_text()[-1000:])
