from pathlib import Path
import json,hashlib,sys,time
import numpy as np
import torch
O=Path(__file__).parent;R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
from model import load_student_model
protocol=json.loads((O/'PROTOCOL.json').read_text());frozen=json.loads((O/'SELECTION_FROZEN.json').read_text());assert hashlib.sha256((O/'PROTOCOL.json').read_bytes()).hexdigest()==frozen['protocol_sha256'];assert hashlib.sha256((O/'INPUTS.npz').read_bytes()).hexdigest()==frozen['inputs_sha256']
samples=json.loads((O/'SAMPLES.json').read_text());z=np.load(O/'INPUTS.npz');h=z['height'];observed=z['observed'];padding=z['nearest_padding'];expected=z['expected'];N=len(h);ii,jj=np.indices((51,51));A=np.c_[ii.ravel()*.04,jj.ravel()*.04,np.ones(2601)];pinv=np.linalg.pinv(A);coef=h.reshape(N,2,2601).astype(np.float64)@pinv.T;plane=(coef@A.T).reshape(N,2,51,51).astype(np.float32);res=h-plane;std=res.std(axis=(-1,-2));safe=(std[:,0]>1e-6)&(std[:,1]>1e-6);ra=res[:,0];rb=res[:,1];pa=plane[:,0];pb=plane[:,1];ha=h[:,0];hb=h[:,1];matched=observed[:,0]&observed[:,1]
names=['actual_before','actual_after','reconstruct_before','reconstruct_after','new_plane_old_residual','old_plane_new_residual','old_plane_only','new_plane_only','equal_rms_old_pattern','new_pattern_old_rms','observed_only_restore','padding_only_restore','alpha025','alpha050','alpha075','alpha125','alpha150'];variants=[ha,hb,pa+ra,pb+rb,pb+ra,pa+rb,pa,pb,pb+ra*(std[:,1]/np.maximum(std[:,0],1e-6))[:,None,None],pb+rb*(std[:,0]/np.maximum(std[:,1],1e-6))[:,None,None],np.where(matched,pb+ra,hb),np.where(padding[:,1],pb+ra,hb),pb+.25*rb,pb+.5*rb,pb+.75*rb,pb+1.25*rb,pb+1.5*rb];v=np.stack(variants,axis=1).astype(np.float32);assert np.isfinite(v).all();hashes=np.empty((N,len(names)),dtype='S64')
for i in range(N):
 for k in range(len(names)):hashes[i,k]=hashlib.sha256(v[i,k].tobytes()).hexdigest().encode()
torch.set_num_threads(4);torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False;weights=R/'tools/ht_cupy_bridge/student_best_epoch_weights.pth';assert hashlib.sha256(weights.read_bytes()).hexdigest()==protocol['validation']['frozen_checkpoint_sha256'];model=load_student_model(str(weights),torch.device('cuda'))
def infer(inp,model=model):
 result=[]
 with torch.inference_mode():
  for i in range(0,len(inp),64):
   x=torch.from_numpy(np.ascontiguousarray(inp[i:i+64])).cuda();y=torch.softmax(model(x[:,None]),dim=2)[:,:,1,0,0].cpu().numpy();result.append(y)
 return np.concatenate(result)
start=time.perf_counter();pred=infer(v.reshape(-1,51,51)).reshape(N,len(names),8);elapsed=time.perf_counter()-start;err=np.max(abs(pred[:,:2]-expected));assert err<=1e-4,err;recon=np.max(abs(pred[:,[2,3]]-pred[:,:2]));assert recon<=1e-4,recon
rng=np.random.default_rng(20261029);repeat_ids=np.sort(rng.choice(N,min(32,N),replace=False));model2=load_student_model(str(weights),torch.device('cuda'));rep=infer(v[repeat_ids].reshape(-1,51,51),model2).reshape(len(repeat_ids),len(names),8);repeat_error=float(np.max(abs(rep-pred[repeat_ids])));assert repeat_error<=1e-4,repeat_error
np.savez_compressed(O/'OUTPUTS.npz',predictions=pred,plane=plane,residual=res,residual_std=std,equal_rms_valid=safe,variant_hashes=hashes,repeat_sample_ids=repeat_ids,repeat_predictions=rep);(O/'VARIANTS.json').write_text(json.dumps(names,indent=2)+'\n');validation={'samples':N,'variants_per_sample':len(names),'eight_channel_forward_evaluations':N*len(names),'fullmap_to_patch_max_abs_error':float(err),'identity_reconstruction_max_prob_error':float(recon),'duplicate_fresh_model_max_abs_error':repeat_error,'repeat_sample_ids':repeat_ids.tolist(),'GPU':torch.cuda.get_device_name(),'torch_version':torch.__version__,'numpy_version':np.__version__,'TF32_disabled':True,'no_production_changes':True,'elapsed_s_not_live_rate':elapsed};(O/'VALIDATION.json').write_text(json.dumps(validation,indent=2)+'\n');print(validation,flush=True)
# Noise stress: common noise realizations across sigma and base types.
selected=[]
for dataset in json.loads((O/'DATASETS.json').read_text()):
 ids=[i for i,s in enumerate(samples) if s['dataset']==dataset['id'] and s['cohort']=='main' and s['stratum']=='high_coverage_low_relief'];selected+=rng.choice(ids,min(16,len(ids)),replace=False).tolist() if ids else []
noise_meta=[];noise_inputs=[];unit=[]
for sample in selected:
 this=[]
 for seed in protocol['noise_stress']['seeds']:
  noise=np.random.default_rng(seed+100000*sample).normal(size=(51,51)).astype(np.float32);this.append(noise)
  for base,label in [(hb[sample],'actual_new'),(pb[sample],'fitted_plane')]:
   for sigma in protocol['noise_stress']['iid_sigma_m']:
    arr=base+sigma*noise;noise_inputs.append(arr);noise_meta.append({'sample':sample,'dataset':samples[sample]['dataset'],'bag':samples[sample]['bag'],'filter':samples[sample]['filter'],'base':label,'sigma_m':sigma,'seed':seed,'input_sha256':hashlib.sha256(arr.tobytes()).hexdigest()})
 unit.append(this)
if noise_inputs:
 noise_pred=infer(np.array(noise_inputs,np.float32));np.savez_compressed(O/'NOISE_OUTPUTS.npz',predictions=noise_pred,noise_unit_fields=np.array(unit,np.float32),sample_ids=np.array(selected,int));(O/'NOISE_SAMPLES.json').write_text(json.dumps(noise_meta,indent=2)+'\n')
else:raise RuntimeError('No high-coverage low-relief stress candidates; preserve empty outcome and revise reporting, not sampling')
print('noise stress',len(noise_meta),'forwards from',len(selected),'recorded patches',flush=True)
