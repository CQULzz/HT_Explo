from pathlib import Path
import sys,json,hashlib,numpy as np,torch
O=Path(__file__).parent;R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
from model import load_student_model
am=json.loads((O/'PROTOCOL_AMENDMENT_01.json').read_text());z=np.load(O/'OUTPUTS.npz');n=np.load(O/'NOISE_OUTPUTS.npz');samples=json.loads((O/'SAMPLES.json').read_text());ids=n['sample_ids'];unit=n['noise_unit_fields'];plane=z['plane'];res=z['residual'];torch.set_num_threads(4);torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False;m=load_student_model(str(R/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'),torch.device('cuda'));ii,jj=np.indices((51,51));xx=(ii-25)*.04;yy=(jj-25)*.04;inp=[];meta=[];noise_units=[]
for nidx,sample in enumerate(ids):
 sample=int(sample);p=plane[sample,1]
 for direction in am['tilt_directions_deg']:
  a=np.deg2rad(direction);ramp=(np.cos(a)*xx+np.sin(a)*yy).astype(np.float32);ramp-=ramp.mean();ramp/=ramp.std()
  for sigma in am['matched_height_RMS_m']:inp.append(p+sigma*ramp);meta.append({'sample':sample,'dataset':samples[sample]['dataset'],'kind':'planar_tilt','repeat':direction,'sigma_m':sigma})
 for repeat in range(5):
  u=unit[nidx,repeat].copy();u-=u.mean();u/=u.std();noise_units.append(u)
  for sigma in am['matched_height_RMS_m']:inp.append(p+sigma*u);meta.append({'sample':sample,'dataset':samples[sample]['dataset'],'kind':'iid_exact_rms','repeat':repeat,'sigma_m':sigma})
  perm=np.random.default_rng(52001+1000*sample+repeat).permutation(2601);rr=res[sample,1].ravel()[perm].reshape(51,51);inp.append(p+rr);meta.append({'sample':sample,'dataset':samples[sample]['dataset'],'kind':'shuffled_measured_residual','repeat':repeat,'sigma_m':float(res[sample,1].std())})
a=np.array(inp,np.float32);pred=[]
with torch.inference_mode():
 for i in range(0,len(a),64):pred.append(torch.softmax(m(torch.from_numpy(a[i:i+64,None]).cuda()),dim=2)[:,:,1,0,0].cpu().numpy())
np.savez_compressed(O/'MATCHED_CONTROL_OUTPUTS.npz',predictions=np.concatenate(pred),exact_rms_noise_units=np.array(noise_units));(O/'MATCHED_CONTROL_SAMPLES.json').write_text(json.dumps(meta,indent=2)+'\n');print('matched control forwards',len(meta),'amendment SHA',hashlib.sha256((O/'PROTOCOL_AMENDMENT_01.json').read_bytes()).hexdigest(),flush=True)
