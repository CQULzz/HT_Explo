from pathlib import Path
import json,csv,collections
r=Path('/home/lzz/ht_recovery_campus_1200s_20261118/runs/recovery_campus_1200s_01');rows=list(csv.DictReader((r/'observations/metrics.csv').open()));start=json.loads((r/'observations/START.json').read_text())['clock'];end=float(rows[-1]['time']);audits=[];bad=[];way=[]
for line in (r/'observations/events.jsonl').open():
 e=json.loads(line)
 if not start<=e['time']<=end:continue
 if e['kind']=='/ht_minimal/command_audit':audits.append(e)
 if e['kind']=='malformed_diagnostic':bad.append(e)
 if e['kind']=='waypoint':way.append(e)
trailing=[]
for e in reversed(audits):
 if e['data'].get('reason')!='HT_CONTEXT_INVALID':break
 trailing.append(e)
last30=[e for e in audits if e['time']>=end-30]
result={'last30s_command_reasons':dict(collections.Counter(e['data'].get('reason') for e in last30)),'trailing_context_invalid_audits':len(trailing),'trailing_context_invalid_begin_s':trailing[-1]['time']-start if trailing else None,'trailing_context_invalid_end_s':trailing[0]['time']-start if trailing else None,'last_waypoint':way[-1] if way else None,'malformed_diagnostic_count':len(bad),'first_malformed_diagnostic':bad[:1],'source':'Original observer events and raw MCAP; no video frames used'}
(r/'STOP_DIAGNOSIS.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
