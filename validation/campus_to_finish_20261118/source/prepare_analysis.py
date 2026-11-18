from pathlib import Path
import ast
old=Path('/mnt/d/HT-Recovery-Campus-1200s-20261118');work=Path('/mnt/d/HT-Campus-To-Finish-20261118');r0='/home/lzz/ht_recovery_campus_1200s_20261118';r1='/home/lzz/ht_campus_to_finish_20261118';c0='recovery_campus_1200s_01';c1='campus_to_finish_01';base='/home/lzz/ht_campus_repeat_1200s_20261118/runs/explicit_labels_campus_repeat_1200s_01'
for name in ['postprocess_long.py','assess_coverage.py','summarize_stop.py','summarize_planning_chain.py','end_motion.py','verify_clock.py','analyze_backtracking.py','analyze_recovery.py']:
 s=(old/name).read_text(encoding='utf-8-sig').replace(base,'__BASELINE__').replace(r0,r1).replace(c0,c1).replace('__BASELINE__',r0+'/runs/'+c0).replace('ROS_DOMAIN_ID=209','ROS_DOMAIN_ID=207').replace('DISPLAY=:107','DISPLAY=:108')
 s=s.replace("b'/ht_recovery_campus_1200s_20261118/'","b'/ht_campus_to_finish_20261118/'")
 if name=='postprocess_long.py':s=s.replace('for begin in range(0,1200,300):','for begin in range(0,int(math.ceil(analysis[\'duration_s\'])),300):').replace('stop=begin+300;','stop=min(begin+300,analysis[\'duration_s\']);')
 if name=='analyze_backtracking.py':s=s.replace('for begin in range(0,1200,300):','for begin in range(0,int(np.ceil(t[-1])),300):')
 (work/name).write_text(s.rstrip()+'\n');ast.parse(s)
commands={'postprocess.sh':f'{r1}/venv/bin/python /mnt/d/HT-Campus-To-Finish-20261118/postprocess_long.py > {r1}/setup/postprocess.log 2>&1','coverage.sh':f'{r1}/venv/bin/python /mnt/d/HT-Campus-To-Finish-20261118/assess_coverage.py > {r1}/setup/coverage.log 2>&1','audit.sh':f"{r1}/venv/bin/python '/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/tools/cmu_minimal/audit_commands.py' {r1}/runs/{c1} --radius 0.58182230175 > {r1}/setup/audit.log 2>&1"}
for n,cmd in commands.items():(work/n).write_text('set -e\nsource '+r1+'/env.sh\n'+cmd+'\n')
print('Dynamic-duration postrun checks prepared')
