#!/usr/bin/env python3
"""Render actual offline C++ route results; never simulates or commands a vehicle."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import subprocess

import numpy as np
from grid_map_msgs.msg import GridMap
from rclpy.serialization import deserialize_message


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def setup():
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib import pyplot as plt, font_manager
    font = Path('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
    if font.exists():
        font_manager.fontManager.addfont(str(font))
        plt.rcParams['font.family'] = font_manager.FontProperties(fname=str(font)).get_name()
    plt.rcParams['axes.unicode_minus'] = False
    return plt


def load_map(row):
    path = Path(row['map_file'])
    if sha(path) != row['map_sha256']:
        raise ValueError(f'Map digest mismatch: {path}')
    m = deserialize_message(path.read_bytes(), GridMap)
    rows = round(m.info.length_x / m.info.resolution)
    cols = round(m.info.length_y / m.info.resolution)
    arrays = {}
    for name, data in zip(m.layers, m.data):
        if [d.label for d in data.layout.dim] != ['column_index', 'row_index']:
            raise ValueError('Expected canonical GridMap array layout')
        value = np.asarray(data.data, np.float32).reshape((rows, cols), order='F')
        arrays[name] = np.roll(value, (-m.outer_start_index, -m.inner_start_index), (0, 1))
    q = m.info.pose.orientation
    if abs(q.x) > 1e-6 or abs(q.y) > 1e-6:
        raise ValueError('Non-planar map')
    yaw = math.atan2(2 * q.w * q.z, 1 - 2 * q.z * q.z)
    return dict(message=m, arrays=arrays, probabilities=np.stack([arrays[f'ht_dir_{k}'] for k in range(8)]),
                center=np.array([m.info.pose.position.x, m.info.pose.position.y]), resolution=m.info.resolution,
                yaw=yaw, shape=(rows, cols))


def world(field, i, j, *, edge=False):
    rows, cols = field['shape']
    offset = 0 if edge else .5
    x = (rows / 2 - np.asarray(i) - offset) * field['resolution']
    y = (cols / 2 - np.asarray(j) - offset) * field['resolution']
    co, si = math.cos(field['yaw']), math.sin(field['yaw'])
    return field['center'][0] + co*x-si*y, field['center'][1] + si*x+co*y


def bounds(row):
    poses = np.asarray(row.get('poses', []), float).reshape((-1, 3))
    points = np.concatenate([np.array([row['start'][:2], row['goal'][:2]]), poses[:, :2]])
    lo, hi = points.min(axis=0)-.9, points.max(axis=0)+.9
    mid = (lo+hi)/2
    half = max(float(np.max(hi-lo))/2, 1.8)
    return mid-half, mid+half


def voxels(ax, field, limits, plt):
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    stride = 12
    nr, nc = field['shape']
    ii, jj = np.meshgrid(np.arange(stride//2, nr, stride), np.arange(stride//2, nc, stride), indexing='ij')
    xx, yy = world(field, ii, jj)
    low, high = limits
    v = field['arrays']['ht_valid'][ii, jj] >= .5
    inside = v & (xx >= low[0]) & (xx <= high[0]) & (yy >= low[1]) & (yy <= high[1])
    p = field['probabilities'][:, ii, jj]
    k, i, j = np.where(np.broadcast_to(inside, p.shape) & np.isfinite(p))
    width = stride*field['resolution']*.96
    vertices = np.array([[0,0,0],[1,0,0],[1,1,0],[0,1,0],
                         [0,0,1],[1,0,1],[1,1,1],[0,1,1]], float)
    vertices = vertices[None] * np.array([width, width, 45.])[None,None]
    vertices = vertices + np.stack([xx[i,j]-width/2, yy[i,j]-width/2, k*45.], axis=1)[:,None]
    faces = np.array([[0,1,2,3],[4,5,6,7],[0,1,5,4],[1,2,6,5],[2,3,7,6],[3,0,4,7]])
    rgba = plt.get_cmap('RdYlGn')(p[k,i,j]); rgba[:,3] = .075
    collection = Poly3DCollection(vertices[:,faces].reshape(-1,4,3), facecolors=np.repeat(rgba,6,axis=0),
                                  edgecolors=(.5,.6,.65,.04), linewidths=.13, zsort='average')
    ax.add_collection3d(collection)
    ax.set(xlim=(low[0],high[0]), ylim=(low[1],high[1]), zlim=(0,360),
           zticks=np.arange(0,361,45), xlabel='X / m', ylabel='Y / m', zlabel='车头 θ / °')
    ax.view_init(elev=23, azim=-61)
    ax.set_box_aspect((1,1,1.15))
    ax.tick_params(labelsize=8)
    ax.set_title(f'XYθ 半透明体素格 | 显示抽样 {stride*field["resolution"]:.2f}m × 45°\n'
                 f'原图 {field["resolution"]:.2f}m/格；未知透明；颜色为真实八通道 T', fontsize=11)
    return stride


def line3(ax, poses, **kwargs):
    if not len(poses):
        return
    theta = np.degrees(poses[:,2]) % 360
    breaks = np.where(np.abs(np.diff(theta)) > 180)[0]+1
    for segment in np.split(np.column_stack([poses[:,:2], theta]), breaks):
        if len(segment):
            ax.plot(segment[:,0], segment[:,1], segment[:,2], **kwargs)


def render_frame(path, row, previous, field, progress, plt, *, synthetic):
    fig = plt.figure(figsize=(16,9), dpi=120, facecolor='#f5f8fa')
    ax3 = fig.add_axes([.015,.15,.54,.73], projection='3d')
    ax2 = fig.add_axes([.60,.23,.33,.59])
    limits = bounds(row)
    stride = voxels(ax3, field, limits, plt)
    poses = np.asarray(row.get('poses', []), float).reshape((-1,3))
    count = max(1, min(len(poses), int(round(progress*max(0,len(poses)-1)))+1)) if len(poses) else 0
    prefix = poses[:count]
    current = prefix[-1] if count else np.asarray(row['start'], float)
    channel = int(math.floor(((current[2]-field['yaw'])%(2*math.pi))/(math.pi/4)+.5))%8
    nr, nc = field['shape']; ii,jj = np.meshgrid(np.arange(nr+1),np.arange(nc+1),indexing='ij')
    xx,yy = world(field,ii,jj,edge=True)
    shown = np.where(field['arrays']['ht_valid']>=.5,field['probabilities'][channel],np.nan)
    color = ax2.pcolormesh(xx,yy,shown,cmap='RdYlGn',vmin=0,vmax=1,shading='flat',rasterized=True)
    obstacle = np.where(field['arrays']['ht_obstacle']>=.5,1.,np.nan)
    from matplotlib.colors import ListedColormap
    ax2.pcolormesh(xx,yy,obstacle,cmap=ListedColormap(['#263238']),shading='flat',rasterized=True)
    if len(poses):
        line3(ax3, poses, color='#5e6971', lw=1, alpha=.45)
        ax2.plot(poses[:,0],poses[:,1],color='#5e6971',lw=1,alpha=.45,label='完整规划路径')
        line3(ax3,prefix,color='#008bd1',lw=3)
        for i in range(1,count):
            d=prefix[i,:2]-prefix[i-1,:2]
            reverse=float(d @ np.array([math.cos(prefix[i-1,2]),math.sin(prefix[i-1,2])])) < -1e-6
            ax2.plot(prefix[i-1:i+1,0],prefix[i-1:i+1,1],color='#a03dcc' if reverse else '#008bd1',lw=3)
    ax3.scatter([current[0]],[current[1]],[math.degrees(current[2])%360],c='#0079bf',s=35,depthshade=False)
    ax2.scatter([row['start'][0]],[row['start'][1]],c='#177b43',s=55,marker='o',label='固定起点',zorder=8)
    ax2.scatter([row['goal'][0]],[row['goal'][1]],c='#b04493',s=90,marker='*',label='查询目标',zorder=8)
    ax2.arrow(current[0],current[1],.28*math.cos(current[2]),.28*math.sin(current[2]),
              width=.035,head_width=.13,color='#00577c',length_includes_head=True,zorder=9)
    low,high=limits
    ax2.set(xlim=(low[0],high[0]),ylim=(low[1],high[1]),xlabel='X / m',ylabel='Y / m',aspect='equal')
    ax2.set_facecolor('#dce1e5')
    ax2.set_title(f'XY：当前车头对应 {channel*45}° 通道\n黑色=测得障碍；蓝色=前进，紫色=倒车',fontsize=11)
    ax2.legend(loc='upper left',fontsize=8)
    fig.colorbar(color,ax=ax2,shrink=.75,pad=.03,label='可通过性 T')
    names={'synthetic_reverse_theta0':'合成方向走廊：目标在车后，实际规划倒车',
           'synthetic_directional_turn_wall':'合成方向地形：转向并绕过挡墙'}
    name=names.get(row['label'],'历史实车数据末帧：检查起点为什么不放行')
    scope='合成场景 · 离线路径回放' if synthetic else '记录地形 · 离线固定目标查询'
    fig.suptitle(f'{name}\n{scope}；没有驱动车辆，不是实车录像或搜索过程动画',fontsize=16,y=.98)
    before_term=previous.get('termination',previous.get('error','未知'))
    after_term=row.get('termination',row.get('error','未知'))
    fig.text(.035,.105,f'修改前：{before_term} / 起点 {previous.get("start_support","未知")}   →   '
             f'修改后：{after_term} / 起点 {row.get("start_support","未知")}',fontsize=12,color='#23303c')
    fig.text(.035,.070,f'实际搜索 {row.get("search_wall_ms",0):.3f}ms；展开 {row.get("expanded",0)} 状态；'
             f'路径 {row.get("path_length_m",0):.2f}m；独立逐段复核：{row.get("independent_recheck_passed",False)}；'
             f'显示规划点 {count}/{len(poses)}',fontsize=11)
    message='按保存路径点依次展示，播放进度不代表车辆速度。' if len(poses) else '规划未产生路径：起点检查未通过，不能绘制或补造路线。'
    fig.text(.035,.032,message+'  保留 T≥0.5 硬门槛及0.6m物理支撑范围。',fontsize=11,color='#b83e35' if not len(poses) else '#34434d')
    fig.savefig(path,dpi=120)
    plt.close(fig)
    return {'label':row['label'],'poses_shown':count,'actual_poses':len(poses),'display_stride':stride,
            'display_resolution_m':stride*field['resolution'],'channel':channel,'termination':after_term}


def comparison(before,after,out,plt):
    fig,axes=plt.subplots(1,3,figsize=(16,5),dpi=140)
    groups=[('历史数据固定查询',lambda q:not q['label'].startswith('synthetic_')),
            ('独立合成对照',lambda q:q['label'].startswith('synthetic_'))]
    for offset,(name,result,color) in zip([-.18,.18],[('修改前',before,'#597d9e'),('修改后',after,'#e29546')]):
        nums=[sum(bool(q.get('reached')) for q in result['queries'] if pick(q)) for _,pick in groups]
        bars=axes[0].bar(np.arange(2)+offset,nums,.36,label=name,color=color)
        for bar,num,(group,pick) in zip(bars,nums,groups):
            total=sum(1 for q in result['queries'] if pick(q))
            axes[0].text(bar.get_x()+bar.get_width()/2,num+.03,f'{num}/{total}',ha='center',fontsize=10)
    axes[0].set(xticks=[0,1],xticklabels=[x[0] for x in groups],ylabel='成功查询数',title='同一地图、同一起终点')
    axes[0].set_ylim(0,max(3,axes[0].get_ylim()[1]+.5));axes[0].legend()
    names=['synthetic_reverse_theta0','synthetic_directional_turn_wall']
    for offset,(name,result,color) in zip([-.18,.18],[('修改前',before,'#597d9e'),('修改后',after,'#e29546')]):
        lookup={q['label']:q for q in result['queries']}
        values=[lookup[k]['search_wall_ms'] for k in names]
        axes[1].bar(np.arange(2)+offset,values,.36,label=name,color=color)
    axes[1].set(xticks=[0,1],xticklabels=['方向走廊倒车','方向地形绕墙'],ylabel='实际搜索耗时 / ms',title='合成场景：计算时间，不是运动时间')
    axes[1].legend()
    counts=[Counter(q.get('start_support','ERROR') for q in result['queries'] if not q['label'].startswith('synthetic_')) for result in [before,after]]
    reasons=sorted(set(counts[0])|set(counts[1]))
    for offset,c,name,color in zip([-.18,.18],counts,['修改前','修改后'],['#597d9e','#e29546']):
        axes[2].bar(np.arange(len(reasons))+offset,[c[k] for k in reasons],.36,label=name,color=color)
    axes[2].set(xticks=np.arange(len(reasons)),xticklabels=reasons,ylabel='查询数',title='记录地形：起点支撑检查结果')
    axes[2].legend()
    for ax in axes:ax.grid(axis='y',alpha=.2)
    unique_maps=len({q['map_sha256'] for q in after['queries'] if not q['label'].startswith('synthetic_')})
    fig.suptitle('实际 C++ XYθ 规划对照：固定查询；不代表探索收益或实车通行能力',fontsize=14)
    fig.text(.5,.018,f'记录数据共 {unique_maps} 张地图/起点，各查询8个目标；目标数不是独立实车试验次数。合成对照另列。',ha='center',fontsize=10)
    fig.tight_layout(rect=[0,.055,1,.93]);fig.savefig(out/'comparison.png');plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    p.add_argument('--ffmpeg',required=True);a=p.parse_args()
    data=a.data.resolve();before=json.loads((data/'before.json').read_text());after=json.loads((data/'after.json').read_text())
    input_meta=json.loads((data/'input/metadata.json').read_text())
    if before['parameters']!=after['parameters']:raise ValueError('Compared runtime parameters differ')
    b={q['label']:q for q in before['queries']};v={q['label']:q for q in after['queries']}
    if b.keys()!=v.keys():raise ValueError('Compared query labels differ')
    for label,row in v.items():
        if row.get('error') or b[label].get('error'):raise ValueError(f'Cannot silently render runner error: {label}')
        for key in ['map_sha256','start','goal']:
            if row[key]!=b[label][key]:raise ValueError(f'Compared input differs: {label}')
        if row['reached'] and not(row['all_segments_permitted'] and row['independent_recheck_passed']):
            raise ValueError('Successful path was not independently checked')
    out=a.output.resolve();out.mkdir(parents=True,exist_ok=False);(out/'frames').mkdir()
    plt=setup();comparison(before,after,out,plt)
    recorded=[q for q in after['queries'] if q['label'].startswith('recorded_')]
    last=max(recorded,key=lambda q:(q['map_stamp_ns'],q['label'].endswith('000deg')))
    scenes=[('synthetic_directional_turn_wall',8.,12),('synthetic_reverse_theta0',8.,12),(last['label'],4.,6)]
    frames=[];timeline=['ffconcat version 1.0'];index=0
    for label,duration,number in scenes:
        row=v[label];field=load_map(row)
        for j in range(number):
            target=out/'frames'/f'{index:04d}.png'
            info=render_frame(target,row,b[label],field,j/max(1,number-1),plt,synthetic=label.startswith('synthetic_'))
            info.update(file=f'frames/{index:04d}.png',display_duration_s=duration/number)
            frames.append(info);timeline.extend([f"file 'frames/{index:04d}.png'",f'duration {duration/number:.12f}'])
            if j==number-1:
                (out/(label+'.png')).write_bytes(target.read_bytes())
            index+=1
    timeline.append(f"file 'frames/{index-1:04d}.png'")
    timeline_path=out/'timeline.ffconcat';timeline_path.write_text('\n'.join(timeline)+'\n')
    video=out/'HT_xytheta_actual_cpp_routes_20s.mp4'
    command=[a.ffmpeg,'-hide_banner','-loglevel','error','-n','-f','concat','-safe','0','-i',str(timeline_path),
             '-an','-vf','fps=20','-t','20','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(video)]
    subprocess.run(command,check=True)
    decoded=subprocess.run([a.ffmpeg,'-v','error','-i',str(video),'-f','null','-'],capture_output=True,text=True)
    if decoded.returncode or decoded.stderr:raise RuntimeError('Video full decode failed: '+decoded.stderr)
    metadata={'scope':'Actual C++ after.poses replay over unchanged HT fields. Synthetic directional controls plus recorded last-frame failure. No vehicle video, no simulated execution, no search-front animation.',
              'input_scope':input_meta['scope'],'before_sha256':sha(data/'before.json'),'after_sha256':sha(data/'after.json'),
              'input_metadata_sha256':sha(data/'input/metadata.json'),'video':video.name,'video_sha256':sha(video),
              'video_size':video.stat().st_size,'duration_s':20,'encoding':'H264/yuv420p/20fps',
              'full_decode_passed':True,'ffmpeg_command':command,'frames':frames,'keyframe_count':len(frames),
              'animation_policy':'Reveal saved actual path poses only; repeated still frames do not imply measured motion speed or search timing.',
              'unknown_policy':'Unknown field cells transparent in voxels and gray in XY; no interpolation or fabricated path points.',
              'last_recorded_query':last['label'],'last_recorded_termination':last['termination']}
    (out/'metadata.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:metadata[k] for k in ['video','duration_s','full_decode_passed','keyframe_count']},ensure_ascii=False))


if __name__=='__main__':main()
