from pathlib import Path
import sys,json,hashlib
import numpy as np,torch
sys.path.insert(0,str(Path.cwd()/'tools/ht_cupy_bridge'))
from model import load_student_model,GRADIENT_KERNEL
from elevation_quality import preprocess_elevation
torch.set_num_threads(2)
torch.set_num_interop_threads(1)
base=Path('presentations/scheduled_results/ht_tare_native_5scene_10min_2026-10-20_19-39-37/indoor/current/inference_context')
out=Path('.git/diagnostics/indoor_ht_input')
model=load_student_model('tools/ht_cupy_bridge/student_best_epoch_weights.pth',torch.device('cpu'))
points=np.array([[2.25,5.25],[2.55,5.25],[2.85,5.25],[3.15,5.25],[2.25,5.55],[2.55,5.55],[2.85,5.55],[3.15,5.55],[3.45,5.55],[3.75,5.55],[3.45,5.85],[3.75,5.85]])
results=[]
for name in ['1792497888_335909632.npz','1792497898_340915712.npz']:
 d=np.load(base/name);cx,cy,res=d['geometry'];h=d['height'];n=241
 patches=[];rows=[]
 for x,y in points:
  i=int(np.floor(n*.5-(x-cx)/res));j=int(np.floor(n*.5-(y-cy)/res))
  if not (0<=i<n and 0<=j<n):continue
  p=h[i:i+51,j:j+51];patches.append(p);rows.append(dict(xy=[x,y],index=[i,j],recorded_prob=d['probabilities'][:,i,j].tolist(),observed_at_center=bool(d['observed'][i+25,j+25]),raw_center=float(d['raw_history'][i+25,j+25]),center_network_height=float(p[25,25]),height_percentiles=np.percentile(p,[0,10,50,90,100]).tolist(),above03_fraction=float((p>.3).mean()),support=bool(d['support'][i,j]),physical=bool(d['physical_support'][i,j])))
 patches=np.asarray(patches,np.float32)
 if not len(patches):
  results.append(dict(context=name,source_stamp=float(d['source_stamp']),geometry=d['geometry'].tolist(),rows=[],note='All12 gatepoints outside241x241 output at this earlier context'))
  continue
 variants={'recorded':patches,'add10':patches+10,'half_gradient':patches*.5,'double_gradient':patches*2,'flatten_small_texture':np.where(abs(patches)<.075,0,patches),'flatten_all':np.zeros_like(patches),'remove_above03':np.minimum(patches,.3),'clip_abs01':np.clip(patches,-.1,.1)}
 for key,arr in variants.items():
  with torch.inference_mode():pred=torch.softmax(model(torch.from_numpy(arr[:,None])),dim=2)[:,:,1,0,0].numpy()
  for row,p in zip(rows,pred):row[key]=p.tolist();row[key+'_max']=float(p.max())
 for row in rows:
  row['reproduction_absmax']=max(abs(a-b) for a,b in zip(row['recorded_prob'],row['recorded']))
  row['constant_shift_absmax']=max(abs(a-b) for a,b in zip(row['recorded'],row['add10']))
 results.append(dict(context=name,source_stamp=float(d['source_stamp']),geometry=d['geometry'].tolist(),rows=rows))
 np.savez_compressed(out/(name+'.patches.npz'),patches=patches,points=points)
# Exact-stamp recorded prefilter replay: this fixture is the18.137s input,
# not the13.512s completion-trigger input.
snapshot=Path('presentations/scheduled_results/ht_tare_native_5scene_10min_2026-10-20_19-39-37/indoor/snapshots/frame_0003.npz')
with np.load(snapshot) as snap:
 quality=preprocess_elevation(snap['history_elevation_raw'],snap['history_variance'],float(snap['ht_geometry'][2]))
 quality_error=float(np.nanmax(abs(quality.height_m-snap['history_elevation'])))
 for row in results[-1]['rows']:
  i,j=row['index'];raw=snap['history_elevation_raw'][i:i+51,j:j+51];var=snap['history_variance'][i:i+51,j:j+51];filt=snap['history_elevation'][i:i+51,j:j+51];known=np.isfinite(raw);changed=known&(raw!=filt)
  row.update(quality_input_observed_fraction=float(known.mean()),quality_changed_fraction=float(changed.mean()),quality_changed_observed_fraction=float(changed.sum()/known.sum()),variance_observed_percentiles=np.percentile(var[known],[0,10,50,90,100]).tolist(),height_raw_percentiles=np.percentile(raw[known],[0,10,50,90,100]).tolist(),height_filtered_percentiles=np.percentile(filt[known],[0,10,50,90,100]).tolist())
source_paths=[Path('tools/ht_cupy_bridge')/n for n in ['cupy_to_ht.py','ht_support.py','elevation_quality.py','local_surface.py','historical_elevation.py','model.py','student_best_epoch_weights.pth']]
source_hashes={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
result=dict(source_hashes=source_hashes,quality_reproduction_max_abs_error_m=quality_error,quality_reproduction_stats=quality.stats,gradient_kernel_max_error=float((model.conv_grad.weight-GRADIENT_KERNEL).abs().max()),gradient_std_m=model.ht_grad_activate.std_m,model_eval=not model.training,scope='Diagnostic offline interventions only: clipping/removing high terrain is not a safe navigation change. Context dumps are ten-second cadence, not the exact13.512s trigger map.',results=results)
def portable(value):
 if isinstance(value,dict):return {k:portable(v) for k,v in value.items()}
 if isinstance(value,list):return [portable(v) for v in value]
 if isinstance(value,float) and not np.isfinite(value):return None
 return value
(out/'model_checks.json').write_text(json.dumps(portable(result),indent=2,allow_nan=False)+'\n')
print('kernel error',result['gradient_kernel_max_error'])
for case in results:
 print(case['context'])
 for row in case['rows']:
  print(row['xy'],'support',row['support'],'orig',round(row['recorded_max'],3),'smalltexture',round(row['flatten_small_texture_max'],3),'flat',round(row['flatten_all_max'],3),'clip01',round(row['clip_abs01_max'],3),'q',np.round(row['height_percentiles'],3),'reproduction',row['reproduction_absmax'])
