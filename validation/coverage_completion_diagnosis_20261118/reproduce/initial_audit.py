from pathlib import Path
import yaml,json,difflib
out=Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118');root=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');root.mkdir(exist_ok=True)
native=Path('/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02');ht=Path('/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01')
result={}
for name in ['tare_planner_node.yaml','localPlanner.yaml','pathFollower.yaml','vehicleSimulator.yaml']:
 a=yaml.safe_load((ht/name).read_text());b=yaml.safe_load((native/name).read_text())
 if not isinstance(b,dict):result[name]={'native_dump_error':b};continue
 a=next(iter(a.values()))['ros__parameters'];b=next(iter(b.values()))['ros__parameters'];result[name]={k:{'ht':a.get(k),'native':b.get(k)} for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
(out/'PARAMETER_DIFF.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
freeze=json.loads((ht/'FREEZE.json').read_text());print('HT TARE freeze',[p for p in freeze if any(t in p for t in ['tare','launch','urdf'])][:45])
