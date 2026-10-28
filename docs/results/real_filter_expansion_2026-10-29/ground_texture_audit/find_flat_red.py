from pathlib import Path
import json,numpy as np
from scipy.ndimage import maximum_filter,minimum_filter
B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');O=Path('/media/lzz/My Passport/HT_exact_red_case_2026-10-29');r=json.loads((B/'rebuild_170043/RESULTS.json').read_text());cs=sorted((B/'red_region_audit/contexts').glob('*.npz'));out=[]
for a,b in [(47,52),(50,51),(51,52),(52,53),(47,53)]:
 old=np.load(cs[a]);new=np.load(cs[b]);za=np.load(B/'rebuild_170043/frames'/r['frames'][a]['file']);zb=np.load(B/'rebuild_170043/frames'/r['frames'][b]['file']);i,j=np.indices((241,241));shift=np.rint((zb['center']-za['center'])/.04).astype(int);pi=i-shift[0];pj=j-shift[1];inside=(pi>=0)&(pi<241)&(pj>=0)&(pj<241);pi=pi.clip(0,240);pj=pj.clip(0,240);h=new['height'];known=new['observed']|np.isfinite(new['obstacle_context']);span=(maximum_filter(h,51)-minimum_filter(h,51))[25:-25,25:-25];obs_span=(maximum_filter(np.where(known,h,-np.inf),51)-minimum_filter(np.where(known,h,np.inf),51))[25:-25,25:-25];T0=za['ht_dir_0'][pi,pj];T1=zb['ht_dir_0'];sel=inside&(za['ht_valid'][pi,pj]>.5)&(zb['ht_valid']>.5)&(T0>.8)&(T1<.2)&(span<.15)
 candidates=np.argwhere(sel)
 if len(candidates):
  score=(T0-T1)[sel];rank=np.argsort(score)[::-1]
  for index in rank[:5]:
   ii,jj=candidates[index];oi,oj=pi[ii,jj],pj[ii,jj];patch=h[ii:ii+51,jj:jj+51];pp=old['height'][oi:oi+51,oj:oj+51];world=zb['center']+np.array([120-ii,120-jj])*.04
   out.append({'before':a,'after':b,'times':[r['frames'][a]['t_s'],r['frames'][b]['t_s']],'new_index':[int(ii),int(jj)],'old_index':[int(oi),int(oj)],'world_xy':world.tolist(),'T0_before':float(T0[ii,jj]),'T0_after':float(T1[ii,jj]),'patch_span_m':float(np.ptp(patch)),'observed_patch_span_m':float(obs_span[ii,jj]),'patch_height_change_max_m':float(abs(patch-pp).max()),'new_observed_count':int(new['observed'][ii:ii+51,jj:jj+51].sum()),'new_nearest_padding_count':int((~new['observed']&~new['inferred_ground']&~np.isfinite(new['obstacle_context']))[ii:ii+51,jj:jj+51].sum()),'new_occupied_count':int(new['occupied'][max(0,ii-25):min(241,ii+26),max(0,jj-25):min(241,jj+26)].sum())})
print(json.dumps(out,indent=2));(O/'FLAT_RED_TARGETS.json').write_text(json.dumps(out,indent=2)+'\n')
