"""Close evidence after the repeat; never edits navigation code or raw recordings."""
from pathlib import Path
import csv,hashlib,importlib.util,json,shutil,time
ROOT=Path('/home/lzz/ht_quality_600s_20261112');PROJECT=Path('/home/lzz/HT_Explo_quality_20261111')
RUN=ROOT/'runs/cmu_quality_600s_02'
def read(p):return json.loads(p.read_text())
result=read(RUN/'RESULT.json')
if not result.get('collection_complete'):raise RuntimeError('No completed collection; cannot finalize as completed')
spec=importlib.util.spec_from_file_location('candidate',PROJECT/'tools/ht_height_quality/run.py');runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)
baseline=read(Path('/home/lzz/ht_quality_20261111/runs/cmu_quality_300s_01/FREEZE.json'))
previous_unchanged=runner.freeze()==baseline
runner.ROOT=ROOT
now=runner.freeze();wrapper=PROJECT/'tools/ht_quality_600s_20261112/run.py';now[str(wrapper)]=hashlib.sha256(wrapper.read_bytes()).hexdigest()
freeze=read(RUN/'FREEZE.json');verified={'files':len(freeze),'matches':freeze==now,'changed':[p for p in set(freeze)|set(now) if freeze.get(p)!=now.get(p)],'previous_navigation_232_files_still_unchanged':previous_unchanged}
(ROOT/'evidence/FREEZE_VERIFIED.json').write_text(json.dumps(verified,indent=2))
receipt={}
for run in sorted((ROOT/'runs').iterdir()):
    for p in sorted((run/'bag').glob('*')):
        if not p.is_file():continue
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
        receipt[str(p)]={'bytes':p.stat().st_size,'sha256':h.hexdigest()}
(ROOT/'evidence/RAW_SHA256.json').write_text(json.dumps(receipt,indent=2))
rows=list(csv.DictReader((RUN/'observations/metrics.csv').open()))
jumps=[]
for a,b in zip(rows,rows[1:]):
    delta=float(b['time'])-float(a['time'])-(float(b['elapsed_s'])-float(a['elapsed_s']))
    if abs(delta)>1:jumps.append({'before_elapsed_s':float(a['elapsed_s']),'elapsed_s':float(b['elapsed_s']),'wall_minus_monotonic_delta_s':delta})
(ROOT/'evidence/CLOCK_CHECK_02.json').write_text(json.dumps({'clock_jumps_gt_1s':jumps,'metric_rows':len(rows),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()},indent=2))
ledger=read(ROOT/'BUDGET.json');ledger['attempts'][1].update(status='complete' if result['freeze_unchanged'] else 'invalid_freeze',elapsed_s=result['summary']['elapsed_s']);ledger.update(status='closed',completed_runs=1,closed_wall_time=time.time(),reason='User-requested one complete 600s repeat obtained on the second infrastructure attempt. Interrupted first trial retained. Stop; no further candidate or formal launch.');(ROOT/'BUDGET.json').write_text(json.dumps(ledger,indent=2))
print(json.dumps({'freeze':verified,'raw_files':len(receipt),'raw_bytes':sum(v['bytes'] for v in receipt.values()),'clock_jumps':jumps,'ledger':ledger},indent=2))
