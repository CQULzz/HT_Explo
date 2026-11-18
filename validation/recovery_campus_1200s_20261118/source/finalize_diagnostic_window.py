from pathlib import Path
import json,re,csv
r=Path('/home/lzz/ht_recovery_campus_1200s_20261118/runs/recovery_campus_1200s_01');a=json.loads((r/'ANALYSIS.json').read_text());s=json.loads((r/'observations/START.json').read_text())['clock'];rows=list(csv.DictReader((r/'observations/metrics.csv').open()));end=float(rows[-1]['time']);d=[]
for l in (r/'simulation.log').read_text().splitlines():
 if 'EXPLORATION_DIAG' not in l:continue
 m=re.search(r'\[([0-9]{10}\.[0-9]+)\]',l)
 if m and s<=float(m[1])<=end:d.append(l)
a['last_planner_diagnostic']=d[-1] if d else None;a['planner_diagnostic_scope']='Only log timestamps within formal collection window, excluding teardown';(r/'ANALYSIS.json').write_text(json.dumps(a,indent=2))
