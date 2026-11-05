from pathlib import Path
import argparse,json,subprocess,sys,time
R=Path('/home/w_lzz/ht-iterations-20261105');P=R/'repo';ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);ap.add_argument('--seed',type=int,required=True);ap.add_argument('--kind',choices=['baseline','candidate','repeat'],required=True);ap.add_argument('--candidate');a=ap.parse_args();ledger=R/'cycle2/BUDGET.json';s=json.loads(ledger.read_text());assert len(s['formal_runs'])<s['max_formal_runs'],'Formal-run budget exhausted';assert not (R/'cycle2'/a.label).exists()
candidate_ids={x.get('candidate') for x in s['formal_runs'] if x.get('candidate')}
if a.kind=='candidate':
 assert a.candidate,'Candidate id required'
 assert a.candidate in candidate_ids or len(candidate_ids)<s['max_candidates'],'Candidate budget exhausted'
cmd=[sys.executable,str(R/'runtime/run_sim.py'),'--label',a.label,'--output-root',str(R/'cycle2'),'--duration','120','--domain','228','--render-backend','egl','--ht-processing-mode','worker','--seed',str(a.seed)]
entry={'id':a.label,'seed':a.seed,'kind':a.kind,'candidate':a.candidate,'path':str(R/'cycle2'/a.label),'tested_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip(),'command':cmd,'state':'RUNNING'};s['formal_runs'].append(entry);s['candidates_used']=len(candidate_ids|({a.candidate} if a.candidate else set()));ledger.write_text(json.dumps(s,indent=2));start=time.monotonic();code=1
try:code=subprocess.run(cmd,check=False).returncode
finally:
 resultpath=R/'cycle2'/a.label/'RUN_RESULT.json';entry['runner_exit_code']=code;entry['wall_s']=time.monotonic()-start
 if resultpath.exists():
  q=json.loads(resultpath.read_text());entry['duration_s']=q['actual_duration_sim_s'];entry['state']='COMPLETE_COLLECTION' if q['full_requested_duration'] and not q['error'] and not q['managed_shutdown_nonzero'] and not q['frozen_files_changed'] else 'FAILED'
 else:entry['state']='FAILED_NO_RESULT'
 ledger.write_text(json.dumps(s,indent=2));print('BUDGET',len(s['formal_runs']),'/',s['max_formal_runs'],'candidates',s['candidates_used'],'/',s['max_candidates'],flush=True)
sys.exit(code)
