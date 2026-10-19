#!/usr/bin/env python3
"""Plot preserved600s HT revisions by scene, retaining failures and provenance."""
import argparse
import collections
import csv
import hashlib
import json
import math
from pathlib import Path
import shutil

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import ListedColormap, PowerNorm
import numpy as np


ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text())
def csvrows(p):
    with p.open() as f:return list(csv.DictReader(f))
def numeric(v):
    try:return float(v)
    except (ValueError,TypeError):return float('nan')
def save(fig,out,name):
    fig.savefig(out/(name+'.png'),dpi=170,bbox_inches='tight')
    fig.savefig(out/(name+'.pdf'),bbox_inches='tight');plt.close(fig)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--metrics-root',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    stages=read(ROOT/'docs/version_history.json')['stages'];index=read(args.metrics_root/'index.json')
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    collected=[];unknown=0
    for path in sorted((ROOT/'docs/results').glob('*/**/manifest.json')):
        folder=path.parent
        if folder.name not in ['indoor','garage','campus','forest','tunnel']:continue
        if not (folder/'metric_definition.json').exists() or not (folder/'endurance_audit.json').exists():continue
        manifest=read(path);summary=read(folder/'summary.json')
        if summary.get('duration_s')!=600:continue
        motion=csvrows(folder/'timeseries.csv');metric=read(folder/'metric_definition.json')
        if not motion or float(motion[-1]['t_s'])<599:continue
        audit=read(folder/'endurance_audit.json');external=audit.get('external_metrics') or {}
        vpath=folder/'observation_volume.csv';recomputed=None
        if str(folder) in index:
            recomputed=Path(index[str(folder)]);vpath=recomputed/'observation_volume.csv'
            external=read(recomputed/'external_metrics.json')
        if 'absolute source second' not in metric.get('selection','') and recomputed is None:
            raise ValueError('Metric needs common source-second recomputation: '+str(folder))
        volume=csvrows(vpath);mission=read(folder/'mission_audit.json');validation=read(folder/'suite_validation.json')
        stage=next((s for s in stages if s['sha']==manifest['git_head']),None)
        if stage is None:
            stage=next((s for s in stages if any(str(folder.parent.relative_to(ROOT))+'/' in ev for ev in s.get('evidence',[]))),None)
        if stage is None:
            unknown+=1;sid=f'D{unknown}';title=folder.parent.name
        else:sid=f'S{stage["number"]:02}';title=stage['title']
        if folder.parent.name=='ht_zero_twist_only_10min_2026-10-18':sid='S21a';title='晚拒绝发零，原航向数'
        elif folder.parent.name=='ht_zero_twist_fine_heading_10min_2026-10-18':sid='S21b';title='晚拒绝发零与32航向'
        t=np.array([numeric(r['t_s']) for r in motion]);age=np.array([numeric(r.get('ht_map_age_s')) for r in motion]);runtime=np.array([numeric(r.get('planner_runtime_s')) for r in motion])
        files=[path,folder/'summary.json',folder/'metric_definition.json',folder/'suite_validation.json',folder/'timeseries.csv',vpath,folder/'endurance_audit.json']
        row=dict(id=sid,title=title,scene=folder.name,git_head=manifest['git_head'],started_at=manifest['started_at'],folder=str(folder),
            distance_m=summary['distance_m'],volume_m3=float(volume[-1]['observed_free_volume_m3']),final_mission=mission['last_sampled_mission'],
            last60_m=external.get('distance_last60_m'),zero_s=external.get('longest_zero_command_s'),no_translation_s=external.get('longest_no_translation_command_s'),
            stopped_fraction=external.get('fully_stopped_fraction'),turn_fraction=external.get('stationary_turn_fraction'),reverse_fraction=external.get('reverse_command_fraction'),
            runtime_p95_s=summary.get('planner_runtime_p95_s'),map_age_p95_s=audit['sampled_map_age_s'].get('p95'),map_age_max_s=audit['sampled_map_age_s'].get('max'),
            timeouts=None,late_nonzero=None,failed_recording_checks=[k for k,v in validation['checks'].items() if not v],
            metric_recomputed=bool(recomputed),metric_provenance=str(recomputed) if recomputed else str(folder/'metric_definition.json'),
            input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
        search=folder.parent/'search_audit/summary.json'
        if search.exists():row['timeouts']=read(search)['all']['termination'].get('TIME_LIMIT',0)
        blocked=folder/'blocked_commands.json'
        if blocked.exists():row['late_nonzero']=read(blocked).get('blocked_nonzero_count')
        row['start_pose']=summary['start_pose_xyyaw'];row['speed_cap_mps']=manifest['speed_cap_mps']
        collected.append(dict(row=row,motion=motion,volume=volume,t=t,age=age,runtime=runtime,folder=folder))
    collected.sort(key=lambda x:x['row']['started_at'])
    records=[d['row'] for d in collected];(out/'measurements.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
    fields=[k for k in records[0] if k not in ['input_sha256','start_pose']]
    with (out/'measurements.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');w.writeheader();w.writerows(records)
    coverage=[]
    for s in stages:
        matched=[r for r in records if r['git_head']==s['sha'] or r['id'].startswith(f'S{s["number"]:02}')]
        coverage.append(dict(stage=s['number'],sha=s['sha'],title=s['title'],complete600s_records=len(matched),scenes=','.join(sorted({r['scene'] for r in matched})),evidence=';'.join(s.get('evidence',[])),note='见measurement表与分场景图' if matched else '没有可统一展示的本协议600s曲线；保留原验证说明，不补造数值'))
    with (out/'version_data_coverage.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=coverage[0]);w.writeheader();w.writerows(coverage)
    shutil.copytree(args.metrics_root,out/'recomputed_metrics',ignore=shutil.ignore_patterns('*.log'))
    generated=[]
    for scene in ['indoor','garage']:
        group=[d for d in collected if d['row']['scene']==scene]
        if not group:continue
        # Only matched origin/speed/protocol traces are put in the same axes.
        first=group[0]['row']
        for d in group:
            r=d['row'];a,b=r['start_pose'],first['start_pose']
            if math.hypot(a[0]-b[0],a[1]-b[1])>.05 or abs(math.remainder(a[2]-b[2],2*math.pi))>.02 or r['speed_cap_mps']!=first['speed_cap_mps']:
                raise ValueError('Unmatched starting pose/speed: '+str(r['folder']))
        names=[d['row']['id']+(' ×' if d['row']['failed_recording_checks'] else '') for d in group];x=np.arange(len(group));colors=plt.cm.turbo(np.linspace(.03,.95,len(group)))
        scene_name={'indoor':'室内','garage':'车库'}[scene]
        fig,ax=plt.subplots(3,2,figsize=(max(13,len(group)*.63),12),layout='constrained')
        panels=[('volume_m3','累计观测自由体积（近似）','m³'),('distance_m','实际里程','m'),('last60_m','最后60秒实际里程','m'),('zero_s','最长停车（区别于原地转向）','s'),('runtime_p95_s','整体规划耗时P95','s'),('map_age_p95_s','HT地图年龄P95 / 最大','s')]
        for axis,(key,title,unit) in zip(ax.flat,panels):
            axis.bar(x,[d['row'][key] for d in group],color=colors)
            if key=='map_age_p95_s':
                axis.plot(x,[d['row']['map_age_max_s'] for d in group],'k.-',label='最大');axis.axhline(3,color='red',ls='--',label='3秒保护');axis.legend()
            axis.set(title=title,ylabel=unit,xticks=x,xticklabels=names);axis.tick_params(axis='x',rotation=65);axis.grid(axis='y',alpha=.2)
        fig.suptitle(scene_name+'：各次完整600秒记录；×为采集异常，单次结果不代表因果或统计优越')
        name=scene+'_01_overview';save(fig,out,name);generated.append(name)
        fig,axes=plt.subplots(2,1,figsize=(13,9),layout='constrained')
        for d,c,label in zip(group,colors,names):
            axes[0].plot([float(r['time_s'])/60 for r in d['volume']],[float(r['observed_free_volume_m3']) for r in d['volume']],c=c,label=label)
            axes[1].plot(d['t']/60,[float(r['distance_m']) for r in d['motion']],c=c,label=label)
        for axis in axes:axis.set(xlim=(0,10),xlabel='测量时间 / 分钟');axis.grid(alpha=.2);axis.legend(ncol=min(8,len(group)),fontsize=8)
        axes[0].set(ylabel='m³',title='累计观测自由体积，统一按源秒输入重算旧口径')
        axes[1].set(ylabel='m',title='实际累计里程；曲线变平不能独自说明完成或故障')
        name=scene+'_02_curves';save(fig,out,name);generated.append(name)
        increments=[]
        for d in group:
            v=np.interp(np.arange(11)*60,[float(r['time_s']) for r in d['volume']],[float(r['observed_free_volume_m3']) for r in d['volume']]);increments.append(np.diff(v))
        fig,axis=plt.subplots(figsize=(12,max(4,len(group)*.43)),layout='constrained');arr=np.array(increments)
        im=axis.imshow(arr,cmap='YlGnBu',norm=PowerNorm(.5,vmin=0,vmax=max(float(arr.max()),1)),aspect='auto')
        for i in range(len(group)):
            for j in range(10):axis.text(j,i,f'{arr[i,j]:.0f}',ha='center',va='center',fontsize=8,color='white' if arr[i,j]>arr.max()*.45 else 'black')
        axis.set(yticks=x,yticklabels=names,xticks=np.arange(10),xticklabels=[f'{i}–{i+1}' for i in range(10)],xlabel='时间 / 分钟',title=scene_name+'：每分钟新增观测自由体积（m³）');fig.colorbar(im,ax=axis,label='m³，平方根色阶')
        name=scene+'_03_minute_gain';save(fig,out,name);generated.append(name)
        fig,axis=plt.subplots(figsize=(max(12,len(group)*.6),5.5),layout='constrained');bottom=np.zeros(len(group))
        parts=[('停车',[d['row']['stopped_fraction'] for d in group],'#bd4242'),('原地转向',[d['row']['turn_fraction'] for d in group],'#e7ab3b'),('倒车（v<−0.05）',[d['row']['reverse_fraction'] for d in group],'#8b72b4')]
        for label,values,c in parts:values=np.asarray(values)*100;axis.bar(x,values,bottom=bottom,color=c,label=label);bottom+=values
        axis.bar(x,100-bottom,bottom=bottom,color='#489da1',label='其余平移');axis.set(xticks=x,xticklabels=names,ylabel='控制消息占比 / %',ylim=(0,100),title=scene_name+'：停车、转向和倒车分别统计');axis.tick_params(axis='x',rotation=65);axis.legend(ncol=4,fontsize=9)
        name=scene+'_04_motion';save(fig,out,name);generated.append(name)
        fig,axes=plt.subplots(2,1,figsize=(max(12,len(group)*.6),8),layout='constrained')
        for axis,key,title in [(axes[0],'runtime','整体规划耗时的0.5s状态采样分布（非独立规划调用）'),(axes[1],'age','HT地图年龄的0.5s状态采样分布')]:
            vals=[d[key][np.isfinite(d[key])] for d in group];axis.boxplot(vals,labels=names,showfliers=False);axis.tick_params(axis='x',rotation=65);axis.set(ylabel='s',title=title);axis.grid(axis='y',alpha=.2)
        axes[1].axhline(3,color='red',ls='--',label='3秒保护');axes[1].legend()
        name=scene+'_05_latency';save(fig,out,name);generated.append(name)
        cols=min(4,len(group));rows=math.ceil(len(group)/cols);fig,axes=plt.subplots(rows,cols,figsize=(cols*4.2,rows*4.3),layout='constrained',squeeze=False)
        allx=[float(r['x_m']) for d in group for r in d['motion']];ally=[float(r['y_m']) for d in group for r in d['motion']];limits=(min(allx)-1,max(allx)+1,min(ally)-1,max(ally)+1)
        for axis,d,label in zip(axes.flat,group,names):
            pts=np.array([[float(r['x_m']),float(r['y_m'])] for r in d['motion']]);segments=np.stack([pts[:-1],pts[1:]],1);line=LineCollection(segments,cmap='viridis',norm=plt.Normalize(0,600));line.set_array(d['t'][:-1]);line.set_linewidth(1.3);axis.add_collection(line);axis.scatter(*pts[0],c='green',s=25,marker='o');axis.scatter(*pts[-1],c='red',s=25,marker='x');axis.set(xlim=limits[:2],ylim=limits[2:],xlabel='X / m',ylabel='Y / m',title=f"{label} · {d['row']['final_mission']}\n{d['row']['distance_m']:.1f}m / {d['row']['volume_m3']:.0f}m³");axis.set_aspect('equal');axis.grid(alpha=.2)
        for axis in list(axes.flat)[len(group):]:axis.set_visible(False)
        fig.suptitle(scene_name+'：统一空间尺度的实际轨迹；颜色为时间，绿起点、红终点')
        name=scene+'_06_trajectories';save(fig,out,name);generated.append(name)
        fig,axis=plt.subplots(figsize=(13,max(4,len(group)*.42)),layout='constrained');state=np.full((len(group),600),-1.)
        statekeys={'EXPLORING':0,'BLOCKED':1,'RETURNING':2,'COMPLETED':3}
        for i,d in enumerate(group):
            snapshot=read(d['folder']/'late_map_snapshot.json');origin=snapshot['ht_stamp']-snapshot['measurement_time_s']
            for r in csvrows(d['folder']/'health.csv'):
                t=int(float(r['wall_time'])-origin)
                if 0<=t<600:state[i,t]=statekeys.get(r['mission'],-1)
        cmap=ListedColormap(['#c5c5c5','#3b9c65','#c44848','#bba331','#4376ad']);axis.imshow(state+1,vmin=-.5,vmax=4.5,cmap=cmap,aspect='auto',extent=(0,10,len(group)-.5,-.5));axis.set(yticks=x,yticklabels=names,xlabel='时间 / 分钟',title=scene_name+'：1Hz任务状态；灰=缺采样，绿=探索，红=阻塞，黄=返航，蓝=内部完成')
        name=scene+'_07_mission';save(fig,out,name);generated.append(name)
    lines=['# 历次修改：多角度探索变化对比','', '按场景分别比较完整600秒记录，失败轮、同版失败复测和阶段34退出异常均保留。统一速度/初始位姿容差检查；不同场景不合并排名。所有体积统一绝对源秒、0.5m自由体素并集近似，旧口径从原始MCAP重新计算，原报告不回写。','', '没有同一协议600秒数据的早期版本不会补造曲线；1至最新阶段逐项覆盖情况见[版本数据覆盖表](version_data_coverage.csv)。D编号为另存的诊断/未采用候选，具体改动和来源见[完整数据表](measurements.csv)。单次闭环轨迹不构成统计或单项因果证明，体积不是物理覆盖真值。','', '停车按|v|<0.01m/s且|ω|<0.05rad/s，转向按|v|<0.01且|ω|>0.05；倒车占比是全部消息中v<−0.05的子集。内部COMPLETED不是全环境覆盖真值。旧轮缺失的搜索/晚拒绝审计值留空。','']
    for name in generated:lines += [f'![{name}]({name}.png)','']
    lines += ['## 每次记录与改动','', '| ID | 环境 | 改动/目的 | 里程m | 近似体积m³ | 最长停车s | 最终状态 |','|---|---|---|---:|---:|---:|---|']
    for r in records:lines.append(f"| {r['id']} | {r['scene']} | {r['title']} | {r['distance_m']:.2f} | {r['volume_m3']:.3f} | {r['zero_s']:.2f} | {r['final_mission']} |")
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n');print(json.dumps(dict(records=len(records),figures=len(generated),output=str(out)),indent=2))


if __name__=='__main__':main()
