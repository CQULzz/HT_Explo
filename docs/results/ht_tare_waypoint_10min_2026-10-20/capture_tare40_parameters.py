from pathlib import Path
import time,json,subprocess,yaml
p=Path(Path('/tmp/ht_tare40_run_path').read_text().strip())/'garage';deadline=time.monotonic()+150
while not (p/'current/measurement_started.json').exists():
 if time.monotonic()>deadline:raise TimeoutError('Measurement did not start')
 time.sleep(1)
records=[]
for node,name in [('/tare_planner_node','planner_parameters.yaml'),('/xytheta_follower','follower_parameters.yaml')]:
 for attempt in range(2):
  r=subprocess.run(['ros2','param','dump',node,'--no-daemon','--spin-time','6'],capture_output=True,text=True,timeout=30);data=yaml.safe_load(r.stdout)
  records.append(dict(node=node,attempt=attempt,returncode=r.returncode,stderr=r.stderr,stdout_bytes=len(r.stdout)))
  if data and node in data:(p/name).write_text(r.stdout);break
  (p/(name+'.attempt'+str(attempt))).write_text(r.stdout+'\n'+r.stderr)
 else:raise RuntimeError('Failed parameter capture '+node)
(p/'parameter_capture_attempts.json').write_text(json.dumps(records,indent=2)+'\n');print(records)
