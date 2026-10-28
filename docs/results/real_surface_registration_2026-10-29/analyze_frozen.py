from pathlib import Path
from functools import lru_cache
from collections import Counter
import json,csv,hashlib,numpy as np
O=Path(__file__).parent;R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');P=Path('/media/lzz/My Passport/HT_filter_expansion_2026-10-29');STUDY=Path('/media/lzz/My Passport/HT_texture_multigroup_2026-10-29')
cases={'original_stationary':B/'rebuild_165317','original_moving':B/'rebuild_170043','plus20_stationary':P/'pad020_165317','plus20_moving':P/'pad020_170043'}
@lru_cache(maxsize=64)
def frame(folder,index):
 results=meta[str(folder)];row=results['frames'][index]
 with np.load(folder/'frames'/row['file']) as d:
  return {'prob':np.stack([d['ht_dir_'+str(k)] for k in range(8)]),'valid':d['ht_valid']>.5,'height':d['local_elevation'],'native':d['native_elevation'],'center':d['center'],'resolution':float(d['resolution']),'robot':d['robot'],'ht_elevation':d['ht_elevation'],'observation':d['ht_observation_valid']>.5,'hard':d['ht_obstacle']>.5}
meta={}
for key,old in cases.items():
 for p in [old,O/('frozen_'+key)]:meta[str(p)]=json.loads((p/'RESULTS.json').read_text())
# Disabled path must reproduce every archived array, including global history.
a=json.loads((O/'frozen_disabled_moving/RESULTS.json').read_text());b=meta[str(cases['original_moving'])];exact=[]
assert len(a['frames'])==len(b['frames'])==64
for x,y in zip(a['frames'],b['frames']):
 with np.load(O/'frozen_disabled_moving/frames'/x['file']) as one,np.load(cases['original_moving']/'frames'/y['file']) as two:
  assert set(one.files)==set(two.files);exact.append(all(np.array_equal(one[k],two[k],equal_nan=True) for k in one.files))
assert all(exact)
summary={'scope':'Frozen offline two-clip regression; four processing cases, not independent scene trials. All rates below refer to model outputs, not labelled traversability accuracy.','disabled_full_arrays_exact':True,'disabled_frames':64,'cases':{},'target_summary':[]};frame_rows=[];target_rows=[];targets=[[-.48,12.24],[-3.,13.],[-1.,18.]]
for key,old in cases.items():
 new=O/('frozen_'+key);ma,mb=meta[str(old)],meta[str(new)];assert len(ma['frames'])==len(mb['frames']);assert [r['stamp_ns'] for r in ma['frames']]==[r['stamp_ns'] for r in mb['frames']]
 status=Counter(r['surface_registration']['status'] for r in mb['scans'] if r['status']=='INTEGRATED');runtime=[r['surface_registration'].get('elapsed_s') for r in mb['scans'] if r['status']=='INTEGRATED'];runtime=[x for x in runtime if x is not None]
 stats={'source_scans':mb['input_scans'],'integrated_scans':mb['integrated'],'output_frames':mb['outputs'],'registration_status_counts':dict(status),'registration_ms_p50_p95':(np.quantile(runtime,[.5,.95])*1000).tolist(),'source_span_s':(mb['scans'][-1]['stamp_ns']-mb['scans'][0]['stamp_ns'])/1e9};summary['cases'][key]=stats
 for i,(oldrow,newrow) in enumerate(zip(ma['frames'],mb['frames'])):
  aa,bb=frame(old,i),frame(new,i);joint=aa['valid']&bb['valid'];p,q=aa['prob'],bb['prob'];row={'case':key,'frame':i,'t_s':oldrow['t_s'],'old_valid_cells':int(aa['valid'].sum()),'new_valid_cells':int(bb['valid'].sum()),'joint_valid':int(joint.sum()),'old_all8red_cells':int(((p<.5).all(axis=0)&aa['valid']).sum()),'new_all8red_cells':int(((q<.5).all(axis=0)&bb['valid']).sum()),'old_hard_cells':int(aa['hard'].sum()),'new_hard_cells':int(bb['hard'].sum()),'joint_mean_abs_delta':float(np.mean(abs(p[:,joint]-q[:,joint]))) if joint.any() else None};frame_rows.append(row)
  for xy in targets:
   ij=np.rint(p.shape[1]//2+(aa['center']-xy)/aa['resolution']).astype(int);ii,jj=ij
   if not (0<=ii<p.shape[1] and 0<=jj<p.shape[2]):continue
   for role,ff in [('old',aa),('new',bb)]:
    v=ff['prob'][:,ii,jj];height=ff['height'];patch=height[ii:ii+51,jj:jj+51];finite=np.isfinite(patch)
    if finite.sum()>50:
     x,y=np.indices(patch.shape);A=np.c_[x[finite]*ff['resolution'],y[finite]*ff['resolution'],np.ones(finite.sum())];res=patch[finite]-A@np.linalg.lstsq(A,patch[finite],rcond=None)[0];rms=float(np.sqrt(np.mean(res**2)))
    else:rms=None
    target_rows.append({'case':key,'frame':i,'t_s':oldrow['t_s'],'xy':xy,'role':role,'valid':bool(ff['valid'][ii,jj]),'prob8':v.tolist(),'mean8':float(np.mean(v)),'min8':float(np.min(v)),'all8red':bool((v<.5).all()),'patch_finite':int(finite.sum()),'local_detrended_rms_m':rms})
 for xy in targets:
  oldt=[r for r in target_rows if r['case']==key and r['xy']==xy and r['role']=='old'];newt=[r for r in target_rows if r['case']==key and r['xy']==xy and r['role']=='new'];assert len(oldt)==len(newt);joint=[(a,b) for a,b in zip(oldt,newt) if a['valid'] and b['valid']]
  summary['target_summary'].append({'case':key,'xy':xy,'frames_within_crop':len(oldt),'old_valid':sum(r['valid'] for r in oldt),'new_valid':sum(r['valid'] for r in newt),'joint_valid':len(joint),'old_allred_on_joint':sum(a['all8red'] for a,b in joint),'new_allred_on_joint':sum(b['all8red'] for a,b in joint),'old_mean8_median_joint':float(np.median([a['mean8'] for a,b in joint])) if joint else None,'new_mean8_median_joint':float(np.median([b['mean8'] for a,b in joint])) if joint else None,'old_local_rms_median_joint_m':float(np.median([a['local_detrended_rms_m'] for a,b in joint])) if joint else None,'new_local_rms_median_joint_m':float(np.median([b['local_detrended_rms_m'] for a,b in joint])) if joint else None})
# Evaluate the previously frozen 640 primary +192 outcome controls. Do not reselect.
samples=json.loads((STUDY/'SAMPLES.json').read_text());samples_out=[];oldmax=0.
for sample in samples:
 key=sample['dataset'];old=cases[key];new=O/('frozen_'+key);oldp=[];newp=[];newvalid=[]
 for part in ['before','after']:
  i=sample[part];ii,jj=sample['old_index' if part=='before' else 'new_index'];a,b=frame(old,i),frame(new,i);oldp.append(a['prob'][:,ii,jj]);newp.append(b['prob'][:,ii,jj]);newvalid.append(bool(b['valid'][ii,jj]));expected=np.array(sample[part+'_all8']);oldmax=max(oldmax,float(np.max(abs(oldp[-1]-expected))))
 oldp,newp=np.array(oldp),np.array(newp);row={'sample':sample['sample'],'case':key,'cohort':sample['cohort'],'stratum':sample['stratum'],'before':sample['before'],'after':sample['after'],'xy':[sample['world_x'],sample['world_y']],'old_prob8':oldp.tolist(),'new_prob8':newp.tolist(),'new_valid_both':all(newvalid),'new_valid_each':newvalid,'old_change_mean_abs':float(np.mean(abs(oldp[1]-oldp[0]))),'new_change_mean_abs':float(np.mean(abs(newp[1]-newp[0]))) if all(newvalid) else None,'old_green_red':bool((oldp[0]>=.5).all() and (oldp[1]<.5).all()),'new_green_red':bool(all(newvalid) and (newp[0]>=.5).all() and (newp[1]<.5).all())};samples_out.append(row)
assert oldmax<1e-4
summary['frozen_sample_reproduction_max_error']=oldmax;groups={}
for cohort in ['main','output_conditioned_control']:
 for st in ['all','high_coverage_low_relief','partial_coverage_low_relief','high_relief_or_occupied_context']:
  rows=[r for r in samples_out if r['cohort']==cohort and (st=='all' or r['stratum']==st)]
  if not rows:continue
  both=[r for r in rows if r['new_valid_both']];groups[cohort+'/'+st]={'n':len(rows),'candidate_valid_both':len(both),'candidate_one_or_both_unknown':len(rows)-len(both),'old_material_changes_all':sum(r['old_change_mean_abs']>=.1 for r in rows),'old_material_changes_joint':sum(r['old_change_mean_abs']>=.1 for r in both),'new_material_changes_joint':sum(r['new_change_mean_abs']>=.1 for r in both),'old_green_red_all':sum(r['old_green_red'] for r in rows),'old_green_red_joint':sum(r['old_green_red'] for r in both),'new_green_red_joint':sum(r['new_green_red'] for r in both),'old_change_median_joint':float(np.median([r['old_change_mean_abs'] for r in both])) if both else None,'new_change_median_joint':float(np.median([r['new_change_mean_abs'] for r in both])) if both else None,'old_stable_to_new_material':sum(r['old_change_mean_abs']<.1 and r['new_change_mean_abs']>=.1 for r in both),'old_material_to_new_stable':sum(r['old_change_mean_abs']>=.1 and r['new_change_mean_abs']<.1 for r in both)}
summary['frozen_sample_groups']=groups
f=json.loads((O/'CANDIDATE_FREEZE.json').read_text());unchanged=all(hashlib.sha256((Path(p) if Path(p).is_absolute() else R/p).read_bytes()).hexdigest()==h for p,h in f['sources'].items());assert unchanged;summary['frozen_production_sources_unchanged']=True
for name,data in [('FRAME_METRICS.json',frame_rows),('TARGETS.json',target_rows),('FROZEN_SAMPLE_RESULTS.json',samples_out),('SUMMARY.json',summary)]: (O/name).write_text(json.dumps(data,indent=2)+'\n')
with (O/'FRAME_METRICS.csv').open('w',newline='') as ff:
 w=csv.DictWriter(ff,fieldnames=list(frame_rows[0]));w.writeheader();w.writerows(frame_rows)
print(json.dumps(summary,indent=2),flush=True)
