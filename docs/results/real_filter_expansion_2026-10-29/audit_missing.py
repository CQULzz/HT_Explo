from pathlib import Path
import sys,json,numpy as np,torch
from scipy import ndimage
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt,font_manager
R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');O=Path('/media/lzz/My Passport/HT_filter_expansion_2026-10-29');sys.path.insert(0,str(R/'tools/ht_cupy_bridge'))
from model import load_student_model
# CPU diagnostic leaves the separately frozen GPU reconstruction trials uncontended.
torch.set_num_threads(4);model=load_student_model(str(R/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'),torch.device('cpu'))
r=json.loads((B/'rebuild_170043/RESULTS.json').read_text());contexts=sorted((B/'red_region_audit/contexts').glob('*.npz'));records=[]
for a,b in [(12,13),(23,26),(50,51),(51,52),(52,53)]:
 old=np.load(contexts[a]);new=np.load(contexts[b]);before=np.load(B/'rebuild_170043/frames'/r['frames'][a]['file']);after=np.load(B/'rebuild_170043/frames'/r['frames'][b]['file']);shift=np.rint((new['geometry'][:2]-old['geometry'][:2])/.04).astype(int)
 i,j=np.indices((291,291));oi=i-shift[0];oj=j-shift[1];inside=(oi>=0)&(oi<291)&(oj>=0)&(oj<291);oi=oi.clip(0,290);oj=oj.clip(0,290);prev=old['height'][oi,oj];h=new['height'];pad=~new['observed']&~new['inferred_ground']&~np.isfinite(new['obstacle_context']);hole=new['inferred_ground'];measured=new['observed'];occ=np.isfinite(new['obstacle_context'])
 ii,jj=np.indices((241,241));pi=ii-shift[0];pj=jj-shift[1];common=(pi>=0)&(pi<241)&(pj>=0)&(pj<241);pi=pi.clip(0,240);pj=pj.clip(0,240);oldT=np.stack([before[f'ht_dir_{k}'][pi,pj] for k in range(8)]);newT=np.stack([after[f'ht_dir_{k}'] for k in range(8)]);common&=(after['ht_valid']>.5)&(before['ht_valid'][pi,pj]>.5);flip=(oldT>.8)&(newT<.2)&common;threshold_flip=(oldT>=.5)&(newT<.5)&common
 s=r['diagnostics'][b]['surface'];plane=s['reference_center_m']+s['slope_xy'][0]*(145-i)*.04+s['slope_xy'][1]*(145-j)*.04
 variants={'original':h,'restore_only_nearest_padding':np.where(pad&inside,prev,h).astype(np.float32),'restore_only_small_hole_repair':np.where(hole&inside,prev,h).astype(np.float32),'restore_only_observed_heights':np.where(measured&inside,prev,h).astype(np.float32),'diagnostic_flatten_measured_under5cm':np.where(measured&(abs(h-plane)<.05),plane,h).astype(np.float32),'diagnostic_flatten_measured_under15cm':np.where(measured&(abs(h-plane)<.15),plane,h).astype(np.float32)}
 record={'before_frame':a,'after_frame':b,'source_times_s':[r['frames'][a]['t_s'],r['frames'][b]['t_s']],'observed_cells_before_after':[int(old['observed'].sum()),int(measured.sum())],'native_finite_before_after':[int(np.isfinite(old['source_elevation']).sum()),int(np.isfinite(new['source_elevation']).sum())],'nn_padding_cells_before_after':[int((~old['observed']&~old['inferred_ground']&~np.isfinite(old['obstacle_context'])).sum()),int(pad.sum())],'common_world_cells':int(common.sum()),'confident_green_to_red_direction_cells':int(flip.sum()),'half_threshold_green_to_red_direction_cells':int(threshold_flip.sum()),'changed_height_over5cm_by_new_input_type':{k:int((inside&(abs(h-prev)>.05)&v).sum()) for k,v in [('observed',measured),('nearest_padding',pad),('hole_repair',hole),('occupied_context',occ)]},'variants':{}}
 fields={}
 for name,height in variants.items():
  with torch.inference_mode():T=torch.softmax(model(torch.from_numpy(np.ascontiguousarray(height[None,None]))),dim=2)[0,:,1].numpy()
  T[:,new['occupied']]=0
  if name=='original':assert np.max(abs(T-new['probabilities']))<1e-4,float(np.max(abs(T-new['probabilities'])))
  record['variants'][name]={'red_fraction_among_after_valid':float(np.mean(T[:,after['ht_valid']>.5]<.5)),'previous_flips_recovered_over_half':int((flip&(T>=.5)).sum()),'half_threshold_flips_recovered':int((threshold_flip&(T>=.5)).sum()),'previous_flips_recovered_over_point8':int((flip&(T>.8)).sum())};fields[name]=T
 records.append(record)
 if (a,b)==(51,52):np.savez_compressed(O/'sudden_red_fields.npz',old_height=np.where(inside,prev,np.nan),new_height=h,measured=measured,padding=pad,hole=hole,occupied=occ,common=common,valid=after['ht_valid']>.5,flips=flip,oldT=oldT,**fields)
 print(record,flush=True)
(O/'MISSING_DATA_AUDIT.json').write_text(json.dumps({'scope':'Counterfactual NN inputs for mechanism attribution only; no field changes deployed; CPU diagnostic original agrees with GPU within1e-4','pairs':records},indent=2)+'\n')
font_manager.fontManager.addfont('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc');plt.rcParams['font.family']=font_manager.FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc').get_name();plt.rcParams['axes.unicode_minus']=False
q=np.load(O/'sudden_red_fields.npz');fig,ax=plt.subplots(2,3,figsize=(16,10),layout='constrained')
for a,h,title in [(ax[0,0],q['old_height'],'28.70秒：对齐到同一世界格的前帧输入'),(ax[0,1],q['new_height'],'29.20秒：当前网络输入')]:
 m=a.imshow(h.T,origin='lower',cmap='terrain',vmin=-.9,vmax=.8);a.set_title(title);fig.colorbar(m,ax=a,shrink=.7)
m=ax[0,2].imshow((q['new_height']-q['old_height']).T,origin='lower',cmap='coolwarm',vmin=-.15,vmax=.15);ax[0,2].set_title('同世界位置输入高度变化 / m');fig.colorbar(m,ax=ax[0,2],shrink=.7)
for a,key,title in [(ax[1,0],'original','实际：8方向低于0.5的比例'),(ax[1,1],'restore_only_nearest_padding','仅诊断：只还原缺测最近邻填值'),(ax[1,2],'diagnostic_flatten_measured_under5cm','仅诊断：只消除观测地面±5cm纹理')]:
 m=a.imshow(np.ma.masked_where(~q['valid'],np.mean(q[key]<.5,axis=0)).T,origin='lower',cmap='RdYlGn_r',vmin=0,vmax=1);a.set_title(title);fig.colorbar(m,ax=a,shrink=.7)
fig.suptitle('突然变红是否由缺测引起？固定世界坐标对齐、分别干预不同输入来源\n所有改值仅用于归因，没有写回建图或规划器',fontsize=16);fig.savefig(O/'sudden_red_missing_audit.png',dpi=160)
