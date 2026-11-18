from pathlib import Path
import ast
work=Path('/mnt/d/TARE-Native-Campus-20261118');old=Path('/mnt/d/HT-Campus-To-Finish-20261118');r0='/home/lzz/ht_campus_to_finish_20261118';r1='/home/lzz/tare_native_campus_20261118';c0='campus_to_finish_01';c1='native_campus_01'
# Same independent reference geometry; native scanner coincides with base XY.
for name in ['assess_coverage.py','end_motion.py']:
 s=(old/name).read_text().replace(r0,r1).replace(c0,c1).replace('.1725','0.0');(work/name).write_text(s);ast.parse(s)
s=(old/'analyze_backtracking.py').read_text();s=s.replace("baseline=Path('/home/lzz/ht_recovery_campus_1200s_20261118/runs/recovery_campus_1200s_01')","baseline=Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01')");s=s.replace(r0+'\');run=root/\'runs/'+c0,r1+'\');run=root/\'runs/'+c1)
s=s.replace('def analyze(path):','def analyze(path,offset):').replace('-.1725*np.cos','-offset*np.cos').replace('-.1725*np.sin','-offset*np.sin').replace('value,*arrays=analyze(path)','value,*arrays=analyze(path,0. if label==\'repeat\' else .1725)')
(work/'analyze_backtracking.py').write_text(s);ast.parse(s)
(root:=Path(r1)).joinpath('analysis').mkdir(exist_ok=True)
(work/'coverage.sh').write_text('set -e\nsource '+r1+'/env.sh\n/usr/bin/python3 /mnt/d/TARE-Native-Campus-20261118/assess_coverage.py > '+r1+'/setup/coverage.log 2>&1\n')
print('Native non-HT analysis helpers prepared')
