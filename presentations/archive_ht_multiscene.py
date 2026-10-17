#!/usr/bin/env python3
"""Export actual completed multi-scene recordings and their measured evidence."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import cv2

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap,BoundaryNorm
from matplotlib.patches import Patch
import numpy as np

from run_ht_multiscene import SCENES,NAMES


def read_json(path):return json.loads(path.read_text())


def save_ht_snapshot(src,dst,scene,duration):
    """Show actual directional fields without interpolation or invented paths."""
    origin=read_json(src/'current/measurement_started.json')['wall_time']
    index=read_json(src/'snapshots/index.json')['frames']
    frames=[f for f in index if origin<=f['ht_stamp']<=origin+duration]
    if not frames:raise RuntimeError('No in-window HT snapshot for '+scene)
    frame=min(frames,key=lambda f:abs(f['ht_stamp']-(origin+duration-10)))
    shutil.copy2(src/'snapshots'/frame['file'],dst/'late_map_snapshot.npz')
    with np.load(dst/'late_map_snapshot.npz',allow_pickle=False) as data:
        robot=data['robot'];cx,cy,res=data['ht_geometry'];n,m=data['ht_ht_valid'].shape
        extent=(cx-n*res/2,cx+n*res/2,cy-m*res/2,cy+m*res/2)
        cmap=plt.get_cmap('RdYlGn').copy();cmap.set_bad('#bfc3c6')
        fig,axes=plt.subplots(2,4,figsize=(15,8),layout='constrained')
        for k,axis in enumerate(axes.flat):
            z=np.where(data['ht_ht_valid']>=.5,data[f'ht_ht_dir_{k}'],np.nan)
            im=axis.imshow(z[::-1,::-1].T,origin='lower',extent=extent,cmap=cmap,vmin=0,vmax=1,interpolation='nearest')
            axis.plot(*robot[:2],'b+',ms=7)
            axis.set(title=f'HT 通道 {k}',xlabel='X / m',ylabel='Y / m')
        fig.colorbar(im,ax=axes,label='可通过概率（灰色为无有效支撑）')
        fig.suptitle(f'{NAMES[scene]}：t={frame["ht_stamp"]-origin:.1f}s 的实际八方向HT；蓝十字为车辆位置\n概率图不包含车体扫掠检查及地图时效判断；通道编号不替代物理角度标定')
        fig.savefig(dst/'late_ht.png',dpi=140);plt.close(fig)
        # Mirror HtCostMap's hard footprint gate for this recorded protocol:
        # 0.6m support radius plus its sqrt(2)*resolution raster margin.
        valid=data['ht_ht_valid']>=.5;radius=int(np.ceil(.6/res)+1)
        ii,jj=np.mgrid[-radius:radius+1,-radius:radius+1]
        kernel=(np.hypot(ii,jj)*res<=.6+np.sqrt(2)*res).astype('uint8')
        unknown=cv2.dilate((~valid).astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=1).astype(bool)
        support_cmap=ListedColormap(['#bfc3c6','#16854a','#c93335'])
        fig,axes=plt.subplots(2,4,figsize=(15,8),layout='constrained')
        home=read_json(src/'summary.json')['start_pose_xyyaw']
        for k,axis in enumerate(axes.flat):
            blocked=cv2.dilate((valid&(data[f'ht_ht_dir_{k}']<.5)).astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=0).astype(bool)
            status=np.where(blocked,2,np.where(unknown,0,1))
            axis.imshow(status[::-1,::-1].T,origin='lower',extent=extent,cmap=support_cmap,norm=BoundaryNorm([-.5,.5,1.5,2.5],3),interpolation='nearest')
            axis.plot(*robot[:2],'b+',ms=7)
            if extent[0]<=home[0]<=extent[1] and extent[2]<=home[1]<=extent[3]:axis.plot(*home[:2],'*',color='#f5bc00',ms=9)
            axis.set(title=f'HT 通道 {k}',xlabel='X / m',ylabel='Y / m')
        fig.legend(handles=[Patch(color='#16854a',label='足迹HT允许'),Patch(color='#c93335',label='足迹包含低概率格'),Patch(color='#bfc3c6',label='足迹包含未知格')],loc='lower center',bbox_to_anchor=(.5,-.04),ncol=3)
        fig.suptitle(f'{NAMES[scene]}：同一快照的HT足迹硬门槛，半径0.6m，概率阈值0.5\n蓝十字为车辆，黄星为初始位置（若在图内）；另有几何、时效与运动约束')
        fig.savefig(dst/'late_ht_footprint.png',dpi=140,bbox_inches='tight');plt.close(fig)
        cv2.imwrite(str(dst/'late_camera.jpg'),data['camera'])
    (dst/'late_map_snapshot.json').write_text(json.dumps(dict(**frame,
        measurement_time_s=frame['ht_stamp']-origin,source_file=str(src/'snapshots'/frame['file']),
        camera_alignment='latest received camera at capture time, not exact source-time synchronization'),ensure_ascii=False,indent=2)+'\n')


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('job',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--scenarios',nargs='+',choices=SCENES,default=list(SCENES),
                    help='Expected completed recordings; default requires all five scenes')
    args=ap.parse_args();job=args.job.resolve();out=args.output.resolve()
    state=read_json(job/'FINISHED.json')
    if out.exists():raise RuntimeError('Refusing to overwrite '+str(out))
    if len(set(args.scenarios))!=len(args.scenarios) or len(state['runs'])!=len(args.scenarios) or {r['scenario'] for r in state['runs']}!=set(args.scenarios):
        raise RuntimeError('Missing/duplicate scene recordings: expected '+str(args.scenarios))
    for row in state['runs']:
        if not row.get('video_ok'):raise RuntimeError('Video not validated: '+row['scenario'])
        video=read_json(job/row['scenario']/'video_validation.json')
        if not video.get('duration_matches') or video.get('full_decode_returncode')!=0:
            raise RuntimeError('Video duration/decode validation failed')
    temp=out.with_name(out.name+'.staging')
    temp.mkdir(parents=True,exist_ok=False)
    for name in ('REPORT.md','suite.json','FINISHED.json','videos.m3u','overview.jpg'):
        shutil.copy2(job/name,temp/name)
    plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})
    summaries={};shared_hashes=None;audits={}
    for row in state['runs']:
        scene=row['scenario'];src=job/scene;dst=temp/scene;dst.mkdir()
        names=('camera_h264.mp4','preview.jpg','preview_0.jpg','preview_1.jpg','preview_2.jpg',
               'REPORT.md','manifest.json','suite_validation.json','summary.json','video_validation.json',
               'probe_summary.json','mission_audit.json','endurance_audit.json','input_delivery_audit.json',
               'target_selection_audit.json','metric_definition.json','ten_minute_segments.csv',
               'health.csv','resources.csv','mapper_checkpoints.jsonl','COMPLETED.json',
               'ANALYSIS_COMPLETED.json','working_tree.patch','run_ht_endurance.py','endurance_probe.py',
               'effective_parameters.json',
               'stability.png','performance.png')
        for name in names:
            if (src/name).exists():shutil.copy2(src/name,dst/name)
        for source,name in [('current/timeseries.csv','timeseries.csv'),
                            ('current/observation_volume.csv','observation_volume.csv'),
                            ('current/shutdown.json','shutdown.json'),
                            ('current/ht_cpu_threads.json','ht_cpu_threads.json'),
                            ('current/cupy_processing_stats.json','cupy_processing_stats.json')]:
            if (src/source).exists():shutil.copy2(src/source,dst/name)
        hashes=read_json(src/'manifest.json')['source_hashes']
        configs=dst/'frozen_inputs';configs.mkdir();config_index={}
        for path,value in hashes.items():
            source_path=Path(path)
            if source_path.suffix not in ('.yaml','.yml','.sdf','.world'):continue
            if hashlib.sha256(source_path.read_bytes()).hexdigest()!=value:
                raise RuntimeError('Frozen input changed before export: '+path)
            name=f'{len(config_index):02d}_'+source_path.name
            shutil.copy2(source_path,configs/name)
            config_index[name]=dict(source_path=path,sha256=value)
        (configs/'index.json').write_text(json.dumps(config_index,ensure_ascii=False,indent=2)+'\n')
        if shared_hashes is None:shared_hashes=hashes.copy()
        else:
            shared_hashes={key:value for key,value in shared_hashes.items() if key in hashes and hashes[key]==value}
        summaries[scene]=dict(**row['metrics'],checks=row['checks'],video=read_json(src/'video_validation.json'))
        audits[scene]=read_json(src/'endurance_audit.json')
        save_ht_snapshot(src,dst,scene,state['duration_s'])
        if (src/'diagnostics').is_dir():shutil.copytree(src/'diagnostics',dst/'diagnostics')
    # Verify the common control/recording files were identical across all runs;
    # world files and scene-specific profiles are intentionally different.
    first=read_json(job/state['runs'][0]['scenario']/'manifest.json')['source_hashes']
    common=set(first)
    manifests=[read_json(job/r['scenario']/'manifest.json')['source_hashes'] for r in state['runs']]
    for manifest in manifests:common &= manifest.keys()
    unequal=[key for key in common if len({manifest[key] for manifest in manifests})!=1]
    if unequal:raise RuntimeError('Common control sources changed across scenes: '+str(unequal))
    fig,axes=plt.subplots(1,2,figsize=(13,5),layout='constrained')
    trajectories,tx=plt.subplots(1,len(state['runs']),figsize=(max(5,3.6*len(state['runs'])),4),layout='constrained')
    for row,axis in zip(state['runs'],np.atleast_1d(tx)):
        scene=row['scenario']
        with (temp/scene/'timeseries.csv').open() as f:motion=list(csv.DictReader(f))
        t=np.asarray([float(r['t_s']) for r in motion]);distance=np.asarray([float(r['distance_m']) for r in motion])
        x=np.asarray([float(r['x_m']) for r in motion]);y=np.asarray([float(r['y_m']) for r in motion])
        axes[1].plot(t/60,distance,label=NAMES[scene])
        path=temp/scene/'observation_volume.csv'
        if path.exists():
            with path.open() as f:volume=list(csv.DictReader(f))
            axes[0].plot([float(r['time_s'])/60 for r in volume],
                         [float(r['observed_free_volume_m3']) for r in volume],label=NAMES[scene])
        axis.plot(x,y,linewidth=1);axis.scatter([x[0],x[-1]],[y[0],y[-1]],c=['green','red'],s=24)
        axis.set(title=NAMES[scene],xlabel='X / m',ylabel='Y / m');axis.grid(alpha=.2);axis.set_aspect('equal',adjustable='datalim')
    axes[0].set(title='累计观测自由体积（近似）',ylabel='m³',xlabel='时间 / 分钟')
    axes[1].set(title='实际里程',ylabel='m',xlabel='时间 / 分钟')
    for axis in axes:axis.grid(alpha=.2);axis.legend();axis.set_xlim(0,state['duration_s']/60)
    fig.suptitle('同一HT在不同环境：不同起点和场景，不能作算法优劣排名' if len(state['runs'])>1 else '单环境补测：实际观测体积与里程')
    fig.savefig(temp/'scene_metrics.png',dpi=160);plt.close(fig)
    trajectories.suptitle('实际里程计轨迹：绿点为起点，红点为结束位置')
    trajectories.savefig(temp/'trajectories.png',dpi=160);plt.close(trajectories)
    with (temp/'REPORT.md').open('a') as report:
        report.write('\n## 实际出现的问题\n\n')
        report.write('下表保留暂停和地图延迟，不把“节点未崩溃”当作“没有问题”。地图年龄为1Hz抽样，完整控制消息保留在本地MCAP中。全零指令表示既不平移也不转向；原地转向单独统计。\n\n')
        report.write('| 环境 | HT年龄P95/最大(s) | 年龄>3s样本 | 全零指令占比 | 最长全零指令(s) | 全局引导无进展释放 | 验证失败项 |\n|---|---:|---:|---:|---:|---:|---|\n')
        for row in state['runs']:
            scene=row['scenario'];audit=audits[scene];age=audit['sampled_map_age_s'];metrics=audit.get('external_metrics') or {}
            failed=', '.join(k for k,v in row['checks'].items() if not v) or '无'
            report.write(f'| {NAMES[scene]} | {age["p95"]:.2f} / {age["max"]:.2f} | {audit["map_age_over3s_samples"]} | {metrics.get("fully_stopped_fraction",0):.1%} | {metrics.get("longest_zero_command_s",0):.2f} | {audit["target_selection_audit"].get("global_stall_releases",0)} | {failed} |\n')
        report.write('\n遇到旧HT地图时仍执行3秒时效保护；没有为让车持续前进而放宽硬约束。全局引导释放说明该段目标没有持续接近，不能解释为该目标已经到达或覆盖完成。\n\n')
        report.write('| 环境 | 实收激光/600s | 平均频率(Hz) | 最大接收间隔(s) | 同源对齐检查点 | 观察器与建图器计数差恒定 |\n|---|---:|---:|---:|---:|---|\n')
        for row in state['runs']:
            scene=row['scenario'];audit=audits[scene];summary=audit['summary'];delivery=audit['source_aligned_input_delivery']
            report.write(f'| {NAMES[scene]} | {summary["registered_scans"]} | {summary["registered_scans"]/state["duration_s"]:.2f} | {summary["scan_gap_max_s"]:.2f} | {delivery["exact_source_stamp_checkpoints"]} | {delivery["constant_offset_in_observed_window"]} |\n')
        report.write('\n计数差恒定只支持这些对齐区间内没有新增相对漏收；不能证明源端始终连续发布，也不能排除两个订阅者同时漏收。各场景均保留完整扫描计数和原始时间戳检查点。\n\n')
        if (temp/'indoor/diagnostics/README.md').exists():
            report.write('室内组出现持续无可执行路线：原0.6m视点采样没有提供距车0.8m以外且满足HT支撑的目标。地图持续更新，节点未崩溃，不能把这组称为探索成功。详见[只读诊断及原始证据](indoor/diagnostics/README.md)。这五组保留原参数，修改后的补测另列。\n\n')
        if (temp/'tunnel/diagnostics/README.md').exists():
            report.write('隧道组触发返航后受阻：目标周围的车体足迹范围仍包含未知格，严格HT检查拒绝，未到家。详见[返航快照与诊断](tunnel/diagnostics/README.md)。没有放宽硬门槛来掩盖失败。\n\n')
        report.write('\n![各组前中后期实际画面](overview.jpg)\n\n![各场景观测和里程](scene_metrics.png)\n\n![实际轨迹](trajectories.png)\n\n')
        for row in state['runs']:
            scene=row['scenario']
            report.write(f'\n### {NAMES[scene]}末段实际HT\n\n![八方向HT]({scene}/late_ht.png)\n\n![考虑车体足迹的HT硬门槛]({scene}/late_ht_footprint.png)\n\n[同期接收的相机画面]({scene}/late_camera.jpg) · [原始图层快照]({scene}/late_map_snapshot.npz) · [时间与坐标元数据]({scene}/late_map_snapshot.json)\n\n')
        report.write(f'全部视频按15fps、{state["duration_s"]}秒裁剪，时长校验允许1帧误差，完整解码通过；实际帧数和时长见各组video_validation.json。各组共有源文件的{len(common)}项哈希一致，各组自身冻结文件核验见suite_validation.json。\n\n')
        report.write('相机年龄是图像接收后的年龄；相机仿真时间戳与导航墙钟不同，不能把该数值解释为传感器端到端延迟。原始MCAP、全高程历史和输入诊断保存在suite.json所列本地目录；本次只发布选取的数据与视频。\n')
    for p in temp.rglob('*.csv'):p.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'))
    (temp/'summary.json').write_text(json.dumps(dict(duration_s=state['duration_s'],scenes=summaries,
        shared_source_hashes={key:first[key] for key in sorted(common)},source_folder=str(job)),ensure_ascii=False,indent=2)+'\n')
    checksums={str(p.relative_to(temp)):hashlib.sha256(p.read_bytes()).hexdigest() for p in temp.rglob('*') if p.is_file()}
    (temp/'files_sha256.json').write_text(json.dumps(checksums,ensure_ascii=False,indent=2)+'\n')
    temp.rename(out)
    print(json.dumps(dict(output=str(out),videos=len(summaries),largest_video_bytes=max((out/s/'camera_h264.mp4').stat().st_size for s in summaries)),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
