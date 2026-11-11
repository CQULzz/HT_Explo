"""Offline metrics, recovery events and trajectory visualization for the 600s repeat."""
from pathlib import Path
from collections import Counter
import csv
import io
import json
import math
import subprocess
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont

ROOT=Path('/home/lzz/ht_quality_600s_20261112')
RUN=ROOT/'runs/cmu_quality_600s_02'
OUT=ROOT/'delivery'
plt.rcParams.update({'font.family':'sans-serif','font.sans-serif':['Noto Sans CJK JP','DejaVu Sans'],'axes.unicode_minus':False})
SPECS=[
 ('最初几何＋HT','#94a3b8',Path('/home/lzz/cmu_test_20261110/runs/ht_600s_06')),
 ('历史纯HT','#8b5cf6',Path('/home/lzz/ht_only_20261111/runs/a_indoor_600s_03')),
 ('上次质量修复300秒','#ea580c',Path('/home/lzz/ht_quality_20261111/runs/cmu_quality_300s_01')),
 ('本次同版本600秒','#0f766e',RUN),
]

def load(run):
    rows=list(csv.DictReader((run/'observations/metrics.csv').open()))
    return rows,{k:np.array([float(r[k]) if r[k] else np.nan for r in rows]) for k in rows[0] if k!='finish'}

def value(d,k,t):return float(np.interp(t,d['elapsed_s'],d[k]))

def summary(rows,d):
    out={'source_final_sample_s':float(d['elapsed_s'][-1]),'finish':rows[-1]['finish']=='True'}
    for limit in [300,600]:
        if d['elapsed_s'][-1]<limit:continue
        use=d['elapsed_s']<=limit
        out[str(limit)]={k:value(d,k,limit) for k in ['distance_m','sampled_free_volume_m3']}
        out[str(limit)].update(last_30s_distance_m=value(d,'distance_m',limit)-value(d,'distance_m',limit-30),sampled_latest_ht_source_age_p95_s=float(np.nanpercentile(d['ht_age_s'][use],95)))
    moving=np.abs(d['cmd_linear'])+np.abs(d['cmd_angular'])>1e-8
    out['last_nonzero_sample_s']=float(d['elapsed_s'][moving][-1]) if moving.any() else None
    stopped=[];begin=None
    for i,is_moving in enumerate(moving):
        if not is_moving and begin is None:begin=i
        if is_moving and begin is not None:
            if d['elapsed_s'][i]-d['elapsed_s'][begin]>=1:
                stopped.append({'start_s':float(d['elapsed_s'][begin]),'end_s':float(d['elapsed_s'][i]),'duration_s':float(d['elapsed_s'][i]-d['elapsed_s'][begin])})
            begin=None
    if begin is not None:stopped.append({'start_s':float(d['elapsed_s'][begin]),'end_s':float(d['elapsed_s'][-1]),'duration_s':float(d['elapsed_s'][-1]-d['elapsed_s'][begin])})
    out['zero_command_intervals_ge_1s_sampled']=stopped
    return out

def main():
    OUT.mkdir(exist_ok=True)
    series=[];comparison={}
    for label,color,run in SPECS:
        rows,d=load(run);series.append((label,color,d));comparison[label]={'source_run':str(run),**summary(rows,d)}
    comparison['scope']='Same CMU indoor/start/limits/metric definitions, individual unpaired runs with different trajectories and ROS/GPU scheduling. Values interpolate ~0.5s samples at exactly 300/600s. No extrapolation past the actual 300s baseline. Sampled free volume is an observation proxy, not ground-truth coverage. Sampled zero-command intervals are not exact command timing.'
    fig,axes=plt.subplots(3,1,figsize=(11,9),sharex=True)
    for label,color,d in series:
        use=d['elapsed_s']<=600
        for ax,k in zip(axes,['distance_m','sampled_free_volume_m3','ht_age_s']):ax.plot(d['elapsed_s'][use],d[k][use],color=color,lw=1,label=label)
    for ax,label in zip(axes,['实际里程 / m','采样观测自由体积 / m³','最新HT源龄 / s']):ax.set_ylabel(label);ax.grid(alpha=.2)
    axes[0].legend(fontsize=9);axes[-1].axhline(1,color='red',ls='--');axes[-1].set_xlabel('任务时间 / s');axes[-1].set_xlim(0,600)
    fig.suptitle('CMU indoor：同一修复版本延长至10分钟；旧300秒曲线仅显示实测区间')
    fig.tight_layout();fig.savefig(OUT/'progress_comparison.png',dpi=160);plt.close(fig)
    p=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/indoor/preview/pointcloud.ply')
    with p.open('rb') as f:
        while f.readline().strip()!=b'end_header':pass
        points=np.frombuffer(f.read(),dtype='<f4').reshape(-1,3)[::8];points=points[points[:,2]<2]
    fig,ax=plt.subplots(figsize=(12,8));ax.scatter(points[:,0],points[:,1],s=.1,c='#cbd5e1')
    for label,color,d in series:
        use=d['elapsed_s']<=600;xx=d['x'][use];yy=d['y'][use]
        ax.plot(xx,yy,color=color,lw=1.5,label=f'{label}，{d["distance_m"][-1]:.2f}m');ax.scatter(xx[-1],yy[-1],s=25,c=color)
    ax.set(aspect='equal',xlabel='世界X / m',ylabel='世界Y / m',title='录制里程计轨迹：各自实际测量区间');ax.legend(fontsize=9);fig.tight_layout();fig.savefig(OUT/'trajectory_comparison.png',dpi=160);plt.close(fig)
    start=json.loads((RUN/'observations/START.json').read_text())['clock'];end=float(series[-1][2]['time'][-1]);last={};recoveries=[];finish_events=[]
    for line in (RUN/'observations/events.jsonl').open():
        e=json.loads(line)
        if not start<=e['time']<=end:continue
        last[e['kind']]=e['data']
        if e['kind']=='/ht_minimal/recovery':recoveries.append(e['data'])
        if e['kind']=='finish_transition':finish_events.append({'elapsed_s':e['time']-start,**e['data']})
    episodes={}
    for e in recoveries:
        i=e['plans']
        if i and e['state']=='EXECUTING' and i not in episodes:episodes[i]={'start':e,'end':None}
        if i in episodes and e['state']=='COMPLETED' and episodes[i]['end'] is None:episodes[i]['end']=e
    eps=[]
    for i,pair in episodes.items():
        a,b=pair['start'],pair['end'];item={'plan':i,'start_elapsed_s':a['time']-start,'completed':b is not None,'start':a,'end':b}
        if b:item.update(end_elapsed_s=b['time']-start,duration_s=b['time']-a['time'],net_displacement_m=math.dist((a['x'],a['y']),(b['x'],b['y'])))
        eps.append(item)
    diagnostics={'last_events':last,'finish_transitions':finish_events,'recovery_state_counts':Counter(e['state'] for e in recoveries),'recovery_episodes':eps,'scope':'Recovery movement only spans each EXECUTING start to its first COMPLETED event. No simulated/fixture movement is included.'}
    (OUT/'COMPARISON.json').write_text(json.dumps(comparison,indent=2));(ROOT/'analysis/DIAGNOSTICS.json').write_text(json.dumps(diagnostics,indent=2))
    font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',22);small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',17)
    fig,ax=plt.subplots(figsize=(11,7),dpi=100);ax.scatter(points[:,0],points[:,1],s=.1,c='#cbd5e1');ax.set_aspect('equal');ax.axis('off');fig.subplots_adjust(0,0,1,1);fig.canvas.draw();box=ax.get_window_extent();xlim=ax.get_xlim();ylim=ax.get_ylim();buf=io.BytesIO();fig.savefig(buf,format='png',dpi=100);plt.close(fig);buf.seek(0);base=Image.open(buf).convert('RGB')
    def pixel(x,y):return(box.x0+(x-xlim[0])/(xlim[1]-xlim[0])*box.width,700-(box.y0+(y-ylim[0])/(ylim[1]-ylim[0])*box.height)+80)
    ffmpeg='/home/lzz/cmu_test_20261110/deps/usr/bin/ffmpeg';video=OUT/'quality_600s_10x.mp4'
    proc=subprocess.Popen([ffmpeg,'-y','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24','-s','1100x940','-r','10','-i','-','-c:v','libx264','-threads','1','-preset','fast','-pix_fmt','yuv420p',str(video)],stdin=subprocess.PIPE)
    for second in range(601):
        im=Image.new('RGB',(1100,940),'white');im.paste(base,(0,80));draw=ImageDraw.Draw(im);draw.text((20,8),'CMU indoor｜原TARE＋八方向HT｜同版本10分钟复测',font=font,fill='#0f172a');draw.text((20,40),f'录制轨迹可视化（非相机/RViz录像），10倍速  t={second}s',font=small,fill='#475569')
        for row,(label,color,d) in enumerate(series):
            i=max(0,min(int(np.searchsorted(d['elapsed_s'],second,side='right')-1),len(d['x'])-1));xy=[pixel(x,y) for x,y in zip(d['x'][:i+1:2],d['y'][:i+1:2])]
            if len(xy)>1:draw.line(xy,fill=color,width=3)
            u,v=pixel(d['x'][i],d['y'][i]);draw.ellipse((u-4,v-4,u+4,v+4),fill=color)
            ended='（仅测300秒，已结束）' if d['elapsed_s'][-1]<599 and second>d['elapsed_s'][-1] else ''
            draw.text((20,795+row*32),f'{label}{ended}：{d["distance_m"][i]:.2f}m，观测体积 {d["sampled_free_volume_m3"][i]:.1f}m³',font=small,fill=color)
        proc.stdin.write(im.tobytes())
    proc.stdin.close();assert proc.wait()==0
    subprocess.run([ffmpeg,'-v','error','-i',str(video),'-f','null','-'],check=True)
    print(json.dumps(comparison,indent=2))

if __name__=='__main__':main()
