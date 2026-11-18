from pathlib import Path
import csv,hashlib,json,shutil,ast,yaml
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
base=Path('/home/lzz/tare_native_campus_20261118');repeat=Path('/home/lzz/tare_native_campus_repeat_20261118')
out=Path('/mnt/d/TARE-Native-Campus-20261118/results');out.mkdir(exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
roots=[base,repeat];cases=['native_campus_01','native_campus_02'];summaries=[]
for root,case in zip(roots,cases):
 run=root/'runs'/case;target=out/case;target.mkdir(exist_ok=True)
 for p in run.iterdir():
  if p.is_file() and p.suffix in ['.json','.yaml','.txt','.png','.csv','.log']:
   shutil.copy2(p,target/p.name)
 for sub in ['observations','terminal_inputs']:
  for p in (run/sub).glob('*'):
   if p.is_file() and p.stat().st_size<20_000_000:
    (target/sub).mkdir(exist_ok=True);shutil.copy2(p,target/sub/p.name)
 (target/'bag').mkdir(exist_ok=True);shutil.copy2(run/'bag/metadata.yaml',target/'bag/metadata.yaml')
 for p in (root/'analysis').glob('*'):
  if p.suffix in ['.json','.png']:
   (target/'coverage').mkdir(exist_ok=True);shutil.copy2(p,target/'coverage'/p.name)
 summary=json.loads((run/'ANALYSIS.json').read_text());summary['coverage']=json.loads((root/'analysis/COVERAGE_ASSESSMENT.json').read_text());summaries.append(summary)
 shutil.copy2(root/'PLAN.json',target/'PLAN.json')
setup=out/'setup';setup.mkdir(exist_ok=True)
for p in (base/'setup').iterdir():
 if p.is_file():shutil.copy2(p,setup/p.name)
for p in [base/'BUDGET.json',base/'PLAN.json']:
 shutil.copy2(p,out/p.name)
helpers=out/'reproduce';helpers.mkdir(exist_ok=True)
for p in Path('/mnt/d/TARE-Native-Campus-20261118').iterdir():
 if p.suffix in ['.py','.sh','.json','.diff'] and p.is_file():
  shutil.copy2(p,helpers/p.name)
for tag,root in [('first',base),('repeat',repeat)]:
 dest=helpers/tag;dest.mkdir(exist_ok=True)
 for name in ['env.sh','simulation.launch.py','run.py','observer.py','mission_stop.py','campus.world','recording_qos.yaml','mcap.yaml','run_native.sh']:
  if (root/name).is_file():shutil.copy2(root/name,dest/name)
# Compare full effective YAML and actual binary identity, not merely selected headline parameters.
a=base/'runs'/cases[0];b=repeat/'runs'/cases[1]
params={p.name:sha(p)==sha(b/p.name) for p in a.glob('*.yaml')}
normalized={}
for p in a.glob('*.yaml'):
 aa=p.read_text();bb=(b/p.name).read_text()
 if 'Node not found' in aa or 'Node not found' in bb:
  normalized[p.name]=None;continue
 normalized[p.name]=yaml.safe_load(aa)==yaml.safe_load(bb.replace(str(repeat),str(base)))
assert all(v is not False for v in normalized.values()),normalized
exes=lambda path:{Path(e['executable']).name:e['sha256'] for e in json.loads((path/'ACTUAL_NAVIGATION.json').read_text())}
assert exes(a)==exes(b)
for name,digest in exes(a).items():
 records=json.loads((a/'ACTUAL_NAVIGATION.json').read_text());p=Path(next(e['executable'] for e in records if Path(e['executable']).name==name));assert sha(p)==digest
for run in [a,b]:
 assert not any(s in (run/'NODES.txt').read_text().lower() for s in ['ht_mapper','ht_scout','cupy','ht_inference'])
 for name,digest in json.loads((run/'FREEZE.json').read_text()).items():assert sha(Path(name))==digest,name
proof={'full_effective_yaml_byte_equal':params,'effective_yaml_equal_after_resolving_isolated_root':normalized,'missing_effective_parameter_dump':['native_campus_02/vehicleSimulator.yaml'],'evidence_gap':'Second vehicleSimulator parameter service lookup returned Node not found. Node-list snapshot also missed TARE and vehicleSimulator; four actual executables independently verified. Frozen launch/source/config and same binary retained; no replacement dump fabricated.','actual_binary_sha_equal':exes(a),'both_no_ht_nodes':True,'freeze_current_bytes_match_both':True,'native_vlp16_speed_mps':2.0,'comparison':'No common explicit seed; dynamics/ROS scheduling can choose different routes.'}
(out/'CONFIGURATION_VERIFICATION.json').write_text(json.dumps(proof,indent=2))
(out/'BATCH_SUMMARY.json').write_text(json.dumps(summaries,indent=2))
fig,axes=plt.subplots(1,3,figsize=(15,4.5))
for case,color in zip(cases,['#0f766e','#d97706']):
 rows=list(csv.DictReader((out/case/'observations/metrics.csv').open()));val=lambda k:np.array([float(r[k]) for r in rows]);t=val('elapsed_s')
 axes[0].plot(val('x'),val('y'),label=case,color=color);axes[0].plot(val('x')[-1],val('y')[-1],'x',color=color)
 axes[1].plot(t,val('distance_m'),label=case,color=color);axes[2].plot(t,val('sampled_free_volume_m3'),label=case,color=color)
axes[0].set(xlabel='World X (m)',ylabel='World Y (m)',aspect='equal',title='Native TARE, same configuration')
axes[1].set(xlabel='Wall time (s)',ylabel='Recorded distance (m)',title='Distance is not completeness')
axes[2].set(xlabel='Wall time (s)',ylabel='Observation proxy (m3)',title='Not ground-truth coverage')
for ax in axes:ax.grid(alpha=.2);ax.legend()
fig.tight_layout();fig.savefig(out/'native_repeat_comparison.png',dpi=150);plt.close(fig)
print(json.dumps({'cases':summaries,'configuration':proof},indent=2))
