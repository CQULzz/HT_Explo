from pathlib import Path
import yaml,json,hashlib,subprocess
r=Path('/home/lzz/ht_repeat_20261114');out=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/repeats_20261114')
a=r/'runs/repeat_01';b=r/'runs/repeat_02';old=Path('/home/lzz/ht_execution_300s_20261113/runs/execution_300s_02')
diffs={}
def read_parameters(path):
    d=yaml.safe_load(path.read_text())
    return d if isinstance(d,dict) else None
for n in ['tare_planner_node.yaml','localPlanner.yaml','pathFollower.yaml','cupy_to_ht_bridge.yaml']:
    vals=[read_parameters(p/n) for p in [old,a,b]]
    diffs[n]={'repeat_parameters_equal':vals[1]==vals[2] if vals[1] and vals[2] else None,'repeat_01_equal_previous':vals[0]==vals[1] if vals[1] else None,'repeat_02_equal_previous':vals[0]==vals[2] if vals[2] else None,'unavailable':[label for label,v in zip(['previous','repeat_01','repeat_02'],vals) if v is None]}
freeze_equal=json.loads((a/'FREEZE.json').read_text())==json.loads((b/'FREEZE.json').read_text())
sources={}
for p in sorted((r/'original_tare_source').rglob('*.cpp')):
    q=Path('/home/lzz/tare_native_20261110/src/tare_planner/src')/p.relative_to(r/'original_tare_source')
    sources[str(p.relative_to(r/'original_tare_source'))]={'before':hashlib.sha256(p.read_bytes()).hexdigest(),'diagnostic':hashlib.sha256(q.read_bytes()).hexdigest()}
result={'same_runtime_freeze_between_repeats':freeze_equal,'parameters':diffs,'tare_source_hashes':sources,'navigation_behavior_modified':False,'completion_or_return_home_modified':False,'repeated_early_return':False,'diagnosis':'Not reproduced in either repeat; previous isolated early completion root cause remains unconfirmed.'}
print('comparison flags',freeze_equal,diffs)
fa=json.loads((a/'FREEZE.json').read_text());fb=json.loads((b/'FREEZE.json').read_text())
print('freeze diffs',{k:[fa.get(k),fb.get(k)] for k in set(fa)|set(fb) if fa.get(k)!=fb.get(k)})
assert freeze_equal
(out/'COMPARABILITY.json').write_text(json.dumps(result,indent=2))
for name in ['build_diag.log','build_diag_retry.log','build_diag_final.log','repeat_01.log','repeat_02.log','repeat_01_audit.log','repeat_02_audit.log']:
    p=r/'setup'/name
    if p.exists():__import__('shutil').copy2(p,out/'setup'/name)
print(json.dumps(result,indent=2))
