"""Inspect published clouds around the prior early return; observational only."""
import argparse,csv,json
from pathlib import Path
import cv2,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);a=p.parse_args()
    rows=list(csv.DictReader((a.folder/'candidates.csv').open()))
    ids=[min(range(len(rows)),key=lambda i:abs(float(rows[i]['t_s'])-t)) for t in (12.85,13.82,14.51)]
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,axes=plt.subplots(2,3,figsize=(15,9),layout='constrained')
    result={'scope':'Bag time latest-prior HT/collision cloud, not exact internal snapshot. Published candidates exclude rejected nodes; no frontier gains or cell membership recorded. This audit does not identify the single internal rejection branch.'}
    with np.load(a.folder/'candidate_frames.npz') as data:
        for col,i in enumerate(ids):
            key=f'frame_{i+1:04d}';r=rows[i];pts=data[key];collision=data[key+'_collision_viewpoints']
            cx,cy,res=data[key+'_ht_geometry'];valid=data[key+'_ht_valid']>=.5;obstacle=data[key+'_ht_obstacle']>=.5
            prob=np.stack([data[key+f'_ht_dir_{k}'] for k in range(8)])
            n,m=valid.shape;extent=(cx-n*res/2,cx+n*res/2,cy-m*res/2,cy+m*res/2)
            cmap=plt.get_cmap('RdYlGn').copy();cmap.set_bad('#d9dde0')
            ax=axes[0,col]
            ax.imshow(np.where(valid,np.max(prob,axis=0),np.nan)[::-1,::-1].T,origin='lower',extent=extent,vmin=0,vmax=1,cmap=cmap,interpolation='nearest')
            ax.scatter(collision[:,0],collision[:,1],s=4,c='#45474b',alpha=.5,label='碰撞视点')
            unvisited=pts[:,3]>=0
            ax.scatter(pts[~unvisited,0],pts[~unvisited,1],s=5,c='#8c99aa',label='已访问候选')
            ax.scatter(pts[unvisited,0],pts[unvisited,1],s=6,c='#25a9ee',label='未访问候选')
            ax.scatter(float(r['x']),float(r['y']),s=65,marker='*',c='black',label='车辆')
            ax.set(xlim=(-3,23),ylim=(-7,17),title=f't={float(r["t_s"]):.3f}s：候选{r["candidates"]} / 未访{r["unvisited"]}')
            ax.legend(fontsize=7);ax.set_aspect('equal')
            ax=axes[1,col]
            cloud=data[key+'_collision'];near=cloud[np.abs(cloud[:,2]-float(r['z']))<=.6]
            ax.scatter(near[:,0],near[:,1],s=3,c='#808080',alpha=.4,label='车高附近碰撞点云')
            ax.scatter(pts[:,0],pts[:,1],c=np.where(unvisited,np.floor(pts[:,3]),np.nan),s=12,cmap='viridis',vmin=0,vmax=100)
            ax.scatter(float(r['x']),float(r['y']),s=65,marker='*',c='red')
            ax.set(xlim=(-2,9),ylim=(-2,8),title='起点附近：候选颜色为原始表面收益（封顶100）')
            ax.set_aspect('equal');ax.grid(alpha=.2)
        prev=data[f'frame_{ids[0]+1:04d}'];cur=data[f'frame_{ids[1]+1:04d}']
        collisions=data[f'frame_{ids[1]+1:04d}_collision_viewpoints']
        xy=lambda arr:{tuple(np.round(v,4)) for v in arr[:,:2]}
        removed=xy(prev)-xy(cur);collision_xy=xy(collisions)
        result.update(previous_t_s=float(rows[ids[0]]['t_s']),decision_t_s=float(rows[ids[1]]['t_s']),
            recovery_t_s=float(rows[ids[2]]['t_s']),previous_candidates=len(prev),decision_candidates=len(cur),
            recovery_candidates=int(rows[ids[2]]['candidates']),removed_previous_xy=len(removed),
            removed_marked_in_collision_current=len(removed&collision_xy),
            removed_not_marked_in_collision_current=len(removed-collision_xy))
    for ax in axes.flat:ax.set(xlabel='X / m',ylabel='Y / m')
    fig.suptitle('上次失败记录：短暂候选收缩后即锁定返航，下一帧几何候选回升\n底图为最近先到HT八方向最大分数；视点云不含被拒原因，不能据此唯一归因HT')
    fig.savefig(a.folder/'transition.png',dpi=160);fig.savefig(a.folder/'transition.pdf');plt.close(fig)
    (a.folder/'transition_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
