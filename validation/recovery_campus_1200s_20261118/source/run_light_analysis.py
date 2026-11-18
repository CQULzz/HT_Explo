from pathlib import Path
import subprocess
w=Path('/mnt/d/HT-Recovery-Campus-1200s-20261118');py='/home/lzz/ht_recovery_campus_1200s_20261118/venv/bin/python'
for n in ['summarize_stop.py','summarize_planning_chain.py','end_motion.py','analyze_recovery.py','analyze_backtracking.py']:
 r=subprocess.run([py,str(w/n)],capture_output=True,text=True);(w/(n+'.log')).write_text(r.stdout+r.stderr);assert r.returncode==0,(n,r.stderr);print(n,'OK')
