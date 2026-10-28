from pathlib import Path
import json,sys,numpy as np,torch
from scipy import ndimage
R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');O=B/'red_region_audit';sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
from model import load_student_model
model=load_student_model(str(R/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'),torch.device('cuda'));torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
r=json.loads((B/'rebuild_170043/RESULTS.json').read_text());contexts=sorted((O/'contexts').glob('*.npz'));out=[]
for index in [10,11,15,17,19,23,27,31,35,39,43,47]:
 f=r['frames'][index];z=np.load(B/'rebuild_170043/frames'/f['file']);q=np.load(contexts[index]);i,j=np.indices((291,291));plane=r['diagnostics'][index]['surface'];p=plane['reference_center_m']+plane['slope_xy'][0]*(145-i)*.04+plane['slope_xy'][1]*(145-j)*.04;h=q['height'];rob=z['robot'];wx=q['geometry'][0]+(145-i)*.04;wy=q['geometry'][1]+(145-j)*.04;dx=wx-rob[0];dy=wy-rob[1];bx=np.cos(rob[3])*dx+np.sin(rob[3])*dy;by=-np.sin(rob[3])*dx+np.cos(rob[3])*dy;close=dx*dx+dy*dy<1.5**2
 bump=close&(h-p>.06)&(h-p<.25)&q['observed'];padding=~q['observed']&~q['inferred_ground']&~np.isfinite(q['obstacle_context']);noise=(abs(h-p)<.03)&close
 inputs={'original':h.copy(),'diagnostic_replace_only_6to25cm_measured_bumps':np.where(bump,p,h).astype(np.float32),'diagnostic_replace_only_unmeasured_padding':np.where(padding,p,h).astype(np.float32),'diagnostic_flatten_only_under3cm_near_ground':np.where(noise,p,h).astype(np.float32)}
 valid=z['ht_valid']>.5;near=close[25:-25,25:-25];saved=np.stack([z[f'ht_dir_{k}'] for k in range(8)]);red=near&valid&(np.max(saved,axis=0)<.5);mask_out=bump[25:-25,25:-25];record={'frame':index,'t_s':f['t_s'],'bump_cells':int(bump.sum()),'bump_body_centroid':[float(bx[bump].mean()),float(by[bump].mean())] if bump.any() else None,'bump_body_range':np.quantile(np.stack([bx[bump],by[bump]],axis=1),[0,.5,1],axis=0).tolist() if bump.any() else None,'bump_height_above_reference_m':np.quantile((h-p)[bump],[0,.5,1]).tolist() if bump.any() else None,'low_all8_near_before':int(red.sum()),'probes':{}}
 predictions={}
 for name,height in inputs.items():
  with torch.inference_mode():probs=torch.softmax(model(torch.from_numpy(height[None,None]).cuda()),dim=2)[0,:,1].cpu().numpy()
  probs[:,q['occupied']]=0;predictions[name]=probs
  if name=='original':assert np.array_equal(probs,q['probabilities']),float(np.max(abs(probs-q['probabilities'])))
  maximum=np.max(probs,axis=0);record['probes'][name]={'still_low_all8_near':int((near&valid&(maximum<.5)).sum()),'previous_red_now_any_pass':int((red&(maximum>=.5)).sum()),'previous_red_now_all8_pass':int((red&(np.min(probs,axis=0)>=.5)).sum()),'median_maxT_in_previous_red':float(np.median(maximum[red])) if red.any() else None,'T0_at_before_red_median':float(np.median(probs[0][red])) if red.any() else None}
 out.append(record)
 if index==17:np.savez_compressed(O/'frame17_probe_fields.npz',height=h,plane=p,bump=bump,bx=bx,by=by,observed=q['observed'],inferred=q['inferred_ground'],padding=padding,red=red,**predictions)
 print(record,flush=True)
(O/'PROBES.json').write_text(json.dumps({'scope':'Offline diagnostic counterfactual NN inputs only, unsafe to deploy as terrain; no map, validity, threshold, planner or vehicle changes','records':out},indent=2)+'\n')
