from pathlib import Path
import json,sys,numpy as np,torch
from scipy.ndimage import distance_transform_edt
R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');O=Path('/media/lzz/My Passport/HT_exact_red_case_2026-10-29');sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
from model import load_student_model
m=load_student_model(str(R/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'),torch.device('cuda'));torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
c=sorted((B/'red_region_audit/contexts').glob('*.npz'));t=json.loads((O/'FLAT_RED_TARGETS.json').read_text())[0];result=[];fields={}
for frame,ind in [(47,t['old_index']),(52,t['new_index'])]:
 q=np.load(c[frame]);i,j=ind
 for name,h in [('native_cupy',q['source_elevation']),('raw_history',q['raw_history']),('final_ht_input',q['height'])]:
  patch=h[i:i+51,j:j+51].copy();finite=np.isfinite(patch);assert finite.any();_,near=distance_transform_edt(~finite,return_indices=True);filled=patch[tuple(near)].copy()
  with torch.inference_mode():p=torch.softmax(m(torch.from_numpy(filled[None,None]).cuda()),dim=2)[0,:,1,0,0].cpu().numpy()
  ii,jj=np.indices((51,51));A=np.c_[ii.ravel()*.04,jj.ravel()*.04,np.ones(2601)];res=filled-(A@np.linalg.lstsq(A,filled.ravel(),rcond=None)[0]).reshape(51,51);gr=np.r_[np.diff(filled,axis=0).ravel(),np.diff(filled,axis=1).ravel()]
  row={'frame':frame,'stage':name,'actual_finite_cells':int(finite.sum()),'diagnostic_local_nearest_filled':int((~finite).sum()),'T0':float(p[0]),'all8':p.tolist(),'detrended_rms_cm':float(np.std(res)*100),'adjacent_abs_p99_cm':float(np.quantile(abs(gr),.99)*100)};result.append(row);fields[f'{frame}_{name}']=filled;print(row,flush=True)
np.savez_compressed(O/'stage_probe_fields.npz',**fields);(O/'STAGE_PROBE.json').write_text(json.dumps({'scope':'Diagnostic patch-only inference, not deployed. Native/history patches fill only their own missing cells for this probe; final51patch reproduces original T. Native and history geometry centers must coincide to cell precision.','records':result},indent=2)+'\n')
