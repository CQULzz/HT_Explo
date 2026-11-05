from pathlib import Path
import json,subprocess,sys,time,argparse,hashlib
R=Path('/home/w_lzz/ht-iterations-20261105');P=R/'repo';C=R/'cycle6';ap=argparse.ArgumentParser();ap.add_argument('label');a=ap.parse_args();ledger=C/'BUDGET.json';s=json.loads(ledger.read_text());assert len(s['runs'])<s['max_runs'];assert all(x['state']!='RUNNING' for x in s['runs']);case=s['planned_order'][len(s['runs'])];assert case['label']==a.label;assert not (C/a.label).exists()
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip()
cmd=[sys.executable,str(R/'runtime/run_sim.py'),'--label',a.label,'--output-root',str(C),'--duration','120','--domain','228','--render-backend','egl','--ht-processing-mode','worker','--mapper-executor',case['mode'],'--seed',str(case['seed'])]
entry={**case,'tested_commit':head,'command':cmd,'state':'RUNNING'};s['runs'].append(entry);ledger.write_text(json.dumps(s,indent=2));start=time.monotonic();code=1
try:code=subprocess.run(cmd,check=False).returncode
finally:
 entry['runner_exit_code']=code;entry['wall_s']=time.monotonic()-start;p=C/a.label/'RUN_RESULT.json'
 if p.exists():
  result=json.loads(p.read_text());entry['duration_s']=result['actual_duration_sim_s'];entry['state']='COMPLETE_COLLECTION' if result['full_requested_duration'] and not result['error'] and not result['managed_shutdown_nonzero'] and not result['frozen_files_changed'] else 'FAILED'
 else:entry['state']='FAILED_NO_RESULT'
 ledger.write_text(json.dumps(s,indent=2));print('BUDGET',len(s['runs']),'/',s['max_runs'],flush=True)
sys.exit(code)
