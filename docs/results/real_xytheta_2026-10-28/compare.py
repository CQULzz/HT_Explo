"""Build an exact old gate against the same offline runner, then compare C++ searches."""
from pathlib import Path
from collections import Counter
import argparse,subprocess,json,hashlib,shlex,os,platform,time
ROOT=Path(__file__).resolve().parents[3]
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def run(args,cwd,log):
 with log.open('w') as f:subprocess.run(args,cwd=cwd,check=True,stdout=f,stderr=subprocess.STDOUT)
def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);a=p.parse_args();d=a.data.resolve();b=ROOT/'build_real/tare_planner'
 old=d/'baseline_binary';old.mkdir(exist_ok=False)
 db=read(b/'compile_commands.json');e=next(x for x in db if x['file'].endswith('/src/ht_cost/ht_cost_map.cpp'))
 args=e.get('arguments') or shlex.split(e['command']);args[args.index('-o')+1]=str(old/'ht_cost_map.cpp.o');args[args.index('-c')+1]=str(d/'ht_cost_map_before.cpp')
 run(args,Path(e['directory']),d/'baseline_compile.log')
 run(['/usr/bin/ar','rcs',str(old/'libht_cost_before.a'),str(old/'ht_cost_map.cpp.o')],b,d/'baseline_archive.log')
 link=shlex.split((b/'CMakeFiles/ht_xytheta_offline.dir/link.txt').read_text());link[link.index('-o')+1]=str(old/'ht_xytheta_before')
 count=0
 for i,x in enumerate(link):
  if x=='libht_cost.a':link[i]=str(old/'libht_cost_before.a');count+=1
 assert count==1,link
 run(link,b,d/'baseline_link.log')
 actual=ROOT/'src/tare_planner/src/ht_cost/ht_cost_map.cpp';before=old/'ht_xytheta_before';after=b/'ht_xytheta_offline'
 manifest={'baseline':read(d/'BASELINE.json'),'candidate_local_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
   'architecture':platform.machine(),'candidate_gate_sha256':sha(actual),'baseline_gate_sha256':sha(d/'ht_cost_map_before.cpp'),
   'runner_source_sha256':sha(ROOT/'src/tare_planner/tools/ht_xytheta_offline.cpp'),'before_binary_sha256':sha(before),'after_binary_sha256':sha(after),
   'baseline_compile_argv':args,'baseline_link_argv':link,'batch_sha256':sha(d/'input/queries.tsv'),
   'scope':'Same actual C++ planner and query inputs; only HT gate object differs. No hardware, controller, TARE goal selection or simulation.'}
 write(d/'BINARY_MANIFEST.json',manifest)
 for role,binary in [('before',before),('after',after)]:
  run([str(binary),'--batch',str(d/'input/queries.tsv'),'--output',str(d/(role+'.json'))],ROOT,d/(role+'.log'))
 u=read(d/'before.json');v=read(d/'after.json');assert u['parameters']==v['parameters'];assert len(u['queries'])==len(v['queries'])
 hashes={};pairs=[]
 for x,y in zip(u['queries'],v['queries']):
  assert not x.get('error') and not y.get('error'),(x,y)
  for k in ['label','map_file','map_sha256','map_stamp_ns','start','goal']:assert x[k]==y[k],(k,x['label'])
  path=Path(x['map_file']);hashes.setdefault(str(path),sha(path));assert x['map_sha256']==hashes[str(path)]
  assert x['map_stamp_ns']==x['clock_ns']==y['clock_ns']
  for row in [x,y]:
   if row['reached']:assert row['all_segments_permitted'] and row['independent_recheck_passed']
  pairs.append({'label':x['label'],'synthetic':x['label'].startswith('synthetic_'),'before_reached':x['reached'],'after_reached':y['reached'],
    'before_termination':x['termination'],'after_termination':y['termination'],'before_ms':x['search_wall_ms'],'after_ms':y['search_wall_ms'],
    'before_start_support':x['start_support'],'after_start_support':y['start_support']})
 synth={x['label']:x for x in v['queries'] if x['label'].startswith('synthetic_')}
 assert synth['synthetic_reverse_theta0']['reached']
 assert synth['synthetic_low_probability']['termination']=='INVALID_START'
 groups={}
 for name,is_synthetic in [('recorded',False),('synthetic',True)]:
  subset=[x for x in pairs if x['synthetic']==is_synthetic]
  groups[name]={'queries':len(subset),'before_reached':sum(x['before_reached'] for x in subset),'after_reached':sum(x['after_reached'] for x in subset),
    'before_termination':dict(Counter(x['before_termination'] for x in subset)),'after_termination':dict(Counter(x['after_termination'] for x in subset))}
 write(d/'SUMMARY.json',{'scope':manifest['scope'],'groups':groups,'pairs':pairs,'parameters':v['parameters'],'all_successful_paths_rechecked':True,
  'original_source_stamps_preserved':True,'input_and_cpp_sha256_independently_verified':True})
 print(json.dumps(groups,indent=2),flush=True)
if __name__=='__main__':main()
