from pathlib import Path
p=Path('/mnt/d/HT-Campus-To-Finish-20261118/monitor.py');s=p.read_text();s=s.replace("print('LATEST',json.dumps(rows[-1]) if rows else 'waiting for readiness')", "print('LATEST',json.dumps({k:rows[-1][k] for k in ['elapsed_s','distance_m','x','y','cmd_linear','cmd_angular','finish','ht_age_s']}) if rows else 'waiting for readiness')")
s=s.replace("if p.exists():print('TASK_STATUS',p.read_text())", "if p.exists():\n try:\n  status=json.loads(p.read_text());print('TASK_STATUS',json.dumps({k:status[k] for k in ['outcome','distance_to_initial_m','first_finish_elapsed_s','home_hold_elapsed_s','inputs_fresh']}))\n except json.JSONDecodeError:print('TASK_STATUS updating')")
p.write_text(s)
