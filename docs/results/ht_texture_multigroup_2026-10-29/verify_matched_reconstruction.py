from pathlib import Path
import json,numpy as np,torch,sys,hashlib
O=Path(__file__).parent;R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
from model import load_student_model
meta=json.loads((O/'MATCHED_CONTROL_SAMPLES.json').read_text());x=np.load(O/'MATCHED_CONTROL_OUTPUTS.npz');core=np.load(O/'OUTPUTS.npz');noise=np.load(O/'NOISE_OUTPUTS.npz');ids=noise['sample_ids'].tolist();lookup={s:i for i,s in enumerate(ids)};ii,jj=np.indices((51,51));xx=(ii-25)*.04;yy=(jj-25)*.04;arrays=[];hashes=[];max_rms_error=0.
planes=core['plane'];residuals=core['residual'];noise_units=x['exact_rms_noise_units']
for row in meta:
 s=row['sample'];p=planes[s,1]
 if row['kind']=='planar_tilt':
  a=np.deg2rad(row['repeat']);u=(np.cos(a)*xx+np.sin(a)*yy).astype(np.float32);u-=u.mean();u/=u.std();arr=p+row['sigma_m']*u;max_rms_error=max(max_rms_error,abs(float((arr-p).std())-row['sigma_m']))
 elif row['kind']=='iid_exact_rms':
  u=noise_units[lookup[s]*5+row['repeat']];arr=p+row['sigma_m']*u;max_rms_error=max(max_rms_error,abs(float((arr-p).std())-row['sigma_m']))
 else:
  u=residuals[s,1];perm=np.random.default_rng(52001+1000*s+row['repeat']).permutation(2601);arr=p+u.ravel()[perm].reshape(51,51)
 arrays.append(arr);hashes.append(hashlib.sha256(arr.tobytes()).hexdigest())
subset=np.sort(np.random.default_rng(832).choice(len(arrays),64,replace=False));m=load_student_model(str(R/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'),torch.device('cuda'));torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
with torch.inference_mode():p=torch.softmax(m(torch.from_numpy(np.array(arrays,np.float32)[subset,None]).cuda()),dim=2)[:,:,1,0,0].cpu().numpy()
err=float(np.max(abs(p-x['predictions'][subset])));assert err<1e-4 and max_rms_error<1e-6,(err,max_rms_error);(O/'MATCHED_INPUT_HASHES.json').write_text(json.dumps(hashes)+'\n');(O/'MATCHED_RECONSTRUCTION_CHECK.json').write_text(json.dumps({'all_input_hashes_saved':len(hashes),'recomputed_subset':64,'max_probability_error':err,'max_added_height_rms_error_m':max_rms_error},indent=2)+'\n');print(err,max_rms_error)
