#!/usr/bin/env python3
"""Seal fresh matched-motion measurements, common metrics, videos and comparisons."""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
import numpy as np

from run_scheduled_comparison import ROOT, UP, CMU
import summarize_tare_ht_pair as common


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def run(arguments, log, timeout=1800):
    with log.open('w') as f:
        subprocess.run([str(x) for x in arguments], stdout=f, stderr=subprocess.STDOUT,
                       check=True, timeout=timeout)


def video(folder, encoder, original):
    probe=read(folder/'probe_summary.json');manifest=read(folder/'manifest.json')
    origin=read(folder/'current/measurement_started.json')['wall_time']
    offset=max(0, origin-probe['video_start_wall_time'])
    command=[encoder, '-nostdin', '-y', '-ss', str(offset), '-i', str(folder/probe['video_file'])]
    if original:
        # The shared observer records the camera without needing HT. Replace
        # its HT-specific last status row, preserving the camera and v/w row.
        band=np.zeros((30,960,3),np.uint8)
        cv2.putText(band,'Original TARE + CMU | matched motion envelope | no HT map',
                    (12,21),cv2.FONT_HERSHEY_SIMPLEX,.55,(120,230,240),1)
        cv2.imwrite(str(folder/'original_status_band.png'),band)
        command += ['-loop','1','-i',str(folder/'original_status_band.png'),
                    '-filter_complex','[0:v][1:v]overlay=0:570:shortest=1']
    command += ['-t','600','-c:v','libx264','-preset','fast','-crf','24',
                '-pix_fmt','yuv420p','-threads','2','-movflags','+faststart',str(folder/'camera_h264.mp4')]
    run(command,folder/'video_encode.log')
    run([encoder,'-nostdin','-v','error','-threads','2','-i',folder/'camera_h264.mp4',
         '-progress','pipe:1','-nostats','-f','null','-'],folder/'video_decode.log',600)
    progress=dict(line.split('=',1) for line in (folder/'video_decode.log').read_text().splitlines() if '=' in line)
    frames=int(progress.get('frame','0'));seconds=frames/15
    result=dict(encode_returncode=0,full_decode_returncode=0,fps=15,decoded_frames=frames,
                duration_s=seconds,duration_matches=abs(seconds-600)<=1/15+.001,
                trim_offset_s=offset,bytes=(folder/'camera_h264.mp4').stat().st_size,
                sha256=sha(folder/'camera_h264.mp4'))
    write(folder/'video_validation.json',result)
    run([encoder,'-nostdin','-v','error','-y','-ss','590','-i',folder/'camera_h264.mp4',
         '-frames:v','1',folder/'late_camera.jpg'],folder/'video_preview.log',60)
    return result


def motion_audit(folder):
    from rclpy.serialization import deserialize_message
    from geometry_msgs.msg import TwistStamped
    origin=read(folder/'current/measurement_started.json')['wall_time']
    r=common.reader(folder/'current_bag',['/cmd_vel','/comparison/tare_raw_cmd_vel'])
    final=[];raw=[]
    while r.has_next():
        topic,data,ns=r.read_next()
        if not 0<=ns/1e9-origin<600:
            continue
        m=deserialize_message(data,TwistStamped)
        t=common.stamp(m)
        (final if topic=='/cmd_vel' else raw).append((t,m.twist.linear.x,m.twist.angular.z))
    def limits(rows):
        a=np.asarray(rows,float)
        if not len(a):
            return dict(samples=0)
        return dict(samples=len(a),max_forward_mps=float(a[:,1].max()),min_linear_mps=float(a[:,1].min()),
                    max_abs_yaw_rps=float(np.abs(a[:,2]).max()))
    a=np.asarray(final,float);timing=np.diff(a[:,0]);delta=np.diff(a[:,1:],axis=0)
    # Explicit zero/emergency holds are immediate in both control chains.
    immediate_zero=np.all(a[1:,1:]==0,axis=1)
    normal=(timing>0)&(timing<.3)&~immediate_zero
    excess=np.any(np.abs(delta)>timing[:,None]*np.array([.5,1.2])+.005,axis=1)&normal
    result=dict(final=limits(final),native_raw=limits(raw),
                cap_passed=bool(np.all(a[:,1]<=.50001) and np.all(a[:,1]>=-.25001) and np.all(np.abs(a[:,2])<=.80001)),
                normal_acceleration_excess_count=int(excess.sum()),
                immediate_zero_transition_count=int((immediate_zero&np.any(np.abs(delta)>.001,axis=1)).sum()),
                scope='Source header time; normal acceleration tolerance0.005 per step; explicit all-zero stops exempt. Different trackers/geometry remain.')
    write(folder/'motion_envelope_audit.json',result)
    return result


def parameter_audit(suite):
    import yaml
    files={name:yaml.safe_load((suite/rel).read_text()) for name,rel in {
        'original_follower':'original/pathFollower_parameters.yaml',
        'original_limits':'original/comparison_motion_limiter_parameters.yaml',
        'ht_follower':'ht/follower_parameters.yaml'}.items()}
    params={name:next(iter(d.values()))['ros__parameters'] for name,d in files.items()}
    h=params['ht_follower'];b=params['original_follower'];l=params['original_limits']
    checks=dict(original_autonomy_speed=math.isclose(b['autonomySpeed'],h['max_speed']),
                original_yaw_limit=math.isclose(math.radians(b['maxYawRate']),h['max_yaw_rate']),
                original_linear_acceleration=math.isclose(b['maxAccel'],h['max_accel']),
                common_envelope=all(math.isclose(l[k],h[v]) for k,v in {
                    'forward_cap':'max_speed','reverse_cap':'max_reverse','yaw_cap':'max_yaw_rate',
                    'linear_accel':'max_accel','yaw_accel':'max_yaw_accel'}.items()))
    planners={}
    for name,rel in [('original','original/tare_planner_node_parameters.yaml'),('ht','ht/planner_parameters.yaml')]:
        d=yaml.safe_load((suite/rel).read_text())
        planners[name]=next(iter(d.values()))['ros__parameters']
    differences={k:dict(original=planners['original'][k],ht=planners['ht'][k])
                 for k in sorted(planners['original'].keys()&planners['ht'].keys())
                 if planners['original'][k]!=planners['ht'][k]}
    grids={name:{key:values['viewpoint_manager/'+key] for key in
                 ('number_x','number_y','resolution_x','resolution_y')} for name,values in planners.items()}
    write(suite/'effective_parameter_comparison.json',dict(checks=checks,parameters=params,viewpoint_grids=grids,
                                                         shared_planner_parameter_differences=differences))
    return checks


def collection(folder, original, motion):
    manifest=read(folder/'manifest.json');summary=read(folder/'summary.json')
    integrity={p:Path(p).is_file() and sha(Path(p))==expected for p,expected in manifest['source_hashes'].items()}
    shutdown=read(folder/'current/shutdown.json');vid=read(folder/'video_validation.json')
    checks=dict(timer_completed=(folder/'COMPLETED.json').exists(),measured600s=summary['duration_s']==600,
                enough_samples=summary['sample_count']>=1020,source_hashes_unchanged=all(integrity.values()),
                no_parent_failure=not (folder/'runtime_failures.json').exists(),
                no_live_descendants=shutdown[-1].get('remaining_live_descendants')==[],
                no_forced_shutdown=not any(x.get('signal') in ('SIGTERM','SIGKILL') for x in shutdown),
                video_decodes=vid['full_decode_returncode']==0,video_duration=vid['duration_matches'],
                motion_caps=motion['cap_passed'],normal_acceleration=motion['normal_acceleration_excess_count']==0)
    if original:
        checks['upstream_tracked_unchanged']=(folder/'upstream_tracked.patch').read_bytes()==b''
    else:
        checks['cmu_terrain_isolated']=read(folder/'terrain_topic_isolation.json')['navigation_cmu_terrain_isolated']
        checks['ht_model_threads_bounded']=all(x['num_threads']==1 for x in read(folder/'current/ht_cpu_threads.json')['blas_pools'])
    write(folder/'suite_validation.json',dict(checks=checks,source_hashes_unchanged=integrity,video=vid))
    return checks


def plots(suite, data, scene='indoor'):
    font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
    if Path(font).exists():
        from matplotlib import font_manager
        font_manager.fontManager.addfont(font)
        plt.rcParams['font.family']=FontProperties(fname=font).get_name()
    plt.rcParams['axes.unicode_minus']=False
    colors={'original':'#2878b5','ht':'#ed7d31'}
    labels={'original':'原TARE（同运动上限）','ht':'最新HT + 原TARE决策'}
    fig,axes=plt.subplots(2,3,figsize=(17,9),layout='constrained')
    fig.suptitle(f'同{scene}、同原生起点、各600秒：TARE 与最新HT\n单次端到端对照；近似观测自由体积并非覆盖真值')
    for i,(name,d) in enumerate(data.items()):
        rows,volume,metrics=d['rows'],d['volume'],d['external']
        t=np.array([float(r['t_s']) for r in rows]);distance=np.array([float(r['distance_m']) for r in rows])
        vt=np.array([r['time_s'] for r in volume]);v=np.array([r['observed_free_volume_m3'] for r in volume])
        c=colors[name];label=labels[name]
        axes[0,0].plot(vt/60,v,color=c,label=label)
        axes[0,1].plot(t/60,distance,color=c,label=label)
        boundaries=np.arange(0,601,60);gains=np.diff(np.interp(boundaries,vt,v))
        axes[0,2].bar(np.arange(1,11)+(i-.5)*.36,gains,width=.34,color=c,label=label)
        edges=np.arange(0,601,10);speed=np.diff(np.interp(edges,t,distance))/10
        axes[1,0].plot((edges[:-1]+5)/60,speed,color=c,label=label)
        components=[metrics['fully_stopped_fraction'],metrics['stationary_turn_fraction'],metrics['reverse_command_fraction']]
        axes[1,1].bar(np.arange(3)+(i-.5)*.36,np.array(components)*100,width=.34,color=c,label=label)
        runtimes=[float(r['planner_runtime_s']) for r in rows if r['planner_runtime_s']]
        axes[1,2].hist(runtimes,bins=np.linspace(0,2.5,51),density=True,histtype='step',color=c,label=label)
    titles=[('累计近似观测自由体积','时间/min','m³'),('实际累计里程','时间/min','m'),('每分钟新增观测','第几分钟','m³'),
            ('每10秒平均平移速度','时间/min','m/s'),('停车、转向和倒车指令占比','运动类型','%'),('TARE整个规划周期采样分布','时间/s','概率密度')]
    for ax,(title,xlabel,ylabel) in zip(axes.flat,titles):
        ax.set(title=title,xlabel=xlabel,ylabel=ylabel);ax.grid(alpha=.2);ax.legend(fontsize=8)
    axes[1,1].set_xticks(range(3),['完全停车','原地转向','倒车'])
    fig.savefig(suite/'comparison.png',dpi=160);fig.savefig(suite/'comparison.pdf');plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(12,6),layout='constrained')
    xs=[float(r['x_m']) for d in data.values() for r in d['rows']]
    ys=[float(r['y_m']) for d in data.values() for r in d['rows']]
    for ax,(name,d) in zip(axes,data.items()):
        rows=d['rows'];x=[float(r['x_m']) for r in rows];y=[float(r['y_m']) for r in rows]
        ax.plot(x,y,color=colors[name]);ax.scatter([x[0]],[y[0]],color='green',label='起点')
        ax.scatter([x[-1]],[y[-1]],color='red',label='终点')
        ax.set(title=labels[name],xlabel='X/m',ylabel='Y/m',xlim=(min(xs)-2,max(xs)+2),ylim=(min(ys)-2,max(ys)+2))
        ax.set_aspect('equal');ax.grid(alpha=.2);ax.legend()
    fig.savefig(suite/'trajectories.png',dpi=160);fig.savefig(suite/'trajectories.pdf');plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(14,8),layout='constrained')
    for name in data:
        folder=suite/name;origin=read(folder/'current/measurement_started.json')['wall_time']
        groups=[]
        for row in csv.DictReader((folder/'resources.csv').open()):
            second=float(row['wall_time'])-origin
            if not 0<=second<600:
                continue
            wall=float(row['wall_time'])
            if not groups or wall-groups[-1]['first_wall']>1:
                groups.append(dict(first_wall=wall,last_wall=wall,cpu=0.,rss=0.,rows=0))
            group=groups[-1]
            group['last_wall']=wall;group['rows']+=1
            group['rss']+=float(row['rss_mb'])
            if row['cpu_percent']:
                group['cpu']+=float(row['cpu_percent'])
        batches=[dict(time_s=g['first_wall']-origin,cpu_percent=g['cpu'],rss_mib=g['rss'],
                      process_rows=g['rows'],batch_span_s=g['last_wall']-g['first_wall']) for g in groups]
        with (folder/'resource_batches.csv').open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(batches[0]),lineterminator='\n');writer.writeheader();writer.writerows(batches)
        t=[b['time_s'] for b in batches];c=colors[name];label=labels[name]
        axes[0,0].plot(np.array(t)/60,[b['cpu_percent'] for b in batches],label=label,color=c,linewidth=.8)
        axes[0,1].plot(np.array(t)/60,[b['rss_mib'] for b in batches],label=label,color=c,linewidth=.8)
        health=[r for r in csv.DictReader((folder/'health.csv').open()) if 0<=float(r['wall_time'])-origin<600]
        ht=np.array([float(r['wall_time'])-origin for r in health])/60
        scan=np.array([float(r['scan_source_age_s']) if r['scan_source_age_s'] else np.nan for r in health])
        axes[1,0].plot(ht,scan,label=label,color=c,linewidth=.8)
        if name=='ht':
            age=np.array([float(r['map_source_age_s']) if r['map_source_age_s'] else np.nan for r in health])
            axes[1,1].plot(ht,age,label='HT地图源时间年龄',color=c,linewidth=.8)
    axes[1,1].axhline(3,color='red',linestyle='--',label='3秒新鲜度上限')
    axes[1,1].text(.02,.92,'原TARE不使用HT地图，无对应地图年龄',transform=axes[1,1].transAxes,fontsize=9)
    for ax,title,ylabel in zip(axes.flat,['全部试验进程组CPU','全部试验进程组RSS','激光源时间年龄','仅HT地图时间年龄'],['%（100%=一核）','MiB（共享页可能重复）','秒','秒']):
        ax.set(title=title,xlabel='时间/min',ylabel=ylabel);ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.savefig(suite/'resources_comparison.png',dpi=160);fig.savefig(suite/'resources_comparison.pdf');plt.close(fig)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    job=read(a.state);suite=Path(job['suite']);out=Path(job['archive']);encoder=job['encoder']
    state=read(suite/'suite.json')
    stage=int(job.get('stage',47));scene=job.get('scene',state.get('scene','indoor'))
    if scene!=state.get('scene',scene):
        raise RuntimeError('Scenario differs between job and recorded suite')
    if state['state']!='MEASUREMENTS_COMPLETE':
        raise RuntimeError('Both actual measurements must finish; preserve interrupted state')
    if out.exists():
        raise RuntimeError('Refusing to overwrite selected archive '+str(out))
    for label in ['original','ht']:
        link=suite/label/'current_bag'
        if link.is_symlink():
            if link.resolve()!=(suite/label/'evidence_bag').resolve():
                raise RuntimeError('Unexpected recording alias '+str(link))
            link.unlink()
        elif link.exists():
            raise RuntimeError('Recording alias is an actual path '+str(link))
        link.symlink_to('evidence_bag',target_is_directory=True)
    run([sys.executable,ROOT/'presentations/summarize_ht_endurance.py',suite/'ht'],suite/'ht/analysis.log')
    original_reader=common.reader
    def sampled_reader(path, topics):
        return original_reader(path,['/endurance/registered_scan' if t=='/registered_scan' else t for t in topics])
    common.reader=sampled_reader
    data={}
    for row in state['runs']:
        name=row['scenario'];folder=suite/name
        if not (folder/'current_bag').exists():
            (folder/'current_bag').symlink_to(folder/'evidence_bag',target_is_directory=True)
        if name=='ht':
            # The unchanged endurance analysis above already uses the same
            # source-second evaluator; don't process its600 scans twice.
            rows=list(csv.DictReader((folder/'current/timeseries.csv').open()))
            volume=[{k:float(v) for k,v in r.items()} for r in csv.DictReader((folder/'current/observation_volume.csv').open())]
            external=read(folder/'current/external_metrics.json')
        else:
            rows,volume,external=common.evaluate(folder,'current',600,scan_selection='source_second')
        video(folder,encoder,name=='original')
        motion=motion_audit(folder)
        checks=collection(folder,name=='original',motion)
        summary=read(folder/'summary.json')
        mission=('EXPLORATION_FINISH_TRIGGERED' if summary['exploration_finished'] else 'EXPLORING') if name=='original' else read(folder/'endurance_audit.json')['mission_audit']['last_sampled_mission']
        row.update(state='RECORDED' if all(checks.values()) else 'VALIDATION_FAILED',checks=checks,
                   metrics=dict(distance_m=summary['distance_m'],observed_free_volume_m3=external['observed_free_volume_m3'],mission=mission))
        data[name]=dict(rows=rows,volume=volume,external=external,summary=summary,motion=motion,checks=checks,mission=mission)
    params=parameter_audit(suite)
    first=data['original']['summary']['start_pose_xyyaw'];second=data['ht']['summary']['start_pose_xyyaw']
    start_distance=math.dist(first[:2],second[:2]);start_yaw=abs(math.atan2(math.sin(first[2]-second[2]),math.cos(first[2]-second[2])))
    paired=dict(start_distance_m=start_distance,start_yaw_difference_rad=start_yaw,parameter_checks=params,
                start_position_pass=start_distance<=.05,start_yaw_pass=start_yaw<=.02)
    write(suite/'paired_validation.json',paired)
    state['state']='COMPLETED' if all(r['state']=='RECORDED' for r in state['runs']) and all(params.values()) and paired['start_position_pass'] and paired['start_yaw_pass'] else 'COMPLETED_WITH_ISSUES'
    write(suite/'suite.json',state);write(suite/'FINISHED.json',state)
    plots(suite,data,scene)
    concise={name:{k:v for k,v in d.items() if k not in ('rows','volume')} for name,d in data.items()}
    write(suite/'comparison_metrics.json',concise)
    grids=read(suite/'effective_parameter_comparison.json')['viewpoint_grids']
    def grid_description(name):
        g=grids[name]
        return (f"{g['number_x']}×{g['number_y']}，间距{g['resolution_x']:g}×{g['resolution_y']:g}m，"
                f"名义{g['number_x']*g['resolution_x']:g}×{g['number_y']*g['resolution_y']:g}m")
    lines=[f'# 阶段{stage}：原TARE与最新HT，同运动上限{scene}600秒对照','',
        f"试验设施冻结`{job['candidate_commit']}`；HT导航保持`{job['navigation_control_commit']}`，原TARE ROS2适配基线`{job['upstream_commit']}`。每组独立重启同一{scene}原生起点，顺序原TARE→HT，均实际600秒。",'',
        '原TARE保留自身探索/TSP与CMU规划器；原CMU参数对齐角速度和线加速度，并用透明限幅组件对齐倒车速度/角加速度，限幅前后指令均已记录。前进0.5、倒车0.25m/s，角速度0.8rad/s，常规线/角加速度0.5m/s²、1.2rad/s²。显式全零/输入过期可立即停止。CMU原maxSpeed=2.0的内部归一化配置保留，但autonomySpeed=0.5，实际输出另有共同限幅，并非以2m/s开车。两套地形、几何安全规则与跟踪器仍不同，是端到端对照，不是HT单模块消融。','',
        '| 指标 | 原TARE（对齐运动上限） | 最新HT |','|---|---:|---:|']
    specs=[('实际里程/m','distance_m','summary'),('近似观测自由体积/m³','observed_free_volume_m3','external'),
        ('最后60秒里程/m','distance_last60_m','external'),('最长完全停车/s','longest_zero_command_s','external'),
        ('完全停车比例','fully_stopped_fraction','external'),('原地转向比例','stationary_turn_fraction','external'),
        ('倒车指令比例','reverse_command_fraction','external'),('规划周期P95/s','planner_runtime_p95_s','summary')]
    for label,key,source in specs:
        values=[data[n][source][key] for n in ['original','ht']]
        lines.append('| '+label+' | '+' | '.join(f'{v:.2%}' if key.endswith('fraction') else f'{v:.3f}' for v in values)+' |')
    lines+=['| 末任务 | '+data['original']['mission']+' | '+data['ht']['mission']+' |',
        '| 视点网格 | '+grid_description('original')+' | '+grid_description('ht')+' |','',
        f"本次HT/原TARE体积比={data['ht']['external']['observed_free_volume_m3']/data['original']['external']['observed_free_volume_m3']:.3f}，里程比={data['ht']['summary']['distance_m']/data['original']['summary']['distance_m']:.3f}。仅该次运行描述，不代表统计优越。",'',
        '![累计体积、增量、里程、速度、运动组成和规划周期](comparison.png)','',
        '![同尺度实际轨迹](trajectories.png)','',
        '![CPU、内存、激光与HT地图年龄](resources_comparison.png)','',
        f"起点差{start_distance:.6f}m、航向差{start_yaw:.6f}rad；配对/参数/实际指令/视频/采集检查分别保存在paired_validation.json、effective_parameter_comparison.json和逐组审计。总体状态：{state['state']}。",'',
        '## 视频与数据','',
        '[原TARE 10分钟视频](original/camera_h264.mp4) · [最新HT 10分钟视频](ht/camera_h264.mp4)','',
        '![原TARE末段实际环境](original/late_camera.jpg)','', '![HT末段实际环境](ht/late_camera.jpg)','',
        '## 口径与限制','',
        '- 每秒按绝对源秒取一帧真实地图坐标激光，使用相同sensor里程计原点；0.5m自由体素并集、0.25m射线步长、15m截断、回波前0.25m排除。这是近似观测量，不是真值覆盖率。',
        '- 原TARE完成信号只表示原生返航触发，不能拿它当HT的COMPLETED到家驻留状态，也不证明真实全覆盖。',
        '- 两个系统各一次，固定运行顺序，探索随机性和初始化/感知/控制差异未统计消除；限幅后的原TARE不是原CMU默认高速控制链。',
        '- 本场景实际视点网格见上表及effective_parameter_comparison.json；没有沿用室内配置的网格说明。即使采样密度相同，感知、几何与控制链仍不同，不能把差距单独归因于HT。',
        '- 记录保留全部发布控制/odom/状态/路线；激光源秒采样、HT输入/地图按既有策略，不是全部原始传感器全频无损录包。',
        '- 本轮没有修改HT导航；本次对照不同时验证森林、隧道或实车。', '',
        f'完整数据以docs/experiments/publications/stage{stage}.json远端大小/SHA回执为准，报告存在不等于已发布。']
    (suite/'REPORT.md').write_text('\n'.join(lines)+'\n')
    out.mkdir(parents=True)
    root_files=['REPORT.md','comparison_metrics.json','comparison.png','comparison.pdf','trajectories.png','trajectories.pdf','resources_comparison.png','resources_comparison.pdf',
                'suite.json','FINISHED.json','paired_validation.json','effective_parameter_comparison.json']
    for name in root_files:
        shutil.copy2(suite/name,out/name)
    for row in state['runs']:
        name=row['scenario'];src=suite/name;dst=out/name;dst.mkdir()
        for p in src.iterdir():
            if p.is_file() and (p.suffix in ('.json','.yaml','.xml') or p.name in ('camera_h264.mp4','late_camera.jpg')):
                shutil.copy2(p,dst/p.name)
        (dst/'current').mkdir()
        for name2 in ['timeseries.csv','observation_volume.csv','external_metrics.json','summary.json','measurement_started.json','shutdown.json']:
            shutil.copy2(src/'current'/name2,dst/'current'/name2)
        shutil.copy2(src/'health.csv',dst/'health.csv')
        shutil.copy2(src/'resources.csv',dst/'resources.csv')
        shutil.copy2(src/'resource_batches.csv',dst/'resource_batches.csv')
    for script in ['run_matched_tare_comparison.py','run_matched_tare_original.py','comparison_motion_limits.py','finalize_matched_tare_comparison.py']:
        shutil.copy2(Path(__file__).with_name(script),out/script)
    shutil.copy2(a.state,out/'frozen_job.json')
    write(out/'files_sha256.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()})
    print(json.dumps(dict(state=state['state'],original=concise['original']['external'],ht=concise['ht']['external']),indent=2))


if __name__=='__main__':
    main()
