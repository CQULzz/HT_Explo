from pathlib import Path
import numpy as np,json,warnings
from scipy import ndimage
warnings.filterwarnings('ignore',message='All-NaN')
B=Path('/media/lzz/My Passport/HT_newbags_replay_20261028');O=B/'red_region_audit';results=json.loads((B/'rebuild_170043/RESULTS.json').read_text());contexts=sorted((O/'contexts').glob('*.npz'));assert len(contexts)==64
stats=[];data=[]
for f,c in zip(results['frames'],contexts):
 z=np.load(B/'rebuild_170043/frames'/f['file']);q=np.load(c);r=float(z['resolution']);ii,jj=np.indices((241,241));x=z['center'][0]+(120-ii)*r;y=z['center'][1]+(120-jj)*r;rob=z['robot'];dx=x-rob[0];dy=y-rob[1];bx=np.cos(rob[3])*dx+np.sin(rob[3])*dy;by=-np.sin(rob[3])*dx+np.cos(rob[3])*dy;T=np.stack([z[f'ht_dir_{k}'] for k in range(8)]);valid=z['ht_valid']>.5;low=valid&(np.max(T,axis=0)<.5);region=dx*dx+dy*dy<1.5**2;components,n=ndimage.label(low);candidate=[]
 for label in range(1,n+1):
  m=components==label
  if m.sum()>=20 and np.any(m&region):
   candidate.append((int(m.sum()),m))
 candidate.sort(key=lambda t:t[0]);m=candidate[0][1] if candidate else np.zeros(low.shape,bool)
 # 291-map coordinates, fitted reference plane matches the production reference estimator.
 i,j=np.indices((291,291));s=results['diagnostics'][len(stats)]['surface'];plane=s['reference_center_m']+s['slope_xy'][0]*(145-i)*r+s['slope_xy'][1]*(145-j)*r
 input_residual=q['height']-plane
 wx=q['geometry'][0]+(145-i)*r;wy=q['geometry'][1]+(145-j)*r
 close=(wx-rob[0])**2+(wy-rob[1])**2<1.5**2
 bump=(input_residual>.06)&(input_residual<.3)&close
 observed=q['observed'];inferred=q['inferred_ground'];other=~observed&~inferred&~np.isfinite(q['obstacle_context'])
 sample={'frame':len(stats),'t_s':f['t_s'],'robot':rob.tolist(),'body_red_cells':int((low&region).sum()),'component_cells':int(m.sum()),'component_body_centroid':[float(bx[m].mean()),float(by[m].mean())] if m.any() else None,'component_world_centroid':[float(x[m].mean()),float(y[m].mean())] if m.any() else None,'body_bump_input_cells':int(bump.sum()),'bump_observed':int((bump&observed).sum()),'bump_interpolated':int((bump&inferred).sum()),'bump_nearest_padding':int((bump&other).sum()),'near_occupied_cells':int((region&(z['ht_obstacle']>.5)).sum())}
 stats.append(sample);data.append(dict(z=z,q=q,x=x,y=y,low=low,plane=plane,input_residual=input_residual,close=close,component=m))
(O/'BODY_STATS.json').write_text(json.dumps(stats,indent=2)+'\n')
# Match the same fixed world XY at a fixed channel, not the robot-following display pixel.
flips=[]
for ia in range(2,52):
 a=data[ia];za=a['z'];gx=np.rint(a['x']/.04).astype(np.int64);gy=np.rint(a['y']/.04).astype(np.int64)
 for ib in range(ia+3,min(ia+16,64)):
  b=data[ib];zb=b['z'];ix=np.rint(120-(a['x']-zb['center'][0])/.04).astype(int);iy=np.rint(120-(a['y']-zb['center'][1])/.04).astype(int);inside=(ix>=0)&(ix<241)&(iy>=0)&(iy<241);ix=ix.clip(0,240);iy=iy.clip(0,240)
  # Robust, all-eight-red to channel-zero confidently green; both actual valid outputs.
  pa=za['ht_dir_0'];pb=zb['ht_dir_0'][ix,iy];oldall=np.max(np.stack([za[f'ht_dir_{k}'] for k in range(8)]),axis=0)<.3
  dista=np.hypot(a['x']-za['robot'][0],a['y']-za['robot'][1]);distb=np.hypot(a['x']-zb['robot'][0],a['y']-zb['robot'][1]);h0=za['ht_elevation'];h1=zb['ht_elevation'][ix,iy]
  use=inside&oldall&(pb>.95)&(za['ht_valid']>.5)&(zb['ht_valid'][ix,iy]>.5)&(dista<1.5)&(dista>.4)&(distb>1.7)&np.isfinite(h0)&np.isfinite(h1)&(abs(h0-h1)<.03)
  if not use.any():continue
  vals=np.where(use,pb-pa,-np.inf);i,j=np.unravel_index(np.argmax(vals),vals.shape);k,l=ix[i,j],iy[i,j]
  # Input context patches corresponding exactly to that world target.
  qa=a['q']['height'][i:i+51,j:j+51];qb=b['q']['height'][k:k+51,l:l+51]
  flips.append(dict(before=ia,after=ib,t_before=stats[ia]['t_s'],t_after=stats[ib]['t_s'],world_xy=[float(a['x'][i,j]),float(a['y'][i,j])],old_index=[int(i),int(j)],new_index=[int(k),int(l)],T0_before=float(pa[i,j]),T0_after=float(pb[i,j]),all8_before=[float(za[f'ht_dir_{k}'][i,j]) for k in range(8)],height_before=float(h0[i,j]),height_after=float(h1[i,j]),distance_before=float(dista[i,j]),distance_after=float(distb[i,j]),context_height_max_abs_change_m=float(abs(qa-qb).max()),context_changed_cells=int((abs(qa-qb)>.02).sum())))
flips.sort(key=lambda f:f['T0_after']-f['T0_before'],reverse=True)
(O/'WORLD_FLIPS.json').write_text(json.dumps(flips[:100],indent=2)+'\n');print('world flips',len(flips));print(flips[:2]);print('frame17',stats[17])
