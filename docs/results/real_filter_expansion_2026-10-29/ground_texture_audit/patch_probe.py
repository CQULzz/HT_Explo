from pathlib import Path
import sys,json,numpy as np,torch
from scipy.ndimage import gaussian_filter
R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');O=Path('/media/lzz/My Passport/HT_exact_red_case_2026-10-29');sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
from model import load_student_model
model=load_student_model(str(R/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'),torch.device('cuda'));torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
cs=sorted((B/'red_region_audit/contexts').glob('*.npz'));t=json.loads((O/'FLAT_RED_TARGETS.json').read_text())[0];i,j=np.indices((51,51));A=np.c_[i.ravel()*.04,j.ravel()*.04,np.ones(2601)];patches=[];planes=[]
for index,ij in [(t['before'],t['old_index']),(t['after'],t['new_index'])]:
 q=np.load(cs[index]);x,y=ij;h=q['height'][x:x+51,y:y+51].copy();plane=(A@np.linalg.lstsq(A,h.ravel(),rcond=None)[0]).reshape(51,51).astype(np.float32);patches.append(h);planes.append(plane)
old,new=patches;p0,p1=planes;oldres=old-p0;newres=new-p1
variants={'actual_before':old,'actual_after':new,'diagnostic_new_plane_only':p1,'diagnostic_new_plane_old_texture':p1+oldres,'diagnostic_old_plane_new_texture':p0+newres,'diagnostic_half_new_texture':p1+.5*newres,'diagnostic_gauss_sigma_0p5_cell':p1+gaussian_filter(newres,.5),'diagnostic_gauss_sigma_1_cell':p1+gaussian_filter(newres,1.)}
results={}
for name,h in variants.items():
 with torch.inference_mode():T=torch.softmax(model(torch.from_numpy(h[None,None]).cuda()),dim=2)[0,:,1,0,0].cpu().numpy()
 results[name]=T.tolist()
 if name=='actual_before':assert abs(T[0]-t['T0_before'])<1e-5
 if name=='actual_after':assert abs(T[0]-t['T0_after'])<1e-5
np.savez_compressed(O/'ground_patch_probe_fields.npz',**variants,old_residual=oldres,new_residual=newres)
(O/'PATCH_PROBE.json').write_text(json.dumps({'target':t,'scope':'Exact51patch forward original values reproduce full-map T within1e-5; counterfactual plane/texture changes for causal attribution only, not production filtering','results':results},indent=2)+'\n');print(json.dumps(results,indent=2),flush=True)
