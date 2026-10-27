#!/usr/bin/env python3
"""Recompute saved HT inputs and render honest offline replay videos.

No rosbag player, device driver, planner or chassis output is started. Only
trusted local pickle files may be supplied. Historical bag geometry is checked
against the production decoder without fabricating an observation-age layer.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import pickle
import shutil
import sqlite3
import subprocess
import time
from types import SimpleNamespace

import numpy as np
import rclpy
from rclpy.serialization import deserialize_message
from rclpy.time import Time
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry

from cupy_to_ht import CupyToHt, decode_elevation_source

ROOT = Path(__file__).resolve().parents[2]


def stamp(m):
    return m.header.stamp.sec * 10**9 + m.header.stamp.nanosec


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def layers(m):
    nx = round(m.info.length_x / m.info.resolution)
    ny = round(m.info.length_y / m.info.resolution)
    return {k: np.roll(np.asarray(v.data, np.float32).reshape(nx, ny, order='F'),
                       (-m.outer_start_index, -m.inner_start_index), (0, 1))
            for k, v in zip(m.layers, m.data)}


def pose(m):
    p, q = m.pose.pose.position, m.pose.pose.orientation
    return np.array([p.x, p.y, math.atan2(2 * (q.w*q.z + q.x*q.y),
                                        1 - 2 * (q.y*q.y + q.z*q.z))])


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def current_commit():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


def recompute(source, out):
    out.mkdir(parents=True, exist_ok=False)
    raw = pickle.loads(source.read_bytes())  # User-provided trusted archive.
    maps = sorted((deserialize_message(b, GridMap) for b in raw['maps']), key=stamp)
    odoms = sorted((deserialize_message(b, Odometry) for b in raw['odometry']), key=stamp)
    rclpy.init(args=['--ros-args', '-p', 'ht_device:=cpu', '-p', 'ht_quality_backend:=numpy',
                    '-p', 'surface_sensor_ground_offset_m:=0.23479',
                    '-p', 'odometry_child_frame:=base_link', '-p', 'ht_small_hole_repair:=true'])
    node = CupyToHt()
    clock = [stamp(maps[0])]
    node.get_clock = lambda: SimpleNamespace(now=lambda: Time(nanoseconds=clock[0]))
    captured = []

    class Capture:
        def publish(self, m):
            captured.append(m)

        def get_subscription_count(self):
            return 0

    node.pub = Capture()
    node.history_pub = SimpleNamespace(get_subscription_count=lambda: 0)
    index = 0
    frames = []
    try:
        for i, source_map in enumerate(maps):
            clock[0] = stamp(source_map) + 30_000_000
            while index < len(odoms) and stamp(odoms[index]) <= clock[0]:
                node.on_odometry(odoms[index])
                index += 1
            before = len(captured)
            started = time.perf_counter()
            node.on_map(source_map)
            elapsed = time.perf_counter() - started
            item = {'input_index': i, 'stamp_ns': stamp(source_map),
                    't_s': (stamp(source_map) - stamp(maps[0])) / 1e9,
                    'callback_s': elapsed, 'output': len(captured) > before}
            if item['output']:
                result = captured[-1]
                d = layers(result)
                robot_odom = min(odoms, key=lambda m: abs(stamp(m) - stamp(result)))
                robot = pose(robot_odom)
                r = result.info.resolution
                side = d['ht_valid'].shape[0]
                ii, jj = np.indices((side, side))
                x = result.info.pose.position.x + (side/2 - ii - .5) * r
                y = result.info.pose.position.y + (side/2 - jj - .5) * r
                body = (x-robot[0])**2 + (y-robot[1])**2 <= .6**2
                physical = d['ht_observation_valid'] >= .5
                valid = d['ht_valid'] >= .5
                probs = np.stack([d[f'ht_dir_{k}'] for k in range(8)])
                item.update(file=f'frame_{i:04d}.npz', body_cells=int(body.sum()),
                            body_physical_unknown=int((body & ~physical).sum()),
                            body_context_invalid=int((body & ~valid).sum()),
                            context_valid=int(valid.sum()), physical_valid=int(physical.sum()),
                            probability_mean=[float(np.nanmean(p)) for p in probs],
                            pose_skew_s=(stamp(robot_odom)-stamp(result))/1e9)
                np.savez_compressed(out/item['file'], probabilities=probs, robot=robot,
                                    center=[result.info.pose.position.x, result.info.pose.position.y],
                                    resolution=r, raw=layers(source_map)['elevation'],
                                    raw_center=[source_map.info.pose.position.x, source_map.info.pose.position.y],
                                    **d)
            frames.append(item)
            print(f'current {i+1}/{len(maps)} output={item["output"]} elapsed={elapsed:.3f}s', flush=True)
        metadata = dict(scope='Offline HT callback recomputation; no new vehicle trajectory or closed loop',
                        source=str(source), source_sha256=sha(source), input_maps=len(maps),
                        input_odometry=len(odoms), accepted_odometry=len(node.input_odometry.samples),
                        duration_s=(stamp(maps[-1])-stamp(maps[0]))/1e9,
                        outputs=sum(f['output'] for f in frames), frames=frames,
                        parameters={'ht_device':'cpu','ht_quality_backend':'numpy',
                                    'ht_small_hole_repair':True,'surface_sensor_ground_offset_m':.23479,
                                    'odometry_child_frame':'base_link','controlled_clock_offset_s':.03},
                        source_commit=current_commit(), input_fault=node.input_odometry.fault,
                        diagnostics=node.diagnostics)
        write_json(out/'index.json', metadata)
        return metadata
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


def check_legacy(bag, out):
    out.mkdir(parents=True, exist_ok=False)
    frames, odoms, reasons, sizes = [], [], Counter(), Counter()
    digest = hashlib.sha256()
    count = 0
    missing_age = 0
    first = None
    last = None
    saved_at = -math.inf
    databases = []
    for path in sorted(bag.glob('*.db3'), key=lambda p: int(p.stem.split('_')[-1])):
        databases.append({'name':path.name,'size':path.stat().st_size})
        connection = sqlite3.connect('file:'+str(path)+'?mode=ro&immutable=1', uri=True)
        wanted = {i:(name, typ) for i, name, typ in connection.execute('select id,name,type from topics')
                  if name in ('/elevation_mapping_node/elevation_map_raw','/state_estimation')}
        placeholders = ','.join('?' for _ in wanted)
        rows = connection.execute(f'select topic_id,timestamp,data from messages where topic_id in ({placeholders}) order by timestamp', tuple(wanted))
        for topic_id, receipt_ns, data in rows:
            name, _ = wanted[topic_id]
            if name == '/state_estimation':
                m = deserialize_message(data, Odometry)
                odoms.append((stamp(m), pose(m)))
                continue
            count += 1
            digest.update(data)
            m = deserialize_message(data, GridMap)
            first = stamp(m) if first is None else first
            last = stamp(m)
            shape = (round(m.info.length_x/m.info.resolution),round(m.info.length_y/m.info.resolution))
            sizes[str(shape)] += 1
            missing_age += 'observation_age' not in m.layers
            try:
                decode_elevation_source(m)
                reason = 'ACCEPTED'
            except (ValueError, TypeError, OverflowError) as error:
                reason = str(error)
            reasons[reason] += 1
            if stamp(m)/1e9-saved_at >= 1.0:
                file=f'frame_{len(frames):04d}.npz'
                np.savez_compressed(out/file, raw=layers(m)['elevation'],
                                    center=[m.info.pose.position.x,m.info.pose.position.y],
                                    resolution=m.info.resolution)
                frames.append({'file':file,'stamp_ns':stamp(m),'receipt_ns':receipt_ns,
                               't_s':(stamp(m)-first)/1e9,'reason':reason})
                saved_at=stamp(m)/1e9
        connection.close()
        print(f'legacy {path.name}: cumulative native checks={count}',flush=True)
    odoms.sort(key=lambda p:p[0])
    stamps=np.array([v[0] for v in odoms],np.int64)
    for f in frames:
        j=int(np.argmin(np.abs(stamps-f['stamp_ns'])))
        f['robot']=odoms[j][1].tolist()
        f['pose_skew_s']=(odoms[j][0]-f['stamp_ns'])/1e9
    result=dict(scope='Native input-contract audit; recorded raw-map preview only, NOT new HT inference',
                source=str(bag), databases=databases, checked_elevation_messages=count,
                processed_raw_map_cdr_sha256=digest.hexdigest(),
                shapes=dict(sizes), missing_observation_age=missing_age, decoder_results=dict(reasons),
                duration_s=(last-first)/1e9, frames=frames, source_commit=current_commit(),
                no_age_fabrication=True, no_padding_or_resampling=True)
    write_json(out/'index.json',result)
    return result


def plot_setup():
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt, font_manager
    font=Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family']=font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus']=False
    return plt


def image(ax, arr, center, resolution, **kwargs):
    n,m=arr.shape
    extent=[center[0]-n*resolution/2,center[0]+n*resolution/2,
            center[1]-m*resolution/2,center[1]+m*resolution/2]
    ax.imshow(np.flip(arr.T,(0,1)),origin='lower',extent=extent,
              interpolation='nearest',**kwargs)
    ax.set_aspect('equal')
    ax.tick_params(labelsize=8)
    ax.set_xlabel('X / m',fontsize=9)
    ax.set_ylabel('Y / m',fontsize=9)


def draw_voxels(ax, probabilities, valid, center, resolution, plt):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    # Representative samples only; this changes display density, not inference.
    stride=12
    p=np.flip(probabilities.transpose(0,2,1),(1,2))[:,::stride,::stride]
    v=np.flip(valid.T,(0,1))[::stride,::stride]
    k,i,j=np.where(np.broadcast_to(v,p.shape) & np.isfinite(p))
    n=valid.shape[0]
    x=center[0]-n*resolution/2+(j*stride+.5)*resolution
    y=center[1]-n*resolution/2+(i*stride+.5)*resolution
    z=k*45.
    width=stride*resolution*.92
    vertices=np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],
                       [0,0,1],[1,0,1],[1,1,1],[0,1,1]],float)
    vertices=vertices[None,:,:]*np.array([width,width,45.])[None,None,:]+np.stack([x-width/2,y-width/2,z],1)[:,None,:]
    faces=np.array([[0,1,2,3],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])
    rgba=plt.get_cmap('RdYlGn')(p[k,i,j]);rgba[:,3]=.075
    collection=Poly3DCollection(vertices[:,faces].reshape(-1,4,3),
                               facecolors=np.repeat(rgba,6,axis=0),
                               edgecolors=(.75,.83,.88,.035),linewidths=.12,zsort='average')
    ax.add_collection3d(collection)
    half=n*resolution/2
    ax.set(xlim=(center[0]-half,center[0]+half),ylim=(center[1]-half,center[1]+half),
           zlim=(0,360),zticks=np.arange(0,361,45),xlabel='X / m',ylabel='Y / m',zlabel='θ / °')
    ax.tick_params(labelsize=7)
    ax.view_init(elev=23,azim=-61)
    ax.set_box_aspect((1,1,1.2))
    ax.set_title('XYθ 半透明体素：颜色为方向可通过性\nθ 是朝向；显示抽样约0.49m，未知留空',fontsize=11)


def render_current(folder, plt):
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Circle
    metadata=json.loads((folder/'index.json').read_text())
    pngs=folder/'frames';pngs.mkdir(exist_ok=False)
    supported=plt.get_cmap('RdYlGn').copy();supported.set_bad('#d0d3d6')
    terrain=plt.get_cmap('terrain').copy();terrain.set_bad('#d0d3d6')
    for index,item in enumerate(f for f in metadata['frames'] if f['output']):
        with np.load(folder/item['file']) as d:
            probabilities=d['probabilities'];valid=d['ht_valid']>=.5
            physical=d['ht_observation_valid']>=.5;obstacle=d['ht_obstacle']>=.5
            center=d['center'];r=float(d['resolution']);robot=d['robot']
            fig=plt.figure(figsize=(19.2,10.8),dpi=100)
            fig.suptitle(f'新版 HT 离线重算 | 2026-10-23 保存输入 | t={item["t_s"]:.2f}s | 帧 {index+1}/{metadata["outputs"]}',fontsize=19,y=.98)
            ax=fig.add_axes([.005,.40,.32,.53],projection='3d')
            draw_voxels(ax,probabilities,valid,center,r,plt)
            rawax=fig.add_axes([.035,.10,.125,.24]);image(rawax,d['raw'],d['raw_center'],r,cmap=terrain)
            rawax.plot(robot[0],robot[1],'o',color='#1675ec',markersize=4)
            rawax.set_title('记录的原始高程',fontsize=11)
            support=np.zeros_like(valid,dtype=np.uint8)
            support[physical]=1;support[physical & valid]=2;support[obstacle]=3
            ax=fig.add_axes([.205,.10,.125,.24]);image(ax,support,center,r,
                cmap=ListedColormap(['#a8adb2','#f6ce54','#3d9e56','#c13c34']),vmin=0,vmax=3)
            ax.add_patch(Circle(robot[:2],.6,fill=False,color='white',linewidth=1.5))
            ax.plot(robot[0],robot[1],'o',color='#1675ec',markersize=4)
            ax.set_title('支撑诊断；白圈 r=0.6m',fontsize=11)
            for k in range(8):
                row,col=divmod(k,4)
                ax=fig.add_axes([.365+col*.157,.55-row*.40,.142,.31])
                image(ax,np.where(valid,probabilities[k],np.nan),center,r,cmap=supported,vmin=0,vmax=1)
                ax.plot(robot[0],robot[1],'o',color='#1675ec',markersize=4)
                ax.set_title(f'HT θ={k*45}°',fontsize=13)
            fig.text(.365,.91,'红→绿：HT低→高；灰：上下文不足。蓝点：记录车位；没有新版规划轨迹。',fontsize=12)
            fig.text(.365,.055,f'本帧回调 {item["callback_s"]*1000:.1f} ms（本机CPU离线，非Jetson性能）\n'
                     f'车旁 {item["body_cells"]} 格：缺物理支撑 {item["body_physical_unknown"]}；HT上下文无效 {item["body_context_invalid"]}',fontsize=13)
            fig.text(.025,.028,'左下诊断：灰=缺支撑，黄=仅物理支撑，绿=物理+HT上下文，红=观测障碍。\n纯数据回放，无驱动、无底盘指令；本视频以0.2倍速播放记录时间。',fontsize=10)
            fig.savefig(pngs/f'{index:05d}.png');plt.close(fig)
        print(f'render current {index+1}/{metadata["outputs"]}',flush=True)


def render_legacy(folder, plt):
    m=json.loads((folder/'index.json').read_text());pngs=folder/'frames';pngs.mkdir(exist_ok=False)
    path=np.array([f['robot'][:2] for f in m['frames']])
    terrain=plt.get_cmap('terrain').copy();terrain.set_bad('#c5c8ca')
    for i,item in enumerate(m['frames']):
        with np.load(folder/item['file']) as d:
            fig=plt.figure(figsize=(19.2,10.8),dpi=100)
            fig.suptitle(f'历史实车录包兼容性回放 | 2026-10-11 | t={item["t_s"]:.1f}s / {m["duration_s"]:.1f}s',fontsize=21,y=.96)
            ax=fig.add_axes([.05,.16,.49,.68]);image(ax,d['raw'],d['center'],float(d['resolution']),cmap=terrain)
            ax.plot(path[:i+1,0],path[:i+1,1],color='#1265df',linewidth=1.8)
            ax.plot(item['robot'][0],item['robot'][1],'o',color='#1265df')
            ax.set_title('旧录包原始高程 + 已记录轨迹',fontsize=17)
            fig.text(.59,.77,'新版原生输入检查：拒绝',fontsize=25,color='#ba302b')
            fig.text(.59,.47,'旧输入：250×250，0.040m/格\n缺少 observation_age 层\n\n新版要求：291×291，并携带观测年龄\n\n不能直接生成新版 HT 结果。',fontsize=19,linespacing=1.8)
            fig.text(.59,.20,'未填造观测年龄、未强行扩图。\n蓝线是旧车实际记录，不是新版规划。\n这不代表新版车辆在此环境试跑。',fontsize=17,color='#555555',linespacing=1.7)
            fig.text(.06,.06,'原始录包约208秒；显示帧约1Hz；按记录时间1倍速。此片展示历史输入与新版接口的兼容性问题。',fontsize=14)
            fig.savefig(pngs/f'{i:05d}.png');plt.close(fig)
        if i%20==0:print(f'render legacy {i+1}/{len(m["frames"])}',flush=True)


def encode(folder, ffmpeg, speed):
    metadata=json.loads((folder/'index.json').read_text())
    frames=[f for f in metadata['frames'] if f.get('output',True)]
    timeline=folder/'timeline.ffconcat'
    lines=['ffconcat version 1.0']
    for i,f in enumerate(frames):
        delta=frames[i+1]['t_s']-f['t_s'] if i+1<len(frames) else .2
        lines.extend([f"file 'frames/{i:05d}.png'",f'duration {max(.02,delta/speed):.8f}'])
    lines.append(f"file 'frames/{len(frames)-1:05d}.png'")
    timeline.write_text('\n'.join(lines)+'\n')
    target=folder/'replay.mp4'
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-n','-f','concat','-safe','0',
                    '-i',str(timeline),'-an','-vf','fps=20','-c:v','libx264','-preset','fast',
                    '-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(target)],check=True)
    decoded=subprocess.run([ffmpeg,'-v','error','-i',str(target),'-f','null','-'],capture_output=True,text=True)
    if decoded.returncode or decoded.stderr:
        raise RuntimeError('Video decode validation failed: '+decoded.stderr)
    write_json(folder/'video_validation.json',dict(codec='H264',pixel_format='yuv420p',
        size=target.stat().st_size,sha256=sha(target),full_decode_passed=True,
        frame_images=len(frames),playback_speed=speed,source_commit=metadata['source_commit']))


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--archive',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--ffmpeg',required=True)
    p.add_argument('--phase',choices=['capture','render','all'],default='all')
    a=p.parse_args()
    if a.phase in ('capture','all'):
        a.output.mkdir(parents=True,exist_ok=False)
        source=a.archive/'validation/jetson_scout_2026-10-23/quality_optimization/live_input.pkl'
        recompute(source,a.output/'current_20261023')
        check_legacy(a.archive/'validation/arm_vehicle/results/demo_20261011_225010/rosbag',a.output/'legacy_20261011')
    if a.phase in ('render','all'):
        plt=plot_setup()
        render_current(a.output/'current_20261023',plt)
        encode(a.output/'current_20261023',a.ffmpeg,.2)
        render_legacy(a.output/'legacy_20261011',plt)
        encode(a.output/'legacy_20261011',a.ffmpeg,1.)


if __name__=='__main__':
    main()
