from pathlib import Path
import csv, json, math
import numpy as np
run=Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01')
summary=json.loads((run/'observations/SUMMARY.json').read_text())
rows=list(csv.DictReader((run/'observations/metrics.csv').open()))
t=np.array([float(r['elapsed_s']) for r in rows]);x=np.array([float(r['x'])-.1725*math.cos(float(r['yaw'])) for r in rows]);y=np.array([float(r['y'])-.1725*math.sin(float(r['yaw'])) for r in rows])
tail=np.flatnonzero(t>=t[-1]-20)
dist=np.hypot(x[tail],y[tail]);motion=np.hypot(x[tail]-x[tail[0]],y[tail]-y[tail[0]])
zero=all(abs(float(rows[i]['cmd_linear']))<.01 and abs(float(rows[i]['cmd_angular']))<.01 for i in tail)
finish=all(rows[i]['finish']=='True' for i in tail)
fresh=all(0<=float(rows[i]['ht_age_s'])<=1 and 0<=float(rows[i]['odom_age_s'])<=.2 and 0<=float(rows[i]['scan_age_s'])<=2 for i in tail)
out={'outcome':summary['mission_outcome'],'terminal_rule_hold_s':summary['terminal_status']['home_hold_elapsed_s'],'csv_sample_span_in_last20s':float(t[tail[-1]]-t[tail[0]]),'samples':len(tail),'maximum_distance_to_initial_m':float(dist.max()),'maximum_translation_from_first_tail_sample_m':float(motion.max()),'all_zero_command':zero,'all_finish_true':finish,'all_recorded_ht_odom_scan_ages_fresh':fresh,'observer_also_required_command_arrival_age_s':.25,'scope':'Independent CSV check of final20s samples plus the observer continuous hold; initial base is fixed world origin for this scene.'}
out['passed']=bool(summary['mission_complete'] and out['terminal_rule_hold_s']>=20 and dist.max()<=.5 and motion.max()<=.05 and zero and finish and fresh)
assert out['passed'],out
(run/'RETURN_VERIFICATION.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
