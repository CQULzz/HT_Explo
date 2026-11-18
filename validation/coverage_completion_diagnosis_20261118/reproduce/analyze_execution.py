from pathlib import Path
import json,csv,collections,numpy as np
root=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');ht=Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01');start=json.loads((ht/'observations/START.json').read_text())['clock'];finish=json.loads((ht/'ANALYSIS.json').read_text())['finish_signal_elapsed_s'];n=0;no=0;reasons=collections.Counter();cmd=collections.Counter()
for line in (ht/'observations/events.jsonl').open():
 e=json.loads(line)
 if not start<=e['time']<=start+finish:continue
 data=e.get('data')
 if not isinstance(data,dict):continue
 if e['kind']=='/ht_minimal/local_selection':
  n+=1;no+=not data.get('path_found',False)
  for k,v in data.get('rejections',{}).items():reasons[k]+=v if isinstance(v,(float,int)) else v.get('count',0)
 if e['kind']=='/ht_minimal/command_audit':cmd[data.get('reason','unknown')]+=1
result={'pre_finish_local_selection_samples':n,'pre_finish_no_path_samples':no,'sample_fraction_no_path':no/n,'sum_reported_candidate_rejections_not_unique_poses':dict(reasons),'sampled_command_gate_reasons_before_finish':dict(cmd),'interpretation':'Selected-path gate counts omit alternative paths already rejected by local selection. Candidate counts are repeated tests, not distinct terrain cells. No causal ablation performed.'}
(root/'HT_EXECUTION_EVIDENCE.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
