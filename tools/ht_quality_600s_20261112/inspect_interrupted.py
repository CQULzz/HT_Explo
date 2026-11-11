"""Summarize the preserved interrupted attempt without changing its raw files."""
from pathlib import Path
from collections import Counter
import csv,io,json
import numpy as np

ROOT=Path('/home/lzz/ht_quality_600s_20261112')
RUN=ROOT/'runs/cmu_quality_600s_01'
raw=(RUN/'observations/metrics.csv').read_bytes()
rows=[]
for r in csv.DictReader(io.StringIO(raw.replace(b'\0',b'').decode(errors='replace'))):
    try:float(r['elapsed_s']);float(r['time']);float(r['distance_m']);rows.append(r)
    except (ValueError,TypeError,KeyError):pass
d={k:np.array([float(r[k]) if r[k] else np.nan for r in rows]) for k in ['elapsed_s','time','distance_m','ht_age_s']}
delta=np.diff(d['time'])-np.diff(d['elapsed_s']);indices=np.where(np.abs(delta)>1)[0]
jumps=[{'before_elapsed_s':float(d['elapsed_s'][i]),'after_elapsed_s':float(d['elapsed_s'][i+1]),'wall_vs_monotonic_jump_s':float(delta[i])} for i in indices]
before=np.arange(len(rows))<=indices[0] if len(indices) else np.ones(len(rows),bool)
last={};reasons=Counter();last_accepted=None;invalid_lines=0
for line in (RUN/'observations/events.jsonl').read_bytes().replace(b'\0',b'').decode(errors='replace').splitlines():
    try:e=json.loads(line)
    except (ValueError,TypeError):invalid_lines+=1;continue
    last[e['kind']]=e['data']
    if e['kind']=='/ht_minimal/command_audit':
        a=e['data']
        if not a['allowed']:reasons[a['reason']]+=1
        elif abs(a['linear_candidate'])+abs(a['angular_candidate'])>1e-8:last_accepted=a
out={'interruption':json.loads((RUN/'INTERRUPTED.json').read_text()),'clock_jumps':jumps,
     'before_clock_jump':{'last_elapsed_s':float(d['elapsed_s'][before][-1]),'distance_m':float(d['distance_m'][before][-1]),'sampled_ht_age_p50_s':float(np.nanpercentile(d['ht_age_s'][before],50)),'sampled_ht_age_p95_s':float(np.nanpercentile(d['ht_age_s'][before],95)),'samples_gt_1s':int(np.count_nonzero(d['ht_age_s'][before]>1)),'samples':int(before.sum())},
     'recorded_command_rejections':reasons,'last_accepted_nonzero_audit':last_accepted,
     'last_events':{k:v for k,v in last.items() if k.startswith('/ht_minimal')},'invalid_event_lines':invalid_lines,
     'scope':'Interrupted trial only. Raw NULs removed in memory for diagnostic parsing. No bag recovery, completed-duration claim or performance acceptance. System suspend/clock jump, GPU kernel errors and host reboot evidence remain separate original logs.'}
(ROOT/'analysis/INTERRUPTED_ANALYSIS.json').write_text(json.dumps(out,indent=2));print(json.dumps({k:v for k,v in out.items() if k not in ['last_events','interruption']},indent=2))
