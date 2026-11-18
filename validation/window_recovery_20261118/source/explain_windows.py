from pathlib import Path
import sys,json,numpy as np
r=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');sys.path.insert(0,str(r/'tools/cmu_minimal'));from analyze_context_window import explain
p=r/'validation/campus_repeat_1200s_20261118';m=json.loads((p/'data/MAP_SNAPSHOTS.json').read_text())['snapshots'][-1];a=np.load(p/'data/ht_map_last.npz');res=m['resolution_m'];cx,cy,_=m['center_xyz'];points=[(123,124),(112,119),(106,116),(100,114)]
results=[explain(a,m,cx+(m['rows']/2-rr-.5)*res,cy+(m['cols']/2-cc-.5)*res) for rr,cc in points]
h=np.load('/home/lzz/ht_campus_repeat_1200s_20261118/runs/explicit_labels_campus_repeat_1200s_01/ht_history.npz');xy=results[1]['uncertain_cells'][0]['xy'];ij=np.rint(np.array(xy)/res).astype(int);tile=ij//64;off=ij%64;k=np.flatnonzero((h['keys']==tile).all(axis=1))[0];z=h['elevation_modes'][k,:,off[0],off[1]];t=h['last_seen_modes'][k,:,off[0],off[1]]
results.append({'diagnostic_final_history_cell':{'xy':xy,'height_modes':[float(x) if np.isfinite(x) else None for x in z],'last_seen_modes':[float(x) if np.isfinite(x) else None for x in t],'age_at_last_recorded_map_s':[float(m['stamp_s']-x) if np.isfinite(x) else None for x in t],'rejected_time':None if not np.isfinite(h['rejected_observation_time'][k,off[0],off[1]]) else float(h['rejected_observation_time'][k,off[0],off[1]]),'scope':'Shutdown history may contain a few frames after the recorded map. This confirms retained old modes; it is not a reconstruction of original source variance or every historical frame.'}})
Path('/home/lzz/ht_window_recovery_20261118/analysis/CONTEXT_WINDOWS.json').write_text(json.dumps(results,indent=2,allow_nan=False));print(json.dumps(results[-1]))
assert all(q['reconstructed_context_valid']==q['recorded_context_valid'] for q in results[:-1])
try:explain(a,m,cx+(m['rows']/2-5-.5)*res,cy)
except ValueError:print('PASS incomplete outer context refuses reconstruction')
else:raise RuntimeError('Missing outer context was silently assumed')
