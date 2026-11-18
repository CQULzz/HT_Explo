from pathlib import Path
import json,numpy as np
base=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/campus_1200s_20261118');meta=json.loads((base/'data/MAP_SNAPSHOTS.json').read_text())['snapshots'][-1];a=np.load(base/'data/ht_map_last.npz');pos=json.loads((base/'ANALYSIS.json').read_text())['final_base_xy'];goal=np.array([32.01223566328884,-5.41432597880062]);p=np.array(pos);delta=(goal-p)/np.linalg.norm(goal-p);res=meta['resolution_m'];cx,cy,_=meta['center_xyz'];rows=meta['rows'];cols=meta['cols'];result=[]
for distance in [0,.1,.25,.5,.75,1.]:
 q=p+delta*distance;r=int(np.floor(rows*.5-(q[0]-cx)/res));c=int(np.floor(cols*.5-(q[1]-cy)/res));record={'distance_toward_goal_m':distance,'xy':q.tolist(),'cell_rc':[r,c]}
 for k in ['ht_valid','ht_observation_valid','ht_measured_valid','ht_obstacle']:record[k]=float(a[k][r,c])
 record['finite_direction_scores']=int(sum(np.isfinite(a['ht_dir_'+str(i)][r,c]) for i in range(8)));result.append(record)
out={'source':'Previous complete20min last raw HT map, not current repeat','stamp_s':meta['stamp_s'],'query_samples':result,'context_rule_from_source':'51x51 receptive field (~2.09m at0.04094m/cell), >=90% near-known support and no unresolved uncertainty in that field; occupied handled separately','not_root_cause_proven':'Exported last map identifies invalid context locations, not which original height/variance sample first invalidated the field'}
Path('/mnt/d/HT-Campus-Repeat-1200s-20261118/PREVIOUS_STOP_MAP_CHECK.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
