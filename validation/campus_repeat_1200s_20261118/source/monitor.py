from pathlib import Path
import json,csv,collections
r=Path('/home/lzz/ht_campus_repeat_1200s_20261118/runs/explicit_labels_campus_repeat_1200s_01')
p=r/'observations/metrics.csv'
if p.exists():
 rows=list(csv.DictReader(p.open()));print('LATEST',json.dumps(rows[-1]) if rows else 'header only')
else:print('Waiting for >=5 scans and >=5 HT maps')
if (r/'simulation.log').exists():
 lines=(r/'simulation.log').read_text(errors='replace').splitlines();ds=[l for l in lines if 'EXPLORATION_DIAG' in l];print('PLANNER',ds[-1:] if ds else 'not yet')
if (r/'RESULT.json').exists():print('RESULT',(r/'RESULT.json').read_text())
