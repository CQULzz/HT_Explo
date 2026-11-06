from pathlib import Path
import argparse,json,subprocess,sys,time,fcntl,datetime
R=Path(__file__).parent;P=Path('/home/lzz/HT_linux_cycle7_20261106/repo')
ap=argparse.ArgumentParser();ap.add_argument('label');ap.add_argument('--navigation',choices=['ht','tare-geometric'],required=True);a=ap.parse_args()
lock=(R/'budget.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
f=R/'BUDGET.json';s=json.loads(f.read_text());assert s['used']<s['maximum_attempts'];assert not any(x['state']=='RUNNING' for x in s['runs']);assert not any(x['navigation']==a.navigation and x.get('full_requested_duration') and x.get('role')!='configuration_diagnostic' for x in s['runs'])
cmd=[sys.executable,str(P/'tools/pcd_sim/run_sim.py'),'--runtime','/home/lzz/HT_cmu_indoor_cycle9_20261106/runtime','--project',str(P),'--install-base','/home/lzz/HT_linux_offline_cycle8_20261106/install','--mapper-workspace','/home/lzz/my test/ht_cupy_gpu_ws_20261028','--output-root',str(R/'runs'),'--label',a.label,'--duration','120','--domain','225','--render-backend','egl','--navigation',a.navigation,'--cmu-workspace','/home/lzz/HT_linux_cycle7_20261106/cmu','--ht-processing-mode','worker','--mapper-executor','single','--context-interval','10','--seed','42']
e={'role':'formal_pair','label':a.label,'navigation':a.navigation,'state':'RUNNING','tested_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip(),'command':cmd,'started_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()};s['used']+=1;s['runs'].append(e)
def save():
 p=f.with_suffix('.tmp');p.write_text(json.dumps(s,indent=2));p.replace(f)
save();code=1;t=time.monotonic()
try:code=subprocess.run(cmd,check=False).returncode
finally:
 e.update(exit_code=code,wall_s=time.monotonic()-t)
 p=R/'runs'/a.label/'RUN_RESULT.json'
 if p.exists():
  d=json.loads(p.read_text());e.update(full_requested_duration=d['full_requested_duration'],actual_duration_s=d['actual_duration_sim_s'],error=d['error'],managed_shutdown_nonzero=d['managed_shutdown_nonzero']);e['state']='RECORDED' if code==0 else 'FAILED'
 else:e['state']='FAILED_NO_RESULT'
 save();print('BUDGET',s['used'],'/',s['maximum_attempts'],e['state'],flush=True)
sys.exit(code)
