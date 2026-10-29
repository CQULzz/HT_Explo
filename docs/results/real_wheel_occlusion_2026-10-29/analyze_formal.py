from pathlib import Path
import json,numpy as np,csv,hashlib
O=Path(__file__).parent;R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');L=Path('/media/lzz/My Passport/HT_texture_source_fix_2026-10-29');cases={'default_stationary':B/'rebuild_165317','default_moving':B/'rebuild_170043','registered_stationary':L/'frozen_original_stationary','registered_moving':L/'frozen_original_moving'};summary=[];series={};rows=[]
for case,old in cases.items():
 new=O/('frozen_'+case);a=json.load(open(old/'RESULTS.json'));b=json.load(open(new/'RESULTS.json'));assert len(a['frames'])==len(b['frames']);out=[]
 for n,(one,two) in enumerate(zip(a['frames'],b['frames'])):
  assert one['stamp_ns']==two['stamp_ns'];fields=[]
  for folder,row in [(old,one),(new,two)]:
   z=np.load(folder/'frames'/row['file']);i,j=np.indices((241,241));xy=z['center']+np.stack([120-i,120-j],axis=-1)*.04;robot=z['robot'];delta=xy-robot[:2];c,s=np.cos(robot[3]),np.sin(robot[3]);local=delta@np.array([[c,-s],[s,c]]);near=np.sum(delta**2,axis=-1)<1.5**2;rear=(local[:,:,0]>-1.1)&(local[:,:,0]<-.1)&(abs(local[:,:,1])<.8)&((abs(local[:,:,0])>.49)|(abs(local[:,:,1])>.37));p=np.stack([z['ht_dir_'+str(k)] for k in range(8)]);valid=z['ht_valid']>.5;red=valid&(p<.5).all(axis=0);obs=z['ht_observation_valid']>.5
   fields.append({'near_red':int((near&red).sum()),'rear_red':int((rear&red).sum()),'near_unknown':int((near&~valid).sum()),'rear_unknown':int((rear&~valid).sum()),'near_physical_unknown':int((near&~obs).sum()),'center_valid':bool(valid[120,120]),'center_min8':float(np.min(p[:,120,120])),'global_cells':int(row['global_cells'])});z.close()
  record={'case':case,'frame':n,'t_s':one['t_s'],'stamp_ns':one['stamp_ns']}
  for prefix,field in zip(['old','new'],fields):record.update({prefix+'_'+k:v for k,v in field.items()})
  out.append(record);rows.append(record)
 series[case]=out
 for period in ['whole','known_tail_5to27s']:
  rr=[x for x in out if period=='whole' or 5<=x['t_s']<=27];group={'case':case,'period':period,'frames':len(rr),'input_scans':b['input_scans'],'integrated_scans':b['integrated'],'new_occlusion_removed_points':sum(x.get('wheel_occlusion_removed_points',0) for x in b['scans'])}
  for role in ['old','new']:
   for k in ['near_red','rear_red','near_unknown','rear_unknown','near_physical_unknown']:group[role+'_'+k+'_median']=float(np.median([x[role+'_'+k] for x in rr]))
   group[role+'_center_valid_frames']=sum(x[role+'_center_valid'] for x in rr)
  summary.append(group);print(group,flush=True)
# Prove that opting out with the saved original calibration reproduces all arrays.
x=json.load(open(O/'frozen_disabled_baseline_moving/RESULTS.json'));y=json.load(open(L/'frozen_original_moving/RESULTS.json'));exact=[]
for a,b in zip(x['frames'],y['frames']):
 with np.load(O/'frozen_disabled_baseline_moving/frames'/a['file']) as one,np.load(L/'frozen_original_moving/frames'/b['file']) as two:exact.append(set(one.files)==set(two.files) and all(np.array_equal(one[k],two[k],equal_nan=True) for k in one.files))
assert len(exact)==64 and all(exact)
f=json.load(open(O/'CANDIDATE_FREEZE.json'));assert all(hashlib.sha256((Path(p) if Path(p).is_absolute() else R/p).read_bytes()).hexdigest()==h for p,h in f['source_hashes'].items())
(O/'SUMMARY.json').write_text(json.dumps({'scope':'Two real clips, body filter on/off comparisons under two fixed mapper registration settings. Not four independent field trials. Model low-score counts, not terrain ground truth or physical driving success.','summary':summary,'series':series,'disabled_all_64_frames_all_arrays_exact':True,'frozen_sources_unchanged':True},indent=2)+'\n')
with (O/'FRAME_METRICS.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
