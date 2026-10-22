#!/usr/bin/env python3
"""Recorded HT shown as a filled XYtheta voxel lattice; publishes display markers only."""
import argparse,bisect,json,math,os,pickle,signal,subprocess,time
from contextlib import ExitStack
from pathlib import Path
import numpy as np
import yaml
from rviz_transparent_voxel_replay import decode_ht_grid,sha,frame_times,stop_process

CELL=.3
SIDE=32
HEADINGS=32
HEIGHT=CELL*HEADINGS

def theta_channels():
    # Display intervals tile[0,360); sample their centers. This is the same
    # nearest45deg lookup used by HT, not32 independent network predictions.
    angles=(np.arange(HEADINGS)+.5)*2*np.pi/HEADINGS
    return np.floor(angles/(np.pi/4)+.5).astype(int)%8

def voxel_field(grid,pose,side=SIDE,cell=CELL):
    if grid['source_resolution_m']!=grid['display_cell_m']:
        raise ValueError('Use full native HT cells, not the old stride3 display cache')
    offset=(np.arange(side)+.5-side/2)*cell
    xx,yy=np.meshgrid(offset,offset,indexing='ij')
    gx,gy=grid['x'],grid['y'];res=grid['source_resolution_m']
    ii=np.floor((gx[0]+res/2-(xx+pose[0]))/res).astype(int)
    jj=np.floor((gy[0]+res/2-(yy+pose[1]))/res).astype(int)
    inside=(ii>=0)&(ii<len(gx))&(jj>=0)&(jj<len(gy))
    i=np.clip(ii,0,len(gx)-1);j=np.clip(jj,0,len(gy)-1)
    valid=inside&grid['valid'][i,j]
    channels=theta_channels()
    values=grid['p'][:,i,j][channels].transpose(1,2,0).copy()
    valid=np.broadcast_to(valid[:,:,None],values.shape).copy()
    valid &= np.isfinite(values)&(values>=0)&(values<=1)
    values[~valid]=np.nan
    zz=(np.arange(HEADINGS)+.5)*cell
    xyz=np.stack(np.broadcast_arrays(xx[:,:,None],yy[:,:,None],zz[None,None,:]),axis=-1)
    return xyz,values,valid,channels

def kept_cells(cutaway=False,side=SIDE):
    i,j,k=np.indices((side,side,HEADINGS))
    return ~((i>=side//2)&(j>=side//2)) if cutaway else np.ones(i.shape,dtype=bool)

def boundary_edges(mask,cell=CELL):
    # Draw all small cell edges on the volume exterior and the cut surfaces.
    # There are no separated horizontal sheets; cubes fill every theta bin.
    edges=set();shape=mask.shape
    for index in zip(*np.where(mask)):
        for axis in range(3):
            for sign in (-1,1):
                nb=list(index);nb[axis]+=sign
                if all(0<=nb[a]<shape[a] for a in range(3)) and mask[tuple(nb)]:continue
                other=[a for a in range(3) if a!=axis]
                vertices=[]
                for u,v in [(0,0),(1,0),(1,1),(0,1)]:
                    p=list(index);p[axis]+=int(sign>0);p[other[0]]+=u;p[other[1]]+=v;vertices.append(tuple(p))
                for a,b in zip(vertices,vertices[1:]+vertices[:1]):edges.add(tuple(sorted((a,b))))
    a=np.array(sorted(edges),float).reshape(-1,3)*cell
    a[:,:2]-=mask.shape[0]*cell/2
    return a

def prepare(base_cache,cache,start,end):
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from grid_map_msgs.msg import GridMap
    data=pickle.loads(base_cache.read_bytes());source=data['sources']['ht'];origin=source['origin_wall_time']
    bag=Path(source['bag']);r=rosbag2_py.SequentialReader()
    r.open(rosbag2_py.StorageOptions(uri=str(bag),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    r.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local']))
    maps=[];prior=None
    while r.has_next():
        topic,raw,ns=r.read_next();t=ns/1e9-origin
        if t>end:break
        m=deserialize_message(raw,GridMap);h=decode_ht_grid(m,ns/1e9,1)
        if t<start:prior=(t,h)
        else:maps.append((t,h))
    if prior:maps.insert(0,prior)
    if not maps:raise ValueError('No native HT maps in interval')
    events=[e for e in data['data']['ht']['events'] if e[1] in ('pose','execution') and e[0]<=end]
    result=dict(maps=maps,events=events,start=start,end=end,source=source,
        base_cache_sha256=sha(base_cache),source_bag_metadata_sha256=sha(bag/'metadata.yaml'),
        rows=data['data']['ht']['rows'],volume=data['data']['ht']['volume'],
        scope='Existing Campus simulation recording. Native GridMap cells decoded without display stride; no navigation or inference replay.')
    cache.parent.mkdir(parents=True,exist_ok=True)
    with cache.open('wb') as f:pickle.dump(result,f,protocol=5)
    print('Prepared native HT cache:',len(maps),'maps',flush=True)

def config(path,topic,x):
    qos={'Value':topic,'Depth':2,'History Policy':'Keep Last','Reliability Policy':'Reliable','Durability Policy':'Volatile'}
    d={'Panels':[],'Visualization Manager':{'Class':'','Displays':[{'Class':'rviz_default_plugins/MarkerArray','Name':'XYtheta voxel volume','Enabled':True,'Marker Topic':qos,'Topic':qos}],
        'Enabled':True,'Global Options':{'Fixed Frame':'map','Background Color':'18; 25; 34','Frame Rate':15},'Name':'root',
        'Tools':[{'Class':'rviz_default_plugins/MoveCamera'}],
        'Views':{'Current':{'Class':'rviz_default_plugins/Orbit','Distance':23.,'Pitch':.47,'Yaw':.78,'Focal Point':{'X':0.,'Y':0.,'Z':HEIGHT*.5},'Target Frame':'map','Near Clip Distance':.01,'Name':'Current View','Focal Shape Fixed Size':True,'Focal Shape Size':.03},'Saved':[]}},
        'Window Geometry':{'X':x,'Y':68,'Width':960,'Height':800,'Hide Left Dock':True,'Hide Right Dock':True}}
    path.write_text(yaml.safe_dump(d,sort_keys=False))

def replay(args):
    import rclpy
    from rclpy.node import Node
    from visualization_msgs.msg import Marker,MarkerArray
    from geometry_msgs.msg import Point
    from std_msgs.msg import ColorRGBA
    from PIL import ImageGrab,ImageDraw,ImageFont
    out=args.output;out.mkdir(parents=True,exist_ok=False)
    data=pickle.loads(args.cache.read_bytes())
    if args.start<data['start'] or args.end>data['end']:raise ValueError('Replay outside prepared native cache')
    timeline=frame_times(args.start,args.end,args.speed,args.fps)
    env=dict(os.environ,DISPLAY=args.display,LIBGL_ALWAYS_SOFTWARE='1',QT_QPA_PLATFORM='xcb',LP_NUM_THREADS='4')
    with ExitStack() as cleanup:
        if Path('/tmp/.X11-unix/X'+args.display.lstrip(':')).exists():raise RuntimeError('Display already in use')
        xvfb=subprocess.Popen([str(args.xvfb),args.display,'-screen','0','1920x1080x24','-nolisten','tcp','-ac','+extension','GLX','+render'],env=env,
            stdout=cleanup.enter_context((out/'xvfb.log').open('w')),stderr=subprocess.STDOUT)
        cleanup.callback(stop_process,xvfb)
        deadline=time.monotonic()+15
        while not Path('/tmp/.X11-unix/X'+args.display.lstrip(':')).exists():
            if xvfb.poll() is not None or time.monotonic()>deadline:raise RuntimeError('Xvfb startup failed')
            time.sleep(.1)
        rclpy.init();cleanup.callback(rclpy.try_shutdown)
        node=Node('recorded_xytheta_voxel_grid_only');cleanup.callback(node.destroy_node)
        topics=['/recorded_voxel_grid/full','/recorded_voxel_grid/cutaway']
        pubs=[node.create_publisher(MarkerArray,t,2) for t in topics]
        for n,topic in enumerate(topics):
            cfg=out/('full.rviz' if n==0 else 'cutaway.rviz');config(cfg,topic,n*960)
            proc=subprocess.Popen(['rviz2','-d',str(cfg),'--ros-args','-r','__node:=voxel_view_'+str(n)],env=env,
                stdout=cleanup.enter_context((out/f'rviz_{n}.log').open('w')),stderr=subprocess.STDOUT)
            cleanup.callback(stop_process,proc)
        time.sleep(6)
        def marker(kind,idx,points=None,color=(1,1,1,1),scale=(1,1,1)):
            m=Marker();m.header.frame_id='map';m.ns='voxel_grid';m.id=idx;m.type=kind;m.action=Marker.ADD;m.pose.orientation.w=1.
            m.color=ColorRGBA(r=float(color[0]),g=float(color[1]),b=float(color[2]),a=float(color[3]));m.scale.x,m.scale.y,m.scale.z=map(float,scale)
            if points is not None:m.points=[Point(x=float(p[0]),y=float(p[1]),z=float(p[2])) for p in points]
            return m
        static=[];masks=[kept_cells(False),kept_cells(True)]
        for cut in (False,True):
            lattice=marker(Marker.LINE_LIST,100,boundary_edges(masks[int(cut)]),(.72,.80,.87,.18 if not cut else .3),(.011,0.,0.))
            decorations=[lattice]
            decorations.append(marker(Marker.LINE_LIST,101,[(5.25,-5.25,0.),(5.25,-5.25,HEIGHT)],(.82,.9,1.,.9),(.025,0.,0.)))
            for deg in range(0,361,45):
                m=marker(Marker.TEXT_VIEW_FACING,200+deg,None,(.93,.96,1.,1.),(0.,0.,.42));m.text=str(deg)+' deg'+(' = 0' if deg==360 else '')
                m.pose.position=Point(x=5.95,y=-5.65,z=deg/360*HEIGHT);decorations.append(m)
            for idx,text,p in [(0,'X / m',(5.35,-5.2,0.)),(1,'Y / m',(-5.2,5.35,0.))]:
                m=marker(Marker.TEXT_VIEW_FACING,600+idx,None,(.93,.96,1.,1.),(0.,0.,.35));m.text=text;m.pose.position=Point(x=p[0],y=p[1],z=p[2]);decorations.append(m)
            static.append(decorations)
        map_times=[v[0] for v in data['maps']];events=data['events'];event_index=0;state={};captures=[]
        font='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc';large=ImageFont.truetype(font,29);small=ImageFont.truetype(font,21)
        dest=out/'xytheta_voxel_grid_4x.mp4'
        enc=subprocess.Popen([str(args.encoder),'-nostdin','-y','-v','warning','-f','rawvideo','-pix_fmt','rgb24','-s','1920x1080','-r',str(args.fps),'-i','-',
            '-an','-c:v','libx264','-threads','2','-preset','veryfast','-crf','23','-pix_fmt','yuv420p','-movflags','+faststart',str(dest)],stdin=subprocess.PIPE,
            stderr=cleanup.enter_context((out/'encoder.log').open('w')))
        def finish():
            if not enc.stdin.closed:enc.stdin.close()
            try:enc.wait(timeout=20)
            except subprocess.TimeoutExpired:enc.kill();enc.wait()
        cleanup.callback(finish)
        for frame,t in enumerate(timeline):
            while event_index<len(events) and events[event_index][0]<=t:
                et,kind,v=events[event_index];state[kind]=v;event_index+=1
            mi=bisect.bisect_right(map_times,t)-1
            if mi<0 or 'pose' not in state:raise ValueError('Missing past-only map/pose')
            mt,h=data['maps'][mi];pose=state['pose'];xyz,values,valid,channels=voxel_field(h,pose)
            v=values.reshape(-1);p=xyz.reshape(-1,3);ok=valid.reshape(-1)
            rgb=np.column_stack([np.interp(np.nan_to_num(v),[0,.5,1],[1.,1.,.12]),np.interp(np.nan_to_num(v),[0,.5,1],[.15,.85,.7]),np.interp(np.nan_to_num(v),[0,.5,1],[.1,.15,.3])])
            for n,pub in enumerate(pubs):
                keep=ok&masks[n].reshape(-1)
                cubes=marker(Marker.CUBE_LIST,0,p[keep],(1,1,1,1),(CELL*.98,CELL*.98,CELL*.98))
                alpha=args.alpha if n==0 else args.cut_alpha
                cubes.colors=[ColorRGBA(r=float(c[0]),g=float(c[1]),b=float(c[2]),a=alpha) for c in rgb[keep]]
                markers=[cubes]+static[n]
                path=np.asarray(state.get('execution',[]),float).reshape(-1,4)
                if len(path)>1:
                    angles=np.mod(path[:,3],2*np.pi);pp=np.column_stack([path[:,0]-pose[0],path[:,1]-pose[1],angles/(2*np.pi)*HEIGHT])
                    segments=np.stack([pp[:-1],pp[1:]],axis=1);inside=(np.abs(segments[:,:,:2])<=SIDE*CELL/2).all(axis=(1,2));inside&=np.abs(np.diff(angles))<=np.pi
                    line=segments[inside].reshape(-1,3)
                else:line=np.zeros((0,3))
                markers.append(marker(Marker.LINE_LIST,1,line,(.1,1.,.95,1.),(.055,0,0)))
                z=(pose[3]%(2*np.pi))/(2*np.pi)*HEIGHT
                markers.append(marker(Marker.ARROW,2,[(0,0,z),(.7*math.cos(pose[3]),.7*math.sin(pose[3]),z)],(1.,1.,1.,1.),(.055,.13,.18)))
                pub.publish(MarkerArray(markers=markers))
            rclpy.spin_once(node,timeout_sec=0)
            time.sleep(.35 if frame else 1.2)
            im=ImageGrab.grab(xdisplay=args.display).convert('RGB');assert im.size==(1920,1080)
            d=ImageDraw.Draw(im);d.rectangle((0,0,1920,67),fill='#0b121b');d.rectangle((0,868,1920,1080),fill='#0b121b')
            d.text((22,10),'HT：填满 XYθ 的三维体素网格',font=large,fill='white')
            d.text((1230,17),f'既有Campus仿真回放  t={t:.1f}s  ×{args.speed:g}',font=small,fill='#91dbff')
            for n,label in enumerate(['完整体素体积：半透明 + 单元边界','剖开一个角：显示内部三维格子']):
                x=n*960+20;d.text((x,875),label,font=large,fill='white')
                d.text((x,920),'32 × 32 × 32 格；Δx=Δy=0.30m，Δθ=11.25°',font=small,fill='#e1ebf6')
                d.text((x,955),'颜色取原八方向最近通道；不是32个独立HT预测',font=small,fill='#becddd')
                d.text((x,990),'绿：高分  红：低分  空格：缺有效HT；青线：记录中的执行路径',font=small,fill='#becddd')
            d.text((22,1030),'θ为角度，竖轴经显示缩放；每个格子有完整角度范围。仅离线显示，不重新规划、不发车辆控制。',font=small,fill='#91a8c2')
            enc.stdin.write(im.tobytes());captures.append(dict(frame=frame,time_s=t,map_time_s=mt,valid_voxels=int(ok.sum())))
            if frame in (0,len(timeline)-1):im.save(out/f'frame_{frame:04d}.jpg',quality=94)
            if frame==0:
                np.savez_compressed(out/'voxel_snapshot.npz',xyz=xyz,values=values,valid=valid,theta_channels=channels,native_scores=h['p'],native_valid=h['valid'],native_x=h['x'],native_y=h['y'],pose=pose)
            if frame%20==0:print('Voxel grid frame',frame,'/',len(timeline),'source',t,flush=True)
        finish();assert enc.returncode==0
        meta=dict(source=data['source'],source_bag_metadata_sha256=data['source_bag_metadata_sha256'],base_cache_sha256=data['base_cache_sha256'],
            shape=[SIDE,SIDE,HEADINGS],xy_cell_m=CELL,theta_cell_deg=360/HEADINGS,theta_channels=channels.tolist(),cube_display_size=CELL*.98,
            voxel_fill=.98,full_alpha=args.alpha,cutaway_alpha=args.cut_alpha,source_interval_s=[args.start,args.end],fps=args.fps,frames=len(timeline),speed=args.speed,
            video_duration_s=len(timeline)/args.fps,publishers=topics,navigation_control_published=False,source_resolution_m=h['source_resolution_m'],
            score_policy='Nearest original native XY cell at voxel center; nearest original45deg HT channel at angular-bin center. No score interpolation. Unknown remains uncolored. Display cells do not prove whole-cell motion feasibility.',
            captures=captures,video_sha256=sha(dest))
        (out/'capture.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2)+'\n')

def main():
    p=argparse.ArgumentParser();p.add_argument('--prepare',action='store_true');p.add_argument('--base-cache',type=Path);p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path)
    p.add_argument('--start',type=float,default=30);p.add_argument('--end',type=float,default=150);p.add_argument('--speed',type=float,default=4);p.add_argument('--fps',type=int,default=10)
    p.add_argument('--display',default=':97');p.add_argument('--alpha',type=float,default=.045);p.add_argument('--cut-alpha',type=float,default=.14)
    p.add_argument('--encoder',type=Path,default=Path('/home/lzz/.cache/ht-report-tools/python/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'))
    p.add_argument('--xvfb',type=Path,default=Path('/home/lzz/my test/HT_Explo-fixposition/.git/experiment-tools/xvfb/root/usr/bin/Xvfb'))
    a=p.parse_args();frame_times(a.start,a.end,a.speed,a.fps)
    if not (0<a.alpha<=1 and 0<a.cut_alpha<=1):raise ValueError('Invalid opacity')
    if a.prepare:
        if a.base_cache is None:raise ValueError('--base-cache required')
        prepare(a.base_cache,a.cache,a.start,a.end)
    else:
        if a.output is None:raise ValueError('--output required')
        replay(a)

if __name__=='__main__':main()
