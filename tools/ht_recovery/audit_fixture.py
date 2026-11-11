from pathlib import Path
import json,csv,sys,math
import numpy as np
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
sys.path.insert(0,'/home/lzz/HT_Explo_recovery_20261111/tools/cmu_minimal')
from audit_commands import decode,check
ROOT=Path('/home/lzz/ht_recovery_20261111');source=Path('/home/lzz/ht_only_20261111/analysis/live_indoor_stop/global_local.cdr');m=decode(deserialize_message(source.read_bytes(),GridMap));rows=list(csv.DictReader((ROOT/'analysis/fixture_trace.csv').open()));bad=[];moving=0;minimum=1
for row in rows:
 d={'x':float(row['x']),'y':float(row['y']),'yaw':float(row['yaw']),'linear_candidate':float(row['linear']),'angular_candidate':float(row['angular']),'map_stamp':float(row['map_stamp']),'time':float(row['query_time']),'reaction_time':.1,'linear_brake_accel':2.5,'angular_brake_accel':3.}
 ok,reason,p=check(m,d)
 if not ok:bad.append({'row':row,'reason':reason})
 if abs(d['linear_candidate'])+abs(d['angular_candidate'])>1e-8:moving+=1
 if p is not None:minimum=min(minimum,p)
first,last=rows[0],rows[-1];start=np.array([float(first['x']),float(first['y'])]);end=np.array([float(last['x']),float(last['y'])]);goal=np.array([11.849130669080782,1.0412912503302776]);t=np.array([float(r['time']) for r in rows]);v=np.array([float(r['linear']) for r in rows]);w=np.array([float(r['angular']) for r in rows]);
result={'rows':len(rows),'moving_commands':moving,'violations':bad,'minimum_swept_score':minimum,'movement_m':float(np.linalg.norm(end-start)),'goal_distance_reduction_m':float(np.linalg.norm(start-goal)-np.linalg.norm(end-goal)),'max_linear_accel':float(np.max(np.abs(np.diff(v)/np.diff(t)))),'max_angular_accel':float(np.max(np.abs(np.diff(w)/np.diff(t)))),'simulated_duration_s':float(t[-1]),'passed':not bad and moving>0 and np.linalg.norm(start-goal)-np.linalg.norm(end-goal)>.5,'scope':'Independent Python sweep verification of the C++ controller closed-loop trace against unchanged original frozen HT map. Vehicle integrates yaw-first at CMU 200Hz. Query clock stays at the original snapshot time; this verifies static-map execution, not new observations, long-duration TTL, contacts or hardware.'}
(ROOT/'analysis/FIXTURE_AUDIT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));assert result['passed']
