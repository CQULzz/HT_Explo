from pathlib import Path
import csv,json,sys,numpy as np
R=Path('/home/w_lzz/ht-iterations-20261105');run=R/sys.argv[1];rows=[x for x in csv.DictReader((run/'metrics.csv').open()) if float(x['elapsed_sim'])>=0];done=[x for x in rows if x['mission_completed']=='1'];first=float(done[0]['elapsed_sim']) if done else None;active=[x for x in rows if x['mission_completed']=='0'];t0=float(rows[0]['sim_time'])-float(rows[0]['elapsed_sim']);age=[];service=[]
for line in (run/'events.jsonl').open():
 o=json.loads(line)
 if o['topic']=='ht_performance' and (first is None or o['time']-t0<first):
  q=json.loads(o['data']);age.append(q['source_age_at_publish_s']);service.append(q['callback_service_s'])
q=lambda a:dict(zip(['p50','p95','max'],map(float,np.percentile(a,[50,95,100])))) if a else None
out={'first_internal_completed_elapsed_s':first,'before_completed_samples':len(active),'before_completed_zero_command_fraction':sum(abs(float(x['v_cmd']))<1e-6 and abs(float(x['w_cmd']))<1e-6 for x in active)/len(active) if active else None,'after_completed_samples':len(done),'before_completed_ht_source_age_at_publish_s':q(age),'before_completed_ht_callback_service_s':q(service),'completion_note':'Internal mission state only; no independent full-scene coverage acceptance. Command fractions are telemetry sample fractions, not exact duration.'};dest=R/'reports'/run.name/'PHASE_METRICS.json';dest.write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
