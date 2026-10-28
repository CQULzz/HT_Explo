from pathlib import Path
import json,gzip,hashlib,csv
from collections import Counter,OrderedDict
import numpy as np
from scipy.ndimage import maximum_filter,minimum_filter,uniform_filter
O=Path(__file__).parent;protocol=json.loads((O/'PROTOCOL.json').read_text());registry=json.loads((O/'DATASETS.json').read_text());allselected=[];summaries=[];patches=[];masks=[];padding_masks=[];expected=[];cache=OrderedDict()
def get(path):
 if path in cache:cache.move_to_end(path);return cache[path]
 with np.load(path) as z:
  q={k:z[k].copy() for k in ['height','observed','inferred_ground','obstacle_context','support','occupied','probabilities','geometry','source_stamp']}
 q['span']=(maximum_filter(q['height'],51)-minimum_filter(q['height'],51))[25:-25,25:-25];q['count']=np.rint(uniform_filter(q['observed'].astype(np.float32),51)*2601).astype(int)[25:-25,25:-25];q['context_occupied']=maximum_filter(np.isfinite(q['obstacle_context']),51)[25:-25,25:-25];q['padding']=~q['observed']&~q['inferred_ground']&~np.isfinite(q['obstacle_context']);cache[path]=q
 if len(cache)>16:cache.popitem(last=False)
 return q
pool_stream=gzip.open(O/'CANDIDATE_POOL.jsonl.gz','wt',compresslevel=3)
for case_index,dataset in enumerate(registry):
 frames=json.loads(Path(dataset['results']).read_text())['frames'];files=sorted(Path(dataset['contexts']).glob('*.npz'));assert len(files)==len(frames);times=np.array([x['t_s'] for x in frames]);pool=[];seen=set();rng=np.random.default_rng(20261029+100*case_index)
 for a in range(len(files)):
  qa=get(str(files[a]));cx,cy=qa['geometry'][:2]
  xx=np.arange(np.ceil(cx-4.8),np.floor(cx+4.8)+1,1);yy=np.arange(np.ceil(cy-4.8),np.floor(cy+4.8)+1,1)
  for lag in [.5,2.5,5.]:
   target=times[a]+lag;b=int(np.argmin(abs(times-target)))
   if b<=a or abs(times[b]-target)>.35:continue
   qb=get(str(files[b]));bx,by=qb['geometry'][:2]
   for x in xx:
    for y in yy:
     key=(a,b,int(x),int(y))
     if key in seen:continue
     seen.add(key);ia,ja=np.rint([120-(x-cx)/.04,120-(y-cy)/.04]).astype(int);ib,jb=np.rint([120-(x-bx)/.04,120-(y-by)/.04]).astype(int)
     if not (0<=ia<241 and 0<=ja<241 and 0<=ib<241 and 0<=jb<241):continue
     if not (qa['support'][ia,ja] and qb['support'][ib,jb]) or qa['occupied'][ia,ja] or qb['occupied'][ib,jb]:continue
     cov=min(qa['count'][ia,ja],qb['count'][ib,jb])/2601.;span=max(float(qa['span'][ia,ja]),float(qb['span'][ib,jb]));ctxocc=bool(qa['context_occupied'][ia,ja] or qb['context_occupied'][ib,jb])
     if span<=.2 and not ctxocc:stratum='high_coverage_low_relief' if cov>=.98 else 'partial_coverage_low_relief'
     else:stratum='high_relief_or_occupied_context'
     ta=qa['probabilities'][:,ia,ja];tb=qb['probabilities'][:,ib,jb]
     ga=bool(np.min(ta)>=.5);gb=bool(np.min(tb)>=.5);ra=bool(np.max(ta)<.5);rb=bool(np.max(tb)<.5)
     outcome='allgreen_to_allgreen' if ga and gb else 'allred_to_allred' if ra and rb else 'allgreen_to_allred' if ga and rb else 'allred_to_allgreen' if ra and gb else 'mixed'
     row={'dataset':dataset['id'],'bag':dataset['bag'],'filter':dataset['filter'],'before':a,'after':b,'t_before':float(times[a]),'t_after':float(times[b]),'target_lag_s':lag,'actual_lag_s':float(times[b]-times[a]),'world_x':float(x),'world_y':float(y),'old_index':[int(ia),int(ja)],'new_index':[int(ib),int(jb)],'coverage_min':float(cov),'patch_span_max_m':span,'occupied_context':ctxocc,'stratum':stratum,'outcome':outcome,'before_all8':ta.tolist(),'after_all8':tb.tolist(),'world_time_block':[int(np.floor(x/2.4)),int(np.floor(y/2.4)),int(times[a]//5)]}
     pool.append(row);pool_stream.write(json.dumps(row)+'\n')
 selections=[];used=set()
 for stratum in protocol['sampling']['main_input_strata']:
  indexes=[i for i,row in enumerate(pool) if row['stratum']==stratum];n=min(64,len(indexes));chosen=rng.choice(indexes,n,replace=False) if n else []
  for i in chosen:selections.append((int(i),'main'));used.add(int(i))
 for outcome in protocol['sampling']['control_groups']:
  indexes=[i for i,row in enumerate(pool) if row['outcome']==outcome and i not in used];n=min(16,len(indexes));chosen=rng.choice(indexes,n,replace=False) if n else []
  for i in chosen:selections.append((int(i),'output_conditioned_control'));used.add(int(i))
 for index,cohort in selections:
  row=dict(pool[index]);row['cohort']=cohort;row['sample']=len(allselected);qa=get(str(files[row['before']]));qb=get(str(files[row['after']]));hs=[];obs=[];pad=[]
  for q,ind in [(qa,row['old_index']),(qb,row['new_index'])]:
   i,j=ind;hs.append(q['height'][i:i+51,j:j+51].copy());obs.append(q['observed'][i:i+51,j:j+51].copy());pad.append(q['padding'][i:i+51,j:j+51].copy());assert hs[-1].shape==(51,51)
  patches.append(hs);masks.append(obs);padding_masks.append(pad);expected.append([row['before_all8'],row['after_all8']]);allselected.append(row)
 summary={'dataset':dataset['id'],'eligible_pairs':len(pool),'pool_strata':dict(Counter(r['stratum'] for r in pool)),'pool_outcomes':dict(Counter(r['outcome'] for r in pool)),'selected_by_cohort':dict(Counter(c for _,c in selections)),'selected_main_strata':dict(Counter(pool[i]['stratum'] for i,c in selections if c=='main')),'selected_control_outcomes':dict(Counter(pool[i]['outcome'] for i,c in selections if c!='main')),'unique_world_points_selected':len(set((pool[i]['world_x'],pool[i]['world_y']) for i,c in selections)),'world_time_blocks_selected':len(set(tuple(pool[i]['world_time_block']) for i,c in selections))}
 summaries.append(summary);print(summary,flush=True);cache.clear()
pool_stream.close();np.savez_compressed(O/'INPUTS.npz',height=np.array(patches,np.float32),observed=np.array(masks,bool),nearest_padding=np.array(padding_masks,bool),expected=np.array(expected,np.float32));(O/'SAMPLES.json').write_text(json.dumps(allselected,indent=2)+'\n');(O/'SELECTION_SUMMARY.json').write_text(json.dumps(summaries,indent=2)+'\n')
frozen={'protocol_sha256':hashlib.sha256((O/'PROTOCOL.json').read_bytes()).hexdigest(),'selection_sha256':hashlib.sha256((O/'SAMPLES.json').read_bytes()).hexdigest(),'inputs_sha256':hashlib.sha256((O/'INPUTS.npz').read_bytes()).hexdigest(),'samples':len(allselected),'selection_frozen_before_interventions':True};(O/'SELECTION_FROZEN.json').write_text(json.dumps(frozen,indent=2)+'\n');print(frozen,flush=True)
