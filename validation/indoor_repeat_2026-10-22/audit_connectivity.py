"""Limited graph counterfactual, with explicit alignment and omitted-state limits."""
import csv,json,argparse,hashlib
from pathlib import Path
from collections import deque
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    p=argparse.ArgumentParser();p.add_argument('folder',type=Path);p.add_argument('--latest-at-publication',action='store_true');a=p.parse_args()
    rows=list(csv.DictReader((a.folder/'candidates.csv').open()))
    ids=[min(range(len(rows)),key=lambda i:abs(float(rows[i]['t_s'])-t)) for t in [12.85,13.82,14.51]]
    lattice=lambda v:tuple(np.rint((v[:2]-.15)/.3).astype(int))
    xy=lambda values:{lattice(v) for v in values}
    result={'scope':'Counterfactual 8-neighbor graph on union of three published candidate sets, using latest bag HT before viewpoint-phase end estimated from representation phase durations. Not an exact internal snapshot. Recorded collision vertices preserved; height constraints, rejected vertices, LOS, full planner and route feasibility not reproduced. Agreement supports a mechanism, not unique source-level causality.',
            'input_sha256':{n:hashlib.sha256((a.folder/n).read_bytes()).hexdigest() for n in ['candidates.csv','candidate_frames.npz']},'frames':[]}
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    fig,axes=plt.subplots(1,3,figsize=(15,5),layout='constrained')
    with np.load(a.folder/'candidate_frames.npz') as d:
        points={lattice(v):v for i in ids for v in d[f'frame_{i+1:04d}']}
        for ax,i in zip(axes,ids):
            k=f'frame_{i+1:04d}';prefix=k+('_' if a.latest_at_publication else '_gate_')
            h={tuple(v[:2]):bool(v[2]) for v in d[prefix+'computed_terrain_history']}
            body=d[prefix+'computed_body_blocked'];cx,cy,res=d[prefix+'ht_geometry'];n,m=body.shape
            collisions=xy(d[k+'_collision_viewpoints']);actual=xy(d[k])
            def physical_blocked(v):
                x,y=v[:2];ii=int(np.floor(n*.5-(x-cx)/res));jj=int(np.floor(m*.5-(y-cy)/res))
                return bool(0<=ii<n and 0<=jj<m and body[ii,jj])
            def allowed(v):
                x,y=v[:2]
                return not physical_blocked(v) and h.get((int(np.floor(x/.2)),int(np.floor(y/.2))),True)
            robot=np.array([float(rows[i]['x']),float(rows[i]['y'])]);seed=min(points,key=lambda v:np.linalg.norm(points[v][:2]-robot))
            sets={}
            for label in ['with_HT','without_HT_vertex_filter','only_latest_physical_body']:
                queue=deque([seed]);seen={seed}
                while queue:
                    x,y=queue.popleft()
                    for dx in [-1,0,1]:
                        for dy in [-1,0,1]:
                            q=(x+dx,y+dy)
                            if q in seen or q not in points or q in collisions:continue
                            if label=='with_HT' and not allowed(points[q]):continue
                            if label=='only_latest_physical_body' and physical_blocked(points[q]):continue
                            seen.add(q);queue.append(q)
                sets[label]=seen
            graph=sets['with_HT']
            boundary=set()
            for x,y in graph:
                for dx in [-1,0,1]:
                    for dy in [-1,0,1]:
                        q=(x+dx,y+dy)
                        if q in points and q not in collisions and not allowed(points[q]):boundary.add(q)
            def boundary_data(v):
                x,y=points[v][:2];ii=int(np.floor(n*.5-(x-cx)/res));jj=int(np.floor(m*.5-(y-cy)/res));inside=0<=ii<n and 0<=jj<m
                return dict(xy=[float(x),float(y)],latest_physical_body_blocked=physical_blocked(points[v]),
                    current_grid_valid=float(d[prefix+'ht_valid'][ii,jj]) if inside else None,
                    current_grid_max_8dir_score=max(float(d[prefix+f'ht_dir_{z}'][ii,jj]) for z in range(8)) if inside else None)
            result['frames'].append(dict(time_s=float(rows[i]['t_s']),estimated_viewpoint_end_t_s=float(rows[i]['estimated_viewpoint_end_t_s']),
                ht_bag_time_s=float(rows[i]['gate_ht_bag_t_s']),latest_at_publication_ht_bag_time_s=float(rows[i]['latest_ht_bag_t_s']),
                union_vertices=len(points),actual_candidates=len(actual),replayed_counts={k:len(v) for k,v in sets.items()},
                self_candidates_allowed=sum(allowed(points[v]) for v in actual),
                true_positive=len(graph&actual),false_positive=len(graph-actual),false_negative=len(actual-graph),
                boundary_rejected_vertices=[boundary_data(v) for v in sorted(boundary)]))
            all_points=np.array(list(points.values()));ax.scatter(all_points[:,0],all_points[:,1],s=6,c='#d5d5d5',label='三帧候选并集')
            rejected=np.array([points[v] for v in points if not allowed(points[v])])
            if len(rejected):ax.scatter(rejected[:,0],rejected[:,1],s=14,c='#d43b34',label='重放HT门槛拒绝')
            reached=np.array([points[v] for v in graph]);ax.scatter(reached[:,0],reached[:,1],s=7,c='#1895b7',label='简化连通分量')
            ax.scatter(*robot,c='black',s=65,marker='*');ax.set(title=f't={float(rows[i]["t_s"]):.3f}s：实测{len(actual)} / 简化重放{len(graph)}',xlabel='X / m',ylabel='Y / m',xlim=(-2,23),ylim=(-6,16));ax.set_aspect('equal');ax.legend(fontsize=7)
    suffix='_latest' if a.latest_at_publication else ''
    if a.latest_at_publication:result['scope']='UNALIGNED COUNTEREXAMPLE: latest bag HT at candidate publication, which may be newer than the internal viewpoint stage. Same simplified graph limitations; mismatch must not be presented as reproducing the online failure.'
    result['map_selection']='latest_at_publication' if a.latest_at_publication else 'estimated_viewpoint_phase_end'
    fig.suptitle('HT门槛与走廊连通性的离线核对：'+('发布时最新图（未按视点阶段对齐，作为反例）' if a.latest_at_publication else '按视点处理阶段估算对齐')+'\n简化反事实省略高度/LOS等状态，不是完整规划器或可行路线重放')
    fig.savefig(a.folder/f'connectivity{suffix}.png',dpi=160);fig.savefig(a.folder/f'connectivity{suffix}.pdf');plt.close(fig)
    (a.folder/f'connectivity{suffix}_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
