#!/usr/bin/env python3
"""Render captured live HT slices and the XYtheta path that drove the car."""
import json
import math
import sys
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
from matplotlib import colors, font_manager, pyplot as plt
import numpy as np
from PIL import Image

FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
font_manager.fontManager.addfont(FONT)
plt.rcParams['font.family']=font_manager.FontProperties(fname=FONT).get_name()
plt.rcParams['axes.unicode_minus']=False
CMAP=plt.get_cmap('RdYlGn').copy();CMAP.set_bad('#dddddd')
NORM=colors.Normalize(vmin=0,vmax=1)


def load_frames(directories):
    frames=[]
    for folder in directories:
        meta=json.loads((folder/'index.json').read_text())
        for item in meta['frames']:
            with np.load(folder/item['file']) as d:
                frames.append({**item,'probabilities':d['probabilities'].astype(np.float32),
                    'valid':d['valid'].astype(bool),'center':d['center'],
                    'resolution':float(d['resolution']),'robot':d['robot'],
                    'path':d['path'].astype(float),'stamp':float(d['map_stamp']),
                    'map_yaw':float(d['map_yaw'])})
    frames.sort(key=lambda a:a['stamp'])
    if frames:
        start=frames[0]['stamp']
        for f in frames:f['timeline_s']=round(f['stamp']-start,1)
    return frames


def display_arrays(frame):
    p=frame['probabilities'];valid=frame['valid']
    p=np.flip(np.transpose(p,(0,2,1)),axis=(1,2))
    valid=np.flip(valid.T,axis=(0,1))
    p=np.where(valid[None,:,:],p,np.nan)
    n=valid.shape[0];r=frame['resolution'];cx,cy=frame['center']
    extent=[cx-n*r/2,cx+n*r/2,cy-n*r/2,cy+n*r/2]
    return p,valid,extent


def route_classes(route):
    out=[]
    for a,b in zip(route,route[1:]):
        dx=b[0]-a[0];dy=b[1]-a[1]
        if math.hypot(dx,dy)<.002:kind='spin'
        elif dx*math.cos(a[2])+dy*math.sin(a[2])>=0:kind='forward'
        else:kind='reverse'
        out.append(kind)
    return out


def draw_slices(frame,output):
    p,valid,extent=display_arrays(frame)
    route=frame['path'];robot=frame['robot'];classes=route_classes(route)
    fig,axes=plt.subplots(2,4,figsize=(17,9.6),sharex=True,sharey=True,layout='constrained')
    for k,ax in enumerate(axes.flat):
        ax.imshow(p[k],origin='lower',extent=extent,cmap=CMAP,norm=NORM,interpolation='nearest')
        ax.plot(route[:,0],route[:,1],color='#202020',ls=':',lw=.85,alpha=.65)
        for i,kind in enumerate(classes):
            a,b=route[i],route[i+1]
            sector=int(math.floor((math.degrees((a[2]+b[2])/2)%360+22.5)/45))%8
            if sector!=k:continue
            color={'forward':'#05c7f2','reverse':'#bd4bff','spin':'#f7c844'}[kind]
            if kind=='spin':ax.scatter([a[0]],[a[1]],s=24,c=color,edgecolors='black',linewidths=.3,zorder=5)
            else:ax.plot([a[0],b[0]],[a[1],b[1]],color=color,lw=3,zorder=5)
        ax.scatter([route[-1,0]],[route[-1,1]],s=66,c='#1a66ff',marker='*',edgecolors='white',linewidths=.4,zorder=6)
        if int(round((math.degrees(robot[2])%360)/45))%8==k:
            ax.scatter([robot[0]],[robot[1]],s=65,c='#20ad49',edgecolors='white',linewidths=.7,zorder=7)
            ax.arrow(robot[0],robot[1],.34*math.cos(robot[2]),.34*math.sin(robot[2]),
                     color='#125c28',width=.035,head_width=.18,length_includes_head=True,zorder=8)
        ax.set_title(f'θ = {k*45}°',fontsize=13)
        ax.set_xlim(extent[0],extent[1]);ax.set_ylim(extent[2],extent[3]);ax.set_aspect('equal')
        # Display grid is 0.5 m; HT samples remain at their original 0.041 m resolution.
        ax.set_xticks(np.arange(math.ceil(extent[0]*2)/2,extent[1],.5),minor=True)
        ax.set_yticks(np.arange(math.ceil(extent[2]*2)/2,extent[3],.5),minor=True)
        ax.grid(which='minor',color='white',alpha=.34,lw=.35)
        ax.tick_params(labelsize=8)
    for ax in axes[1]:ax.set_xlabel('X (m)')
    for ax in axes[:,0]:ax.set_ylabel('Y (m)')
    fig.colorbar(plt.cm.ScalarMappable(norm=NORM,cmap=CMAP),ax=axes,shrink=.55,pad=.01,
                 label='HT 方向可通过概率 P(x,y,θ)；灰色 = 未观测')
    fig.suptitle(f'实测 XYθ 规划 | t≈{frame["timeline_s"]:.1f}s | '
                 f'车 ({robot[0]:.2f},{robot[1]:.2f},{math.degrees(robot[2])%360:.0f}°) '
                 f'→ 视点 ({route[-1,0]:.2f},{route[-1,1]:.2f}) | {len(route)} 个姿态',fontsize=16)
    fig.text(.5,.012,'同一 XY 地形重复在 8 个 θ 层。黑色虚线是整条路线的 XY 投影；青/紫/黄分别是该层的前进/倒车/原地转向。'
             '绿色是当前车头姿态，蓝星是目标视点（目标朝向自由）。',ha='center',fontsize=10)
    fig.savefig(output,dpi=135,bbox_inches='tight')
    plt.close(fig)


def draw_3d(frame,output):
    from mpl_toolkits.mplot3d import Axes3D  # noqa:F401
    p,valid,extent=display_arrays(frame)
    step=8;rough=p[:,::step,::step];ny,nx=rough.shape[1:]
    xs=np.linspace(extent[0],extent[1],p.shape[2],endpoint=False)[::step]
    ys=np.linspace(extent[2],extent[3],p.shape[1],endpoint=False)[::step]
    xx,yy=np.meshgrid(xs,ys)
    route=frame['path'];classes=route_classes(route)
    fig=plt.figure(figsize=(12,9),dpi=150)
    ax=fig.add_subplot(111,projection='3d')
    for k in range(8):
        layer=rough[k]
        rgba=CMAP(NORM(np.nan_to_num(layer,nan=0)))
        rgba[...,3]=np.where(np.isfinite(layer),.40,0)
        ax.plot_surface(xx,yy,np.full_like(xx,k*45),facecolors=rgba,
                        edgecolor=(0,0,0,.15),linewidth=.12,shade=False,
                        rstride=1,cstride=1,antialiased=False)
    degrees=np.mod(np.degrees(route[:,2]),360)
    for i,kind in enumerate(classes):
        a,b=route[i],route[i+1]
        if abs(degrees[i+1]-degrees[i])>180:continue
        color={'forward':'#00c8f7','reverse':'#bc43ef','spin':'#e1a500'}[kind]
        ax.plot([a[0],b[0]],[a[1],b[1]],[degrees[i],degrees[i+1]],
                color=color,lw=3.3,zorder=20)
    robot=frame['robot'];ax.scatter([robot[0]],[robot[1]],[math.degrees(robot[2])%360],
                                   c='#008f32',s=85,depthshade=False)
    ax.scatter([route[-1,0]],[route[-1,1]],[degrees[-1]],c='#1455ff',s=90,marker='*',depthshade=False)
    ax.set(xlabel='X (m)',ylabel='Y (m)',zlabel='θ (°)',zlim=(0,315),zticks=np.arange(0,360,45))
    ax.view_init(elev=21,azim=-70);ax.set_box_aspect((1,1,1.25))
    ax.set_title('八张 HT 方向栅格构成 XYθ 空间；彩色线是实际规划路径\n'
                 '青：前进　紫：倒车　黄：原地转向',pad=18,fontsize=14)
    fig.colorbar(plt.cm.ScalarMappable(norm=NORM,cmap=CMAP),ax=ax,shrink=.58,pad=.06,label='HT P(pass)')
    fig.savefig(output,bbox_inches='tight')
    plt.close(fig)


def make_gif(pngs,output):
    images=[]
    for path in pngs:
        im=Image.open(path).convert('RGB')
        im.thumbnail((1300,850))
        images.append(im.quantize(colors=192))
    if images:images[0].save(output,save_all=True,append_images=images[1:],duration=950,loop=0,optimize=True)


def main():
    import argparse
    a=argparse.ArgumentParser();a.add_argument('--input',type=Path,nargs='+',required=True)
    a.add_argument('--output',type=Path,required=True)
    args=a.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    frames=load_frames(args.input)
    if not frames:raise RuntimeError('no captured planning frames')
    pngs=[]
    for i,f in enumerate(frames):
        out=args.output/f'slices_{i:02d}.png';draw_slices(f,out);pngs.append(out)
    make_gif(pngs,args.output/'exploration_xytheta_slices.gif')
    # Pick a route with meaningful heading variation, not just a straight segment.
    chosen=max(frames,key=lambda f:np.ptp(np.unwrap(f['path'][:,2]))+.02*len(f['path']))
    draw_slices(chosen,args.output/'xytheta_grid_keyframe.png')
    draw_3d(chosen,args.output/'xytheta_3d_keyframe.png')
    meta={'frames':len(frames),'source_files':[str(p) for p in args.input],
          'keyframe_t_s':chosen['timeline_s'],'map_resolution_m':chosen['resolution'],
          'ht_theta_layers_deg':list(range(0,360,45)),
          'planner_heading_bins':16,'display_grid_m':.5,
          'explanation':'HT layers are predicted traversability probabilities from the live GridMap; the path is the actual /ht_xytheta_path sent to the follower. Grid lines are display only.'}
    (args.output/'README.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(meta,ensure_ascii=False))

if __name__=='__main__':main()
