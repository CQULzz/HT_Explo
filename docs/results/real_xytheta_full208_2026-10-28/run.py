"""Run a fresh full-frame comparison using already frozen actual C++ binaries."""
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
import argparse,json,hashlib,subprocess,time,shutil
ROOT=Path(__file__).resolve().parents[3]
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(2**20),b''):h.update(b)
 return h.hexdigest()
def read(p):return json.loads(p.read_text())
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def group(label):
 if label.startswith('recorded_'):return 'recorded'
 if label.startswith('counterfactual_heading_'):return 'counterfactual_heading'
 if label.startswith('synthetic_'):return 'synthetic'
 raise ValueError(label)
def main():
 p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--previous',type=Path,required=True);a=p.parse_args();d=a.data.resolve();freeze=read(d/'FREEZE.json');meta=read(d/'input/metadata.json')
 assert meta['recorded_frames']==208 and meta['queries']==2011,meta['queries']
 for row in freeze['production_source_checks']:assert sha(ROOT/row['file'])==row['sha256']
 for role in ['before','after']:assert sha(Path(freeze[role+'_binary']))==freeze[role+'_binary_sha256']
 oldmaps={row['label']:row['sha256'] for row in read(a.previous/'input/metadata.json')['maps']};newmaps={row['label']:row['sha256'] for row in meta['maps']}
 assert all(newmaps[k]==v for k,v in oldmaps.items()),'Existing inputs changed'
 provenance={**freeze,'execution_checkout_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'query_file_sha256':sha(d/'input/queries.tsv'),'input_metadata_sha256':sha(d/'input/metadata.json'),'experiment_script_sha256':sha(Path(__file__)),'prepare_script_sha256':sha(ROOT/'tools/ht_cupy_bridge/prepare_xytheta_replay.py'),'started_utc':datetime.now(timezone.utc).isoformat(),'previous_selected_maps_identical':True}
 write(d/'RUN_MANIFEST.json',provenance)
 for role in ['before','after']:
  target=d/(role+'.json');assert not target.exists(),target
  print('running',role,meta['queries'],'actual C++ queries',flush=True)
  started=time.monotonic()
  with (d/(role+'.log')).open('w') as log:subprocess.run([freeze[role+'_binary'],'--batch',str(d/'input/queries.tsv'),'--output',str(target)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
  provenance[role+'_wall_s']=time.monotonic()-started;print('finished',role,provenance[role+'_wall_s'],flush=True)
 b=read(d/'before.json');c=read(d/'after.json');assert b['parameters']==c['parameters'];assert len(b['queries'])==len(c['queries'])==meta['queries']
 hashes={};pairs=[]
 for x,y in zip(b['queries'],c['queries']):
  assert not x.get('error') and not y.get('error'),(x,y)
  for k in ['label','map_sha256','map_stamp_ns','start','goal']:assert x[k]==y[k],(k,x['label'])
  if x['map_file'] not in hashes:hashes[x['map_file']]=sha(Path(x['map_file']))
  assert x['map_sha256']==hashes[x['map_file']]
  assert x['map_stamp_ns']==x['clock_ns']==y['clock_ns']
  for row in [x,y]:
   if row['reached']:assert row['all_segments_permitted'] and row['independent_recheck_passed']
  pairs.append({'label':x['label'],'group':group(x['label']),'before_reached':x['reached'],'after_reached':y['reached'],'before_termination':x['termination'],'after_termination':y['termination'],'before_start_support':x['start_support'],'after_start_support':y['start_support'],'before_ms':x['search_wall_ms'],'after_ms':y['search_wall_ms']})
 groups={}
 for g in ['recorded','counterfactual_heading','synthetic']:
  subset=[row for row in pairs if row['group']==g]
  groups[g]={'queries':len(subset),'before_reached':sum(row['before_reached'] for row in subset),'after_reached':sum(row['after_reached'] for row in subset),'before_termination':dict(Counter(row['before_termination'] for row in subset)),'after_termination':dict(Counter(row['after_termination'] for row in subset)),'after_start_support':dict(Counter(row['after_start_support'] for row in subset))}
 recorded=[row for row in c['queries'] if group(row['label'])=='recorded'];byframe={}
 for row in recorded:byframe.setdefault(row['map_sha256'],row['start_support'])
 assert len(byframe)==208
 prev={row['label']:row for row in read(a.previous/'after.json')['queries']};now={row['label']:row for row in c['queries']};comparisons=[]
 for label,row in prev.items():
  cur=now[label]
  for k in ['map_sha256','start','goal']:assert row[k]==cur[k]
  comparisons.append({'label':label,'same_reached':row['reached']==cur['reached'],'previous_termination':row['termination'],'current_termination':cur['termination']})
 summary={'scope':freeze['scope'],'runtime_source_commit':freeze['runtime_source_commit'],'runtime_published_commit':freeze['runtime_published_commit'],'checkout_commit':provenance['execution_checkout_commit'],'recorded_frames':208,'source_span_s':207.587430954,'groups':groups,'recorded_start_counts_by_frame':dict(Counter(byframe.values())),'all_success_paths_rechecked':True,'source_stamps_preserved':True,'actual_cpp_and_input_hashes_verified':True,'same_frozen_binaries_as_previous_round':True,'previous_subset_result_comparison':comparisons,'query_pairs':pairs,'parameters':c['parameters'],'counterfactual_limit':'Initial headings are hypothetical, not rotations executed from recorded yaw; exclude from recorded navigation success','freshness_limit':'Clock frozen at source map stamp; no live age/network/tracking test'}
 write(d/'SUMMARY.json',summary);provenance['finished_utc']=datetime.now(timezone.utc).isoformat();write(d/'RUN_MANIFEST.json',provenance)
 print(json.dumps({'groups':groups,'recorded_frames':summary['recorded_start_counts_by_frame']},indent=2),flush=True)
if __name__=='__main__':main()
