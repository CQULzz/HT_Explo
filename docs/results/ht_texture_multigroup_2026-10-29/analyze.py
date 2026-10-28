from pathlib import Path
import json,csv
from collections import Counter
import numpy as np
O=Path(__file__).parent;samples=json.loads((O/'SAMPLES.json').read_text());z=np.load(O/'OUTPUTS.npz');p=z['predictions'];names=json.loads((O/'VARIANTS.json').read_text());v={name:p[:,i] for i,name in enumerate(names)};old=v['actual_before'];new=v['actual_after'];er=.5*((v['old_plane_new_residual']-old)+(new-v['new_plane_old_residual']));ep=.5*((v['new_plane_old_residual']-old)+(new-v['old_plane_new_residual']));inter=new-v['new_plane_old_residual']-v['old_plane_new_residual']+old;assert np.max(abs(er+ep-(new-old)))<1e-6
r=np.mean(abs(er),axis=1);e=np.mean(abs(ep),axis=1);interaction=np.mean(abs(inter),axis=1);delta=np.mean(abs(new-old),axis=1);changed=delta>=.1;rd=changed&(r>=2*e);pd=changed&(e>=2*r);heavy=interaction>=.1;main=np.array([s['cohort']=='main' for s in samples]);rows=[]
alpha_names=['new_plane_only','alpha025','alpha050','alpha075','actual_after','alpha125','alpha150'];alpha_pred=np.stack([v[k].mean(axis=1) for k in alpha_names],axis=1);nonmono=(np.diff(alpha_pred,axis=1)>.05).any(axis=1)
for i,s in enumerate(samples):
 row={**{k:s[k] for k in ['sample','dataset','bag','filter','cohort','stratum','outcome','before','after','t_before','t_after','actual_lag_s','target_lag_s','world_x','world_y','coverage_min','patch_span_max_m']},'mean_abs_delta':float(delta[i]),'mean_abs_residual_effect':float(r[i]),'mean_abs_plane_effect':float(e[i]),'mean_abs_interaction':float(interaction[i]),'material_change':bool(changed[i]),'residual_dominant_2x':bool(rd[i]),'plane_dominant_2x':bool(pd[i]),'large_interaction':bool(heavy[i]),'alpha_score_rise_over_point05':bool(nonmono[i]),'old_meanT':float(old[i].mean()),'new_meanT':float(new[i].mean()),'old_minT':float(old[i].min()),'new_maxT':float(new[i].max()),'new_plane_old_res_meanT':float(v['new_plane_old_residual'][i].mean()),'old_plane_new_res_meanT':float(v['old_plane_new_residual'][i].mean()),'equal_rms_old_pattern_meanT':float(v['equal_rms_old_pattern'][i].mean()),'new_pattern_old_rms_meanT':float(v['new_pattern_old_rms'][i].mean()),'equal_rms_valid':bool(z['equal_rms_valid'][i]),'residual_std_before_cm':float(z['residual_std'][i,0]*100),'residual_std_after_cm':float(z['residual_std'][i,1]*100)};rows.append(row)
(O/'METRICS.json').write_text(json.dumps(rows,indent=2)+'\n')
with (O/'METRICS.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def summary(mask):
 ids=np.flatnonzero(mask);ch=ids[changed[ids]]
 return {'samples':len(ids),'materially_changed':len(ch),'residual_dominant_among_changed':int(rd[ch].sum()),'plane_dominant_among_changed':int(pd[ch].sum()),'mixed_among_changed':int((~rd[ch]&~pd[ch]).sum()),'large_interaction_among_changed':int(heavy[ch].sum()),'median_abs_delta':float(np.median(delta[ids])) if len(ids) else None,'median_residual_effect':float(np.median(r[ids])) if len(ids) else None,'median_plane_effect':float(np.median(e[ids])) if len(ids) else None,'alpha_nonmonotonic_rise_samples':int(nonmono[ids].sum()),'actual_outcomes':dict(Counter(samples[i]['outcome'] for i in ids))}
result={'scope':'Conditional descriptions of paired overlapping windows from2real clips; no physical traversability ground truth or independent-trial rates','main':summary(main),'controls':summary(~main),'by_dataset':{},'main_by_stratum':{},'main_by_lag':{}}
for d in json.loads((O/'DATASETS.json').read_text()):
 mask=np.array([s['dataset']==d['id'] for s in samples]);result['by_dataset'][d['id']]={'main':summary(main&mask),'controls':summary(~main&mask),'strata':{}}
 for t in ['high_coverage_low_relief','partial_coverage_low_relief','high_relief_or_occupied_context']:
  result['by_dataset'][d['id']]['strata'][t]=summary(main&mask&np.array([s['stratum']==t for s in samples]))
for t in ['high_coverage_low_relief','partial_coverage_low_relief','high_relief_or_occupied_context']:result['main_by_stratum'][t]=summary(main&np.array([s['stratum']==t for s in samples]))
for lag in [.5,2.5,5.]:result['main_by_lag'][str(lag)]=summary(main&np.array([s['target_lag_s']==lag for s in samples]))
# All output-conditioned controls remain separate from primary sampling.
result['control_groups']={k:summary(~main&np.array([s['outcome']==k for s in samples])) for k in ['allgreen_to_allgreen','allred_to_allred','allgreen_to_allred','allred_to_allgreen']}
noise_meta=json.loads((O/'NOISE_SAMPLES.json').read_text());npred=np.load(O/'NOISE_OUTPUTS.npz')['predictions'];noise_summary=[]
for d in ['original_moving','plus20_moving']:
 for base in ['actual_new','fitted_plane']:
  for sigma in [0,.005,.01,.015,.02,.03]:
   ids=[i for i,s in enumerate(noise_meta) if s['dataset']==d and s['base']==base and s['sigma_m']==sigma];a=npred[ids]
   noise_summary.append({'dataset':d,'base':base,'sigma_m':sigma,'forwards':len(ids),'distinct_base_patches':len(set(noise_meta[i]['sample'] for i in ids)),'all8_above_half_fraction':float(np.mean(a.min(axis=1)>=.5)) if len(ids) else None,'mean8_median':float(np.median(a.mean(axis=1))) if len(ids) else None,'mean8_p25_p75':np.quantile(a.mean(axis=1),[.25,.75]).tolist() if len(ids) else None})
result['noise_stress']=noise_summary
# Representative charts use nearest-median effects; an explicitly labelled
# strongest plane-dominant counterexample is also retained, never hidden.
chosen=[]
for outcome in ['allgreen_to_allred','allgreen_to_allgreen','allred_to_allred','allred_to_allgreen']:
 ids=np.array([i for i,s in enumerate(samples) if s['outcome']==outcome and s['stratum']=='high_coverage_low_relief'],int)
 if len(ids)==0:ids=np.array([i for i,s in enumerate(samples) if s['outcome']==outcome],int)
 if len(ids):chosen.append({'role':outcome,'sample':int(ids[np.argmin(abs(delta[ids]-np.median(delta[ids])))]),'selection':'closest to median actual8-channel change, prefer high-coverage low-relief'})
ids=np.flatnonzero(main&pd)
if len(ids):chosen.append({'role':'plane_dominant_counterexample','sample':int(ids[np.argmax(e[ids]-r[ids])]),'selection':'largest plane-minus-residual effect among primary materially changed, explicitly extreme counterexample'})
ids=np.flatnonzero(main&heavy)
if len(ids):chosen.append({'role':'large_interaction_counterexample','sample':int(ids[np.argmax(interaction[ids])]),'selection':'largest interaction among primary, explicitly extreme counterexample'})
(O/'REPRESENTATIVE_CASES.json').write_text(json.dumps(chosen,indent=2)+'\n');(O/'SUMMARY.json').write_text(json.dumps(result,indent=2)+'\n');np.savez_compressed(O/'EFFECTS.npz',residual_effect=er,plane_effect=ep,interaction=inter,alpha_predictions=alpha_pred)
print(json.dumps({k:v for k,v in result.items() if k not in ['by_dataset','noise_stress','control_groups']},indent=2),flush=True);print('cases',chosen,flush=True)
