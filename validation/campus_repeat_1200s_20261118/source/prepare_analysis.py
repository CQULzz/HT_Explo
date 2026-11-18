from pathlib import Path
old=Path('/mnt/d/HT-Campus-1200s-20261118');new=Path('/mnt/d/HT-Campus-Repeat-1200s-20261118');root='/home/lzz/ht_campus_repeat_1200s_20261118';previous='/home/lzz/ht_campus_1200s_20261118';case='explicit_labels_campus_repeat_1200s_01';baseline=previous+'/runs/explicit_labels_campus_1200s_03'
for n in ['postprocess_long.py','assess_coverage.py','summarize_stop.py','end_motion.py','verify_clock.py']:
 s=(old/n).read_text();s=s.replace('/home/lzz/ht_labels_300s_20261116/runs/explicit_labels_campus_300s_01','__BASELINE_RUN__');s=s.replace(previous,root).replace('explicit_labels_campus_1200s_03',case).replace('__BASELINE_RUN__',baseline).replace('ROS_DOMAIN_ID=221','ROS_DOMAIN_ID=219').replace('DISPLAY=:105','DISPLAY=:106');(new/n).write_text(s)
commands={'postprocess.sh':f'{root}/venv/bin/python /mnt/d/HT-Campus-Repeat-1200s-20261118/postprocess_long.py > {root}/setup/postprocess.log 2>&1','coverage.sh':f'{root}/venv/bin/python /mnt/d/HT-Campus-Repeat-1200s-20261118/assess_coverage.py > {root}/setup/coverage.log 2>&1','audit.sh':f"{root}/venv/bin/python '/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/tools/cmu_minimal/audit_commands.py' {root}/runs/{case} --radius 0.58182230175 > {root}/setup/audit.log 2>&1"}
for name,cmd in commands.items():(new/name).write_text('set -e\nsource '+root+'/env.sh\n'+cmd+'\n')
import ast
for p in new.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'))
print('Read-only post-run checks prepared; previous20min used as baseline')
