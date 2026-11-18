from pathlib import Path
import subprocess
work=Path('/mnt/d/HT-Campus-To-Finish-20261118');py='/home/lzz/ht_campus_to_finish_20261118/venv/bin/python'
for name in ['summarize_stop.py','summarize_planning_chain.py','end_motion.py','analyze_recovery.py','analyze_backtracking.py']:
 r=subprocess.run([py,str(work/name)],capture_output=True,text=True);(work/(name+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,(name,r.stderr);print(name,'OK')
