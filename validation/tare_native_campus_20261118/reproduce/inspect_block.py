from pathlib import Path
import json,csv
r=Path('/home/lzz/tare_native_campus_20261118/runs/native_campus_01');p=r/'observations/events.jsonl';latest={}
with p.open('rb') as f:f.seek(max(0,p.stat().st_size-600000));lines=f.read().splitlines()
for line in lines:
 try:e=json.loads(line)
 except ValueError:continue
 if e['kind'] in ['waypoint','local_path','finish_transition']:latest[e['kind']]=e
print('LATEST_EVENTS',json.dumps(latest));rows=list(csv.DictReader((r/'observations/metrics.csv').open()));last=rows[-1];begin=float(last['elapsed_s'])-180;window=[x for x in rows if float(x['elapsed_s'])>=begin];print('current',json.dumps(last));print('window180_distance',float(window[-1]['distance_m'])-float(window[0]['distance_m']),'volume',float(window[-1]['sampled_free_volume_m3'])-float(window[0]['sampled_free_volume_m3']))
