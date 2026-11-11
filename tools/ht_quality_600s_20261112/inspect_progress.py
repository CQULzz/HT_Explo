"""Distinguish motion from new observation growth using recorded diagnostics."""
from pathlib import Path
from collections import Counter,defaultdict
import json,csv
import numpy as np
ROOT=Path('/home/lzz/ht_quality_600s_20261112');RUN=ROOT/'runs/cmu_quality_600s_02'
rows=list(csv.DictReader((RUN/'observations/metrics.csv').open()))
t=np.array([float(r['elapsed_s']) for r in rows]);start=json.loads((RUN/'observations/START.json').read_text())['clock']
def v(key,time):return float(np.interp(time,t,[float(r[key]) for r in rows]))
stages={}
for lo,hi in [(0,300),(300,600)]:
    stages[f'{lo}_{hi}']={'distance_increment_m':v('distance_m',hi)-v('distance_m',lo),'observed_free_volume_increment_m3':v('sampled_free_volume_m3',hi)-v('sampled_free_volume_m3',lo)}
groups=defaultdict(Counter)
for line in (RUN/'observations/events.jsonl').open():
    e=json.loads(line)
    if e['kind']!='/ht_minimal/local_selection':continue
    d=e['data'];elapsed=d['time']-start
    if not 0<=elapsed<=600:continue
    k='0_300' if elapsed<=300 else '300_600'
    groups[k]['selections']+=1;groups[k]['path_found']+=d['path_found'];groups[k]['all_groups_rejected']+=d['ht_allowed_groups']==0
    groups[k]['some_group_rejected']+=d['ht_allowed_groups']<d['ht_checked_groups']
    groups[k].update({'rejected_'+reason:n for reason,n in d['rejections'].items()})
out={'stages':stages,'ht_local_selection':groups,'scope':'Post-hoc stage diagnosis. Movement and observed-volume growth are separate proxies. Path_found means a local template was available under HT checks; it does not prove progress to a global exploration objective. Group rejection counts include evaluated alternatives and can exceed event counts; they are not counts of stops. Global-goal cause requires a separate investigation.'}
(ROOT/'analysis/PROGRESS_DIAGNOSIS.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
