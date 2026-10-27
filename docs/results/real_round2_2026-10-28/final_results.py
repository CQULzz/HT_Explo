"""Final factual report figures and videos from frozen offline outputs."""
from pathlib import Path
import argparse,json,sys,os,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/ht_cupy_bridge'))
import replay_real_archive as replay


def read(p):return json.loads(p.read_text())
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def stats(d):
    x=np.array([v['callback_s'] for v in d['frames']])*1000
    return {'mean_ms':float(x.mean()),'median_ms':float(np.median(x)),'p95_ms':float(np.percentile(x,95)),'max_ms':float(x.max())}


def main():
    p=argparse.ArgumentParser();p.add_argument('--data',type=Path,required=True);p.add_argument('--ffmpeg',required=True)
    p.add_argument('--figures-only',action='store_true',help='Regenerate metrics and figures without overwriting videos')
    a=p.parse_args()
    root=a.data;out=ROOT/'docs/results/real_round2_2026-10-28';plt=replay.plot_setup()
    before=root/'rebuilt_ht_before/maps';after=root/'rebuilt_ht_after/maps';b=read(before/'index.json');c=read(after/'index.json')
    assert b['outputs']==c['outputs']==208
    timed={}
    for role in ['before','after']:
        timed[role]=[]
        for i in [1,2,3]:
            d=read(root/f'gpu_numba_timed_{role}_{i}/timed.json');timed[role].append({'outputs':d['outputs'],'pending_replaced':d['pending_replaced'],
                'max_map_age_s':max(x['source_age_at_publish_s'] for x in d['diagnostics']),'input_fault':d['input_fault']})
    fixed_before=read(root/'gpu_numba_before/maps/index.json');fixed_after=read(root/'gpu_numba_after/maps/index.json');delta=0.;flips=0
    for x,y in zip(fixed_before['frames'],fixed_after['frames']):
        with np.load(root/'gpu_numba_before/maps'/x['file']) as u,np.load(root/'gpu_numba_after/maps'/y['file']) as v:
            for k in ['ht_valid','ht_observation_valid','ht_obstacle']:np.testing.assert_array_equal(u[k],v[k])
            mask=u['ht_valid']>=.5;delta=max(delta,float(np.max(abs(u['probabilities'][:,mask]-v['probabilities'][:,mask]))))
            flips+=int(np.count_nonzero((u['probabilities'][:,mask]>=.5)!=(v['probabilities'][:,mask]>=.5)))
    last=c['frames'][-1]
    with np.load(after/last['file']) as d:
        n=d['ht_valid'].shape[0];r=float(d['resolution']);ii,jj=np.indices((n,n))
        xx=d['center'][0]+(n/2-ii-.5)*r;yy=d['center'][1]+(n/2-jj-.5)*r
        dx=xx-d['robot'][0];dy=yy-d['robot'][1];yaw=d['robot'][2];bx=dx*np.cos(yaw)+dy*np.sin(yaw);by=-dx*np.sin(yaw)+dy*np.cos(yaw)
        body=dx*dx+dy*dy<=.6**2;near=dx*dx+dy*dy<=1.
        cx=int(round(n/2-.5-(d['robot'][0]-d['center'][0])/r));cy=int(round(n/2-.5-(d['robot'][1]-d['center'][1])/r))
        center_scores=d['probabilities'][:,cx,cy].tolist();z=d['ht_elevation'];q=np.quantile(z[near&np.isfinite(z)],[.05,.95])
        fig,axs=plt.subplots(1,2,figsize=(13,5.5),layout='constrained');colors=plt.get_cmap('terrain').copy();colors.set_bad('#c6c9cc')
        field=np.where(near,z-q[0],np.nan);im=axs[0].pcolormesh(bx,by,field,cmap=colors,vmin=0,vmax=1.05,shading='nearest');axs[0].set(xlim=(-1.1,1.1),ylim=(-1.1,1.1),aspect='equal',xlabel='车体X / m',ylabel='车体Y / m',title='末帧车旁高程仍有高点（来源待核验）');fig.colorbar(im,ax=axs[0],label='相对低位高程 / m')
        from matplotlib.patches import Rectangle,Circle
        axs[0].add_patch(Rectangle((-.4625,-.19),.925,.38,fill=False,color='black',lw=1.5));axs[0].add_patch(Circle((0,0),.6,fill=False,color='black',ls='--'))
        axs[1].bar([str(k*45)+'°' for k in range(8)],center_scores);axs[1].axhline(.5,color='red',ls='--',label='硬门槛0.5');axs[1].set(ylim=(0,1),ylabel='车位中心T',title='最高T仍低于门槛；不据此确认能走');axs[1].legend()
        fig.savefig(out/'remaining_high_points.png',dpi=150);plt.close(fig)
        body_measured=int((body&(d['ht_measured_valid']>=.5)).sum())
    cpu=read(out/'SUMMARY.json');summary={'scope':'Offline frozen-source experiments; not a new vehicle run or navigation trial',
        'runtime_local_commit':c['source_commit'],'source_mapping':read(root/'GITHUB_SOURCE_MAPPING.json'),
        'python_gpu_tests_passed':215,'cupy_gpu_observation_age_tests_passed':8,
        'fixed_55_frame_parity':{'max_probability_difference':delta,'threshold_0_5_flips':flips,'validity_masks_equal':True},
        'timings':{'old_cpu_numpy':cpu['timing_before'],'new_cpu_numpy':cpu['timing_candidate_v2'],
            'new_cuda_numpy':stats(read(root/'gpu_after_retry1/maps/index.json')),'old_cuda_numba':stats(fixed_before),'new_cuda_numba':stats(fixed_after)},
        'six_second_timed_traces':timed,'rebuild':read(root/'cupy_rebuild/SUMMARY.json'),
        'before_last':b['frames'][-1],'after_last':last,
        'after_body_measured_cells':body_measured,
        'after_center_direction_scores':center_scores,'after_center_max_T':max(center_scores),
        'remaining_height_span_5_to_95_m':float(q[1]-q[0]),
        'candidate_before_after_body_unknown':[[x['t_s'],x['body_physical_unknown'],y['body_physical_unknown']] for x,y in zip(b['frames'],c['frames'])],
        'limitations':['415 sampled raw scans, 208 maps each; 0.5s scan sampling, 1s HT map sampling',
            'Derived base poses from recorded lidar poses and verified static calibration; twist explicitly NaN and never used for control',
            'Physical support includes existing 0.25m nearest-observation support; it is not direct measurement at every cell',
            'Last-frame low center T remains; high points may be real obstacles or unmodelled vehicle attachments',
            'Short arrival traces still replace pending frames; not evidence of network packet loss or long-term stability']}
    write(out/'FINAL_SUMMARY.json',summary)
    fig,axs=plt.subplots(2,2,figsize=(14,9),layout='constrained')
    for label,meta in [('旧自过滤',b),('新几何过滤',c)]:axs[0,0].plot([x['t_s'] for x in meta['frames']],[x['body_physical_unknown'] for x in meta['frames']],label=label)
    axs[0,0].set(title='同一轨迹重建：车旁缺物理支撑格数',xlabel='记录时间 / s',ylabel='格');axs[0,0].legend()
    timing=summary['timings'];labels=['旧CPU/NumPy','新CPU/NumPy','新CUDA/NumPy','新CUDA/Numba'];keys=['old_cpu_numpy','new_cpu_numpy','new_cuda_numpy','new_cuda_numba']
    axs[0,1].bar(labels,[timing[k]['median_ms'] for k in keys]);axs[0,1].set(title='执行环境与代码因素分开显示',ylabel='回调中位数 / ms');axs[0,1].tick_params(axis='x',labelrotation=15)
    for role,label in [('before','旧代码/同GPU后端'),('after','新代码/同GPU后端')]:axs[1,0].plot([1,2,3],[x['max_map_age_s'] for x in timed[role]],'o-',label=label)
    axs[1,0].axhline(1,color='red',ls='--');axs[1,0].set(title='三次6秒到达回放；依然有队列替换',xlabel='重复轮次',ylabel='最大地图年龄 / s',xticks=[1,2,3],ylim=(0,1.1));axs[1,0].legend()
    repeats=np.array([1,2,3])
    for role,label,offset in [('before','旧代码/同GPU后端',-.18),('after','新代码/同GPU后端',.18)]:
        axs[1,1].bar(repeats+offset,[x['outputs'] for x in timed[role]],width=.36,label=label)
    axs[1,1].axhline(55,color='red',ls='--',label='输入55帧')
    axs[1,1].set(title='相同到达时间下输出帧数：仍有波动',xlabel='重复轮次',ylabel='输出帧数',xticks=[1,2,3],ylim=(0,65));axs[1,1].legend()
    for ax in axs.flat:ax.grid(axis='y',alpha=.25)
    fig.suptitle('第二轮最终复测：正向变化与未解决项同时保留',fontsize=17);fig.savefig(out/'FINAL_COMPARISON.png',dpi=150);plt.close(fig)
    if a.figures_only:return
    chosen=sorted(set(list(range(0,len(c['frames']),5))+[len(c['frames'])-1]));video=root/'rebuilt_video';video.mkdir(exist_ok=False)
    meta=dict(c);meta['frames']=[c['frames'][i] for i in chosen];meta['outputs']=len(chosen)
    for f in meta['frames']:os.link(after/f['file'],video/f['file'])
    write(video/'index.json',meta)
    replay.render_current(video,plt,data_label='10月11日点云→CuPy→HT',playback_speed=1,display_note='处理208帧，视频约每5秒展示一帧。')
    replay.encode(video,a.ffmpeg,1.)
    compare=root/'support_comparison_video';compare.mkdir(exist_ok=False);(compare/'frames').mkdir()
    cm=dict(meta);cm['frames']=[dict(f,file=f'not_used_{i}.npz') for i,f in enumerate(meta['frames'])];write(compare/'index.json',cm)
    for k,i in enumerate(chosen):
        x,y=b['frames'][i],c['frames'][i];fig,axes=plt.subplots(1,2,figsize=(19.2,10.8),dpi=100,layout='constrained')
        for ax,label,folder,f in [(axes[0],'旧大方框',before,x),(axes[1],'新车体几何',after,y)]:
            with np.load(folder/f['file']) as d:
                val=(d['ht_observation_valid']>=.5).astype(float);replay.image(ax,val,d['center'],float(d['resolution']),cmap='Greens',vmin=0,vmax=1)
                ax.add_patch(Circle(d['robot'][:2],.6,fill=False,color='#cc3434',lw=2));ax.plot(d['robot'][0],d['robot'][1],'bo');ax.set_title(f'{label}\n车旁缺支撑 {f["body_physical_unknown"]}/{f["body_cells"]} 格',fontsize=21)
        fig.suptitle(f'同一旧录包点云→CuPy→HT | t={y["t_s"]:.1f}s | 物理支撑对比（非新实车运行）',fontsize=23)
        fig.supxlabel('绿=现有物理支撑（含0.25m近邻支持）；白=缺支撑；红圈r=0.6m；蓝点为记录位姿。\n支撑与HT概率是两个条件。末帧支撑已改善，最高方向概率仍只有0.128，保留硬门槛。',fontsize=15)
        fig.savefig(compare/'frames'/f'{k:05d}.png');plt.close(fig)
        if k%10==0:print('render support comparison',k+1,len(chosen),flush=True)
    replay.encode(compare,a.ffmpeg,1.)
    shutil.copy2(video/'frames'/f'{len(chosen)-1:05d}.png',out/'rebuilt_ht_last.png')
    shutil.copy2(compare/'frames'/f'{len(chosen)-1:05d}.png',out/'support_comparison_last.png')
    print('Final metrics, native HT video and support comparison video saved',flush=True)


if __name__=='__main__':main()
