#!/usr/bin/env python3
"""Apply one external observation metric to both recorded exploration systems."""
import argparse
import collections
import csv
import json
import math
from pathlib import Path

import cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py import point_cloud2
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String


def reader(path,topics):
    r=rosbag2_py.SequentialReader()
    r.open(rosbag2_py.StorageOptions(uri=str(path),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    r.set_filter(rosbag2_py.StorageFilter(topics=topics))
    return r


def stamp(m):return m.header.stamp.sec+m.header.stamp.nanosec*1e-9


def pack(cells):
    v=cells.astype(np.int64)+(1<<20)
    if np.any(v<0) or np.any(v>=(1<<21)):raise ValueError('Voxel coordinates out of range')
    return (v[:,0]<<42)|(v[:,1]<<21)|v[:,2]


def evaluate(folder,name,duration):
    trial=folder/name;origin=json.loads((trial/'measurement_started.json').read_text())['wall_time']
    rows=list(csv.DictReader((trial/'timeseries.csv').open()))
    times=np.array([float(r['t_s']) for r in rows]);dist=np.array([float(r['distance_m']) for r in rows])
    poses=[];at_scan=[];commands=[];states=collections.Counter();r=reader(folder/(name+'_bag'),['/state_estimation','/state_estimation_at_scan','/cmd_vel','/ht_follower_status'])
    while r.has_next():
        topic,data,ns=r.read_next();t=ns/1e9-origin
        if topic in ['/state_estimation','/state_estimation_at_scan']:
            m=deserialize_message(data,Odometry)
            if topic=='/state_estimation' and m.child_frame_id!='sensor':
                raise ValueError('Common ray origin requires sensor-frame odometry')
            p=m.pose.pose.position
            (at_scan if topic.endswith('_at_scan') else poses).append((stamp(m),p.x,p.y,p.z))
        elif 0<=t<duration:
            if topic=='/cmd_vel':
                m=deserialize_message(data,TwistStamped);commands.append((t,m.twist.linear.x,m.twist.angular.z))
            else:states.update([deserialize_message(data,String).data])
    # Use the same dense sensor-frame odometry in both systems. The optional
    # scan-generation node can drop synchronized outputs; preferring that
    # sparse topic would discard different observation bins in the two runs.
    positions=np.array(sorted(poses));source='nearest sensor-frame state_estimation (common to both systems)'
    if len(positions)==0:raise ValueError('Missing sensor positions')
    free=set();surface=set();volume=[{'time_s':0.,'observed_free_volume_m3':0.,'distance_m':0.,'free_voxels':0,'scans':0}]
    processed=0;skipped=0;last_bin=-1;pose_offsets=[];scans_recorded=0
    r=reader(folder/(name+'_bag'),['/registered_scan']);steps=np.arange(0,15,.25,dtype=np.float32)
    while r.has_next():
        _,data,ns=r.read_next();m=deserialize_message(data,PointCloud2);t=stamp(m)-origin
        if not 0<=t<duration:continue
        scans_recorded+=1;bin_id=int(math.floor(t))
        if bin_id==last_bin:continue
        last_bin=bin_id
        if m.header.frame_id!='map':raise ValueError('Expected registered cloud in map frame')
        j=int(np.searchsorted(positions[:,0],stamp(m)));j=min(range(max(0,j-1),min(len(positions),j+1)),key=lambda j:abs(positions[j,0]-stamp(m)))
        offset=abs(positions[j,0]-stamp(m))
        if offset>.15:skipped+=1;continue
        sensor=positions[j,1:].astype(np.float32)
        xyz=np.asarray(point_cloud2.read_points_numpy(m,field_names=('x','y','z'),skip_nans=True),np.float32)
        rays=xyz-sensor;length=np.linalg.norm(rays,axis=1);ok=np.isfinite(length)&(length>=.5);rays,xyz,length=rays[ok],xyz[ok],length[ok]
        if not len(rays):skipped+=1;continue
        endpoint=np.floor(xyz/.5).astype(np.int64);_,unique=np.unique(pack(endpoint),return_index=True)
        rays,length=rays[unique],length[unique];direction=rays/length[:,None]
        # 0.25m ray samples estimate the union of observed free 0.5m voxels.
        # Distant returns are clipped to15m; a0.25m endpoint band is excluded.
        limits=np.minimum(15.,length-.25);samples=sensor+direction[:,None,:]*steps[None,:,None]
        cells=np.floor(samples[steps[None,:]<limits[:,None]]/.5).astype(np.int64)
        free.update(np.unique(pack(cells)).tolist());surface.update(np.unique(pack(endpoint)).tolist())
        processed+=1;pose_offsets.append(offset)
        volume.append({'time_s':float(t),'observed_free_volume_m3':len(free)*.125,
                       'distance_m':float(np.interp(t,times,dist)),'free_voxels':len(free),'scans':processed})
    volume.append(dict(volume[-1],time_s=float(duration),distance_m=float(dist[-1])))
    with (trial/'observation_volume.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(volume[0]));w.writeheader();w.writerows(volume)
    zero=sum(abs(v)<.01 and abs(w)<.05 for _,v,w in commands)
    turn=sum(abs(v)<.01 and abs(w)>.05 for _,v,w in commands)
    first=None;last=None;longest=0
    for t,v,w in commands:
        if abs(v)<.01 and abs(w)<.05:
            if first is None:first=t
            last=t
        elif first is not None:longest=max(longest,last-first+.05);first=None
    if first is not None:longest=max(longest,duration-first)
    no_translation_first=None;no_translation_last=None;longest_no_translation=0
    for t,v,w in commands:
        if abs(v)<.01:
            if no_translation_first is None:no_translation_first=t
            no_translation_last=t
        elif no_translation_first is not None:
            longest_no_translation=max(longest_no_translation,no_translation_last-no_translation_first+.05)
            no_translation_first=None
    if no_translation_first is not None:longest_no_translation=max(longest_no_translation,duration-no_translation_first)
    moving=np.flatnonzero(np.diff(dist)>.005)
    result={'observed_free_volume_m3':len(free)*.125,'processed_volume_scans':processed,
            'skipped_volume_scans':skipped,'recorded_scans_in_source_time_window':scans_recorded,
            'sensor_position_source':source,'pose_time_offset_max_s':max(pose_offsets,default=None),
            'command_samples':len(commands),'fully_stopped_fraction':zero/max(1,len(commands)),
            'stationary_turn_fraction':turn/max(1,len(commands)),
            'reverse_command_fraction':sum(v<-.05 for _,v,_ in commands)/max(1,len(commands)),
            'max_abs_linear_command_mps':max((abs(v) for _,v,_ in commands),default=0),
            'max_abs_yaw_command_rps':max((abs(w) for _,_,w in commands),default=0),
            'longest_zero_command_s':longest,'follower_status_samples':dict(states),
            'longest_no_translation_command_s':longest_no_translation,
            'last_translation_s':float(times[moving[-1]+1]) if len(moving) else 0.,
            'distance_last60_m':float(dist[-1]-np.interp(duration-60,times,dist))}
    (trial/'external_metrics.json').write_text(json.dumps(result,indent=2)+'\n')
    return rows,volume,result


def main():
    ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);a=ap.parse_args();folder=a.folder.resolve()
    pair=json.loads((folder/'pair_summary.json').read_text());duration=pair['current']['duration_s'];data={}
    for name in ['original','current']:data[name]=evaluate(folder,name,duration)
    metrics={name:values[2] for name,values in data.items()}
    (folder/'external_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    definition={'voxel_size_m':.5,'ray_sample_step_m':.25,'max_range_m':15.,'scan_selection':'first source-stamped scan in each1s measurement bin',
                'endpoint_exclusion_m':.25,'sensor_pose_max_time_offset_s':.15,
                'definition':'Approximate cumulative union of free voxels observed along registered lidar rays. Not TARE official coverage, ground-truth explored volume, or vehicle footprint area.'}
    (folder/'metric_definition.json').write_text(json.dumps(definition,indent=2)+'\n')
    fig,axes=plt.subplots(2,3,figsize=(15,8.5),layout='constrained');colors={'original':'#2878b5','current':'#ed7d31'}
    for name,label in [('original','Original TARE'),('current','Current HT + XYtheta')]:
        rows,volume,m=data[name];c=colors[name];t=np.array([float(r['t_s']) for r in rows]);d=np.array([float(r['distance_m']) for r in rows]);vt=np.array([r['time_s'] for r in volume]);v=np.array([r['observed_free_volume_m3'] for r in volume]);vd=np.array([r['distance_m'] for r in volume])
        axes[0,0].plot(vt,v,label=label,color=c);axes[0,1].plot(t,d,label=label,color=c);axes[0,2].plot(vd,v,label=label,color=c)
        axes[1,0].plot([float(r['x_m']) for r in rows],[float(r['y_m']) for r in rows],label=label,color=c)
        x=0 if name=='original' else 1;axes[1,1].bar(x,100*m['fully_stopped_fraction'],color=c);axes[1,1].text(x,100*m['fully_stopped_fraction']+.5,f"{100*m['fully_stopped_fraction']:.1f}%",ha='center')
        axes[1,2].bar(x,pair[name]['planner_runtime_median_s'],color=c)
    axes[0,0].set(title='Observed free-space volume (external estimate)',xlabel='Time(s)',ylabel='Volume(m3)');axes[0,1].set(title='Actual travel distance',xlabel='Time(s)',ylabel='Distance(m)');axes[0,2].set(title='Observation gain versus travel',xlabel='Distance(m)',ylabel='Volume(m3)');axes[1,0].set(title='Actual vehicle trajectories',xlabel='World X(m)',ylabel='World Y(m)');axes[1,0].set_aspect('equal',adjustable='datalim')
    axes[1,1].set(title='Fully stopped commands',ylabel='Control samples(%)',xticks=[0,1],xticklabels=['TARE','HT']);axes[1,2].set(title='Reported TARE planning runtime (median)',ylabel='Seconds',xticks=[0,1],xticklabels=['TARE','HT'])
    axes[1,1].set_ylim(0,max(m['fully_stopped_fraction']*100 for m in metrics.values())*1.2+1)
    for ax in axes.flat:ax.grid(alpha=.2)
    for ax in axes[0]:ax.legend(fontsize=8)
    axes[1,0].legend(fontsize=8);fig.savefig(folder/'comparison.png',dpi=175);plt.close(fig)
    lines=['# 原版TARE与当前HT：Garage配对实验','',f'每组{duration:.0f}秒，分别重启同一Garage环境、预定位姿和0.5m/s前进上限。',
           '原版使用自身路径规划及CMU局部规划/跟踪；当前版使用CuPy历史高程、HT硬约束、XYtheta规划和独立跟踪器。这是端到端系统比较。','',
           '| 指标 | 原版TARE | 当前HT |','| --- | ---: | ---: |']
    for title,key,external in [('行驶距离(m)','distance_m',False),('估计累计观测自由空间(m³)','observed_free_volume_m3',True),('到访1米轨迹格','visited_1m_xy_cells',False),('完全停车比例','fully_stopped_fraction',True),('原地转向比例','stationary_turn_fraction',True),('倒车指令比例','reverse_command_fraction',True),('最长连续线/角速度均近零指令(s)','longest_zero_command_s',True),('最长连续不平移指令(含转向，s)','longest_no_translation_command_s',True),('最后60秒行驶距离(m)','distance_last60_m',True),('实际最大线速度指令(m/s)','max_abs_linear_command_mps',True),('实际最大角速度指令(rad/s)','max_abs_yaw_command_rps',True),('TARE运行时间中位数(s)','planner_runtime_median_s',False),('TARE运行时间P95(s)','planner_runtime_p95_s',False)]:
        vals=[]
        for name in ['original','current']:
            value=(metrics[name] if external else pair[name])[key];vals.append(f'{100*value:.2f}%' if key.endswith('_fraction') else f'{value:.3f}')
        lines.append('| '+title+' | '+' | '.join(vals)+' |')
    distance_ratio=pair['current']['distance_m']/pair['original']['distance_m']
    volume_ratio=metrics['current']['observed_free_volume_m3']/metrics['original']['observed_free_volume_m3']
    lines+=['','![对比图](comparison.png)','',
            f"本轮当前HT的估计观测自由空间为原版的{100*volume_ratio:.1f}%，行驶距离为{100*distance_ratio:.1f}%。原版继续向远处推进，当前HT有更多原地转向、完全停车和已知区域回访，后段观测增益趋平。因此本轮原版整体探索效率更高；不能只凭HT不再长时间卡住就认为已追平原版。",'',
            '“完全停车”同时检查线速度和角速度；“不平移”还包括原地转向，后者会使里程曲线暂时变平。两者不能混用。','',
            '## 观测体积口径','',
            '两组使用相同外部算法：每秒取一帧原始地图坐标点云，配对激光位置，沿有效回波光线采样0.5米体素的自由空间并取历史并集，距离截断15米，排除回波终点附近0.25米。ray采样间隔0.25米，因此该体积为近似估计。',
            '该数值不是TARE官方覆盖率、真值探索体积或车辆已走过面积。相同区域重复行驶不会重复增加并集体积；两条路径即使路程接近，也可能观测到不同新空间。','',
            '## 控制器参数差异','',
            '相同的是0.5m/s自主行驶目标/前进速度上限，并非全部运动约束相同。原版CMU控制器允许约0.5m/s倒车、最大转速90°/s(1.571rad/s)、最大加速度2.5m/s²；当前HT跟踪器倒车上限0.25m/s、转速0.8rad/s、加速度0.5m/s²。原版launch中的maxSpeed仍为2.0m/s，但autonomySpeed设置为0.5m/s，实际命令峰值见上表。',
            '原版保留自己的双向跟踪策略，可能长距离倒着开；当前版使用自己的运动时间代价与跟踪器。这里比较原版控制链路与当前完整系统，不是控制器参数完全对齐的单模块消融实验。','',
            '## 限制与原始数据','',
            '每个版本仅一次独立运行，探索具有随机性。两个系统控制器、感知堆栈与初始化过程不同，不能将差异全归于HT单模块。两组规划/runtime指标不包含所有感知与控制耗时。',
            f"探索完成信号：原版{pair['original']['exploration_finished']}，当前{pair['current']['exploration_finished']}；180秒按预设时间停止，不代表探索结束。",'',
            '原始数据：`original/`、`current/`下的`timeseries.csv`、`observation_volume.csv`、`summary.json`及`external_metrics.json`；录包在`original_bag/`、`current_bag/`。',
            '配置与提交记录见`manifest.json`，预定位姿见各组`stage.json`。']
    if (folder/'elevation_display_explained.png').exists():
        lines+=['','## 左下角为什么显得模糊','',
                '视频左下角是历史局部高程图。291×291格覆盖约11.91×11.91米，每格4.09厘米，显示到600像素时每格约2.06像素。示例帧用几乎整个色谱表示约0～15厘米高程，微小起伏被放大；约30%格子无数据，形成灰色空洞与碎斑。图像使用最近邻绘制。',
                '下面只改变色阶并放大栅格，没有补出未知地形，也没有改变规划输入。','',
                '![高程原显示、固定色阶与局部栅格放大](elevation_display_explained.png)']
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n');print(json.dumps(metrics,indent=2))


if __name__=='__main__':main()
