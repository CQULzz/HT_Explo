"""Summarize and visualize fixed, recorded-input experiments; no ROS startup."""
from pathlib import Path
import argparse,json,sys,shutil
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/ht_cupy_bridge'))
import replay_real_archive as replay


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--ffmpeg',required=True)
    a=p.parse_args();root=a.data;out=ROOT/'docs/results/real_round2_2026-10-28';plt=replay.plot_setup()
    b=json.loads((root/'before/maps/index.json').read_text());c=json.loads((root/'after_v2/maps/index.json').read_text())
    first=json.loads((root/'after/maps/index.json').read_text());cloud=json.loads((root/'cloud_v2/index.json').read_text())
    oldcloud=json.loads((root/'cloud/index.json').read_text())
    masks_equal=True;flips=0;maxdiff=0.;per_frame=[]
    for before,after in zip(b['frames'],c['frames']):
        assert before['stamp_ns']==after['stamp_ns']
        with np.load(root/'before/maps'/before['file']) as x,np.load(root/'after_v2/maps'/after['file']) as y:
            for k in ['ht_valid','ht_observation_valid','ht_obstacle','ht_elevation']:
                masks_equal &= np.array_equal(x[k],y[k],equal_nan=True)
            valid=x['ht_valid']>=.5;delta=np.abs(x['probabilities'][:,valid]-y['probabilities'][:,valid])
            change=float(np.max(delta));count=int(np.count_nonzero((x['probabilities'][:,valid]>=.5)!=(y['probabilities'][:,valid]>=.5)))
            maxdiff=max(maxdiff,change);flips+=count;per_frame.append({'t_s':after['t_s'],'max_probability_difference':change,'threshold_0_5_flips':count})
    assert masks_equal and maxdiff<1e-5 and flips==0
    for previous,now in zip(oldcloud['frames'],cloud['frames']):
        assert previous['input_cdr_sha256']==now['input_cdr_sha256']
        with np.load(root/'cloud'/previous['file']) as x,np.load(root/'cloud_v2'/now['file']) as y:
            np.testing.assert_array_equal(x['after'],y['after'])
    def timing(meta):
        v=np.array([f['callback_s'] for f in meta['frames']])*1000
        return dict(mean_ms=float(v.mean()),median_ms=float(np.median(v)),p95_ms=float(np.percentile(v,95)),max_ms=float(v.max()))
    timed={name:json.loads((root/name/'timed.json').read_text()) for name in ['timed_before','timed_after','timed_after_v2']}
    f=cloud['frames'];total=sum(x['low_points'] for x in f);old=sum(x['old_low_kept'] for x in f);new=sum(x['new_low_kept'] for x in f)
    summary={'scope':'Saved-input offline comparison, no vehicle navigation or new CuPy mapping',
        'candidate_local_commit':c['source_commit'],'baseline_commit':b['source_commit'],
        'ht_maps_before':b['outputs'],'ht_maps_after':c['outputs'],'input_duration_s':c['duration_s'],
        'masks_and_elevation_exactly_equal':bool(masks_equal),'max_probability_difference':maxdiff,'threshold_0_5_flips':flips,
        'timing_before':timing(b),'timing_candidate_v1':timing(first),'timing_candidate_v2':timing(c),
        'timed_replay':{k:{q:v[q] for q in ['input_maps','outputs','pending_replaced','input_fault']} for k,v in timed.items()},
        'cloud_samples':len(f),'cloud_duration_s':f[-1]['t_s'],'low_return_points':total,'low_returns_before':old,'low_returns_after':new,
        'low_return_retention_before':old/total,'low_return_retention_after':new/total,
        'old_kept_inside_model':sum(x['old_kept_inside_model'] for x in f),
        'self_filter_ms':{'old_box_median':float(np.median([x['old_filter_ms'] for x in f])),
            'geometry_v1_median':float(np.median([x['new_filter_ms'] for x in oldcloud['frames']])),
            'geometry_v2_median':float(np.median([x['new_filter_ms'] for x in f]))},
        'geometry_v1_v2_masks_exactly_equal':True,'last_frame':c['frames'][-1],
        'per_frame_parity':per_frame,'no_vehicle_motion':True,'low_returns_are_not_ground_truth':True}
    (out/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
    fig,axs=plt.subplots(2,2,figsize=(14,9),layout='constrained')
    for label,meta in [('修改前',b),('最终候选',c)]:axs[0,0].plot([x['t_s'] for x in meta['frames']],[x['callback_s']*1000 for x in meta['frames']],label=label)
    axs[0,0].set(title='55帧逐帧回调耗时（本机CPU）',xlabel='记录时间 / s',ylabel='ms');axs[0,0].legend()
    tt=np.array([x['t_s'] for x in f]);axs[0,1].plot(tt,[100*x['old_low_kept']/x['low_points'] for x in f],label='旧方框');axs[0,1].plot(tt,[100*x['new_low_kept']/x['low_points'] for x in f],label='新几何过滤')
    axs[0,1].set(title='低位实测回波保留率（不是地面真值）',xlabel='旧录包时间 / s',ylabel='%',ylim=(85,101));axs[0,1].legend()
    labels=['修改前','候选1','最终候选'];xx=np.arange(3);published=[timed[k]['outputs'] for k in timed];replaced=[timed[k]['pending_replaced'] for k in timed]
    axs[1,0].bar(xx-.18,published,.36,label='处理输出');axs[1,0].bar(xx+.18,replaced,.36,label='等待队列被新帧替换');axs[1,0].set(xticks=xx,xticklabels=labels,ylabel='帧',title='按原节奏到达55帧；不是网络丢包');axs[1,0].legend()
    last=c['frames'][-1];axs[1,1].bar(['车旁格子','缺物理支撑','HT上下文无效'],[last['body_cells'],last['body_physical_unknown'],last['body_context_invalid']],color=['#6199c6','#d6a53a','#bc5650']);axs[1,1].set(title='已录入高程中的车旁盲区未被恢复',ylabel='格')
    for ax in axs.flat:ax.grid(axis='y',alpha=.25)
    fig.suptitle('第二轮：过滤、推理与输入时序的同数据对照',fontsize=17);fig.savefig(out/'comparison.png',dpi=150);plt.close(fig)
    render_cloud(root/'cloud_v2',cloud,plt)
    # Reuse the original grid/transparent-voxel renderer, without changing data.
    replay.render_current(root/'after_v2/maps',plt)
    replay.encode(root/'after_v2/maps',a.ffmpeg,.2)
    replay.encode(root/'cloud_v2',a.ffmpeg,1.)
    shutil.copy2(root/'after_v2/maps/frames/00020.png',out/'ht_keyframe.png')
    shutil.copy2(root/'cloud_v2/frames/00000.png',out/'cloud_keyframe.png')
    print(json.dumps({k:v for k,v in summary.items() if k not in ['per_frame_parity','last_frame']},ensure_ascii=False,indent=2))


def render_cloud(folder,metadata,plt):
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Rectangle,Circle
    pngs=folder/'frames';pngs.mkdir(exist_ok=False)
    t=np.array(metadata['base_from_lidar']);frames=metadata['frames']
    for index,f in enumerate(frames):
        with np.load(folder/f['file']) as d:
            xyz=d['xyz'];base=xyz@t[:3,:3].T+t[:3,3];finite=np.isfinite(xyz).all(1)
            fig=plt.figure(figsize=(19.2,10.8),dpi=100)
            fig.suptitle(f'原始实车点云：自过滤同输入对比 | t={f["t_s"]:.1f}s | 抽样 {index+1}/{len(frames)}',fontsize=22,y=.97)
            for k,(label,keep) in enumerate([('原始低位回波',finite),('旧大方框保留',d['before']),('新车体几何保留',d['after'])]):
                ax=fig.add_axes([.055+k*.315,.52,.27,.33]);selected=keep&d['low']
                count=np.histogram2d(base[selected,0],base[selected,1],bins=75,range=[[-1.5,1.5],[-1.5,1.5]])[0]
                ax.imshow((count>0).T,origin='lower',extent=[-1.5,1.5,-1.5,1.5],interpolation='nearest',cmap=ListedColormap(['#c6c9cc','#3eaa69']),vmin=0,vmax=1)
                ax.add_patch(Rectangle((-.4625,-.19),.925,.38,fill=False,color='black',lw=1.2))
                ax.set(title=f'{label}：{int(selected.sum())} 点',xlabel='base X / m',ylabel='base Y / m',aspect='equal')
            for k,(label,keep) in enumerate([('旧方框：会删除部分低位地面候选',d['before']),('新几何：按车体形状过滤',d['after'])]):
                ax=fig.add_axes([.065+k*.48,.15,.40,.24]);roi=finite&(np.abs(base[:,1])<.7)&(np.abs(base[:,0])<1.5)
                ax.scatter(base[roi&keep,0],base[roi&keep,2],s=.5,c='#73808c',rasterized=True)
                ax.scatter(base[roi&~keep,0],base[roi&~keep,2],s=1,c='#df5348',rasterized=True)
                ax.set(title=label,xlabel='base X / m',ylabel='base Z / m',xlim=(-1.5,1.5),ylim=(-.6,.8));ax.grid(alpha=.2)
            fig.text(.05,.065,'上：4cm显示格，绿=有保留的低位实测回波，灰=无回波；黑框=车体投影。下：红点=被删，灰点=保留。\n低位回波定义：雷达z在[-1.1,-0.7]m且距车体中心≤1.5m；属于地面候选，没有地面真值标签。',fontsize=12)
            fig.text(.53,.065,'旧录包每5秒抽样；这是离线点云处理，没有新版车辆运动。\n已有高程图里的缺测不会由此视频恢复；未重新运行CuPy建图。',fontsize=12)
            fig.savefig(pngs/f'{index:05d}.png');plt.close(fig)
        if index%10==0:print('render cloud',index+1,len(frames),flush=True)


if __name__=='__main__':main()
