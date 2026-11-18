from pathlib import Path
import ast
old=Path('/mnt/d/HT-Campus-Repeat-1200s-20261118');work=Path('/mnt/d/HT-Recovery-Campus-1200s-20261118');oldroot='/home/lzz/ht_campus_repeat_1200s_20261118';newroot='/home/lzz/ht_recovery_campus_1200s_20261118';oldcase='explicit_labels_campus_repeat_1200s_01';newcase='recovery_campus_1200s_01';baseline=oldroot+'/runs/'+oldcase;first='/home/lzz/ht_campus_1200s_20261118/runs/explicit_labels_campus_1200s_03'
for n in ['postprocess_long.py','assess_coverage.py','summarize_stop.py','summarize_planning_chain.py','end_motion.py','verify_clock.py','analyze_backtracking.py']:
 s=(old/n).read_text(encoding='utf-8-sig').replace(first,'__BASELINE__').replace(oldroot,newroot).replace(oldcase,newcase).replace('__BASELINE__',baseline).replace('ROS_DOMAIN_ID=219','ROS_DOMAIN_ID=209').replace('DISPLAY=:106','DISPLAY=:107')
 s=s.replace("b'/ht_campus_1200s_20261118/'", "b'/ht_recovery_campus_1200s_20261118/'")
 (work/n).write_text(s.rstrip()+'\n');ast.parse(s)
commands={'postprocess.sh':f'{newroot}/venv/bin/python /mnt/d/HT-Recovery-Campus-1200s-20261118/postprocess_long.py > {newroot}/setup/postprocess.log 2>&1','coverage.sh':f'{newroot}/venv/bin/python /mnt/d/HT-Recovery-Campus-1200s-20261118/assess_coverage.py > {newroot}/setup/coverage.log 2>&1','audit.sh':f"{newroot}/venv/bin/python '/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/tools/cmu_minimal/audit_commands.py' {newroot}/runs/{newcase} --radius 0.58182230175 > {newroot}/setup/audit.log 2>&1"}
for n,cmd in commands.items():(work/n).write_text('set -e\nsource '+newroot+'/env.sh\n'+cmd+'\n')
print('Prepared post-run validation, no active runtime mutation')
