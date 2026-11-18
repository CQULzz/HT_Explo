from pathlib import Path
import json,re,csv,numpy as np
out=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');run=Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01');start=json.loads((run/'observations/START.json').read_text())['clock'];rows=[];lines=(run/'simulation.log').read_text(errors='replace').splitlines();context=[]
for i,line in enumerate(lines):
 if 'EXPLORATION_DIAG' in line or 'GLOBAL_DIAG' in line or 'LOCAL_DIAG' in line:
  stamp=re.search(r'\[([0-9]+\.[0-9]+)\]',line)
  if stamp:
   data={k:float(v) for k,v in re.findall(r'(\w+)=(-?[0-9]+(?:\.[0-9]+)?)',line)};rows.append({'elapsed_s':float(stamp[1])-start,'kind':'EXPLORATION_DIAG' if 'EXPLORATION_DIAG' in line else ('GLOBAL_DIAG' if 'GLOBAL_DIAG' in line else 'LOCAL_DIAG'),**data})
 if 'Exploration completed' in line:context=lines[max(0,i-4):i+2]
(out/'HT_FINISH_LOG_CONTEXT.txt').write_text('\n'.join(context)+'\n');(out/'HT_TARE_DIAGNOSTIC_SERIES.json').write_text(json.dumps(rows,indent=2))
finish=json.loads((run/'ANALYSIS.json').read_text())['finish_signal_elapsed_s'];choices=[x for x in rows if x['kind']=='EXPLORATION_DIAG' and x.get('local_complete')==1 and x.get('global_return')==1 and x['elapsed_s']<=finish+.1];first=choices[0];global_record=[x for x in rows if x['kind']=='GLOBAL_DIAG' and x['elapsed_s']<=first['elapsed_s']][-1];local_record=[x for x in rows if x['kind']=='LOCAL_DIAG' and x['elapsed_s']<=first['elapsed_s']][-1]
reason={'actual_trigger_record':first,'same_cycle_global':global_record,'same_cycle_local':local_record,'interpretation':'routable is after local-vs-global eligibility and keypose graph filtering, not a physical reachability oracle. Exploring>0 is compatible with no eligible remote tour tasks. Local complete means no selected gain task, not uncovered==0.','source_rules':{'global_cell_size_m':9.6,'viewpoint_horizon_xy_m':[48,48],'local_min_surface_gain':40,'local_min_frontier_gain':20,'cell_reopen_viewpoint_count':10,'cell_close_qualifying_viewpoint_count_below':1,'unseen_cells_are_global_targets':False,'finish_checks_all_reference_geometry':False},'native_original_per_cell_status_or_viewpoint_stream_recorded':False,'exact_original_R1_cell_state_not_recoverable_from_recorded_topics_alone':True};(out/'COMPLETION_CHAIN.json').write_text(json.dumps(reason,indent=2));print(json.dumps(reason,indent=2))
