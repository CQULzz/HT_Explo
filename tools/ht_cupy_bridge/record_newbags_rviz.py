#!/usr/bin/env python3
"""Publish saved real outputs to four actual RViz windows and record X11.

Only visualization_msgs are published in a private ROS domain. Geometry and
probabilities are read from the reconstruction NPZs. Unknown is gray. Display
decimation is explicit; the inference maps are never downsampled or edited.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import time

import imageio_ffmpeg
import mss
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA
from visualization_msgs.msg import Marker, MarkerArray
import yaml


def point(p):return Point(x=float(p[0]),y=float(p[1]),z=float(p[2]))
def color(c):return ColorRGBA(r=float(c[0]),g=float(c[1]),b=float(c[2]),a=float(c[3]))
def marker(id,typ,frame):
    m=Marker();m.header.frame_id=frame;m.ns='offline';m.id=id;m.type=typ;m.action=Marker.ADD;m.pose.orientation.w=1.;return m


def terrain_colors(z):
    # One common absolute-height scale for both recordings; no auto contrast.
    u=np.clip((np.asarray(z)+.85)/1.9,0,1)
    return np.column_stack((np.clip(2*u,0,1),np.clip(2-2*u,0,1),np.clip(1-2*u,0,1),np.ones(len(u))))


def probability_colors(p,a=1.):
    p=np.clip(np.nan_to_num(p,nan=0.),0,1)
    return np.column_stack((np.clip(2-2*p,0,1),np.clip(2*p,0,1),np.full(len(p),.12),np.full(len(p),a)))


def cells(id,xyz,colors,size,frame,alpha=1.,typ=Marker.CUBE_LIST):
    m=marker(id,typ,frame);m.scale.x,m.scale.y,m.scale.z=map(float,size);m.color.a=float(alpha)
    m.points=[point(p) for p in xyz];m.colors=[color(c) for c in colors];return m


def robot_marker(id,robot,frame,origin):
    x,y,z,yaw=robot;corners=np.array([[-.4825,-.21],[.4825,-.21],[.4825,.21],[-.4825,.21],[-.4825,-.21]])
    rot=np.array([[math.cos(yaw),-math.sin(yaw)],[math.sin(yaw),math.cos(yaw)]])
    xy=corners@rot.T+np.array([x,y])-origin
    m=marker(id,Marker.LINE_STRIP,frame);m.scale.x=.05;m.color=color([.15,.8,1.,1.]);m.points=[point([*p,z+2.]) for p in xy]
    ar=marker(id+1,Marker.ARROW,frame);ar.scale.x=.07;ar.scale.y=.17;ar.scale.z=.2;ar.color=color([.15,.8,1.,1.]);ar.points=[point([x-origin[0],y-origin[1],z+2.]),point([x-origin[0]+math.cos(yaw),y-origin[1]+math.sin(yaw),z+2.])]
    return [m,ar]


def xy_grid(z,center,r):
    i,j=np.indices(z.shape);return np.stack((center[0]+(z.shape[0]/2-i-.5)*r,center[1]+(z.shape[1]/2-j-.5)*r),axis=-1)


def text(id,s,pos,frame,scale=.65):
    m=marker(id,Marker.TEXT_VIEW_FACING,frame);m.text=s;m.pose.position=point(pos);m.scale.z=scale;m.color=color([.9,.95,1.,1.]);return m


def views(z,trajectory):
    robot=z['robot'];origin=robot[:2];r=float(z['resolution']);result=[]
    gp=z['global_xyz'];m=[cells(0,gp,terrain_colors(gp[:,2]),[.04,.04,.02],'global',typ=Marker.POINTS)]
    m+=robot_marker(2,robot,'global',np.zeros(2))
    tr=marker(4,Marker.LINE_STRIP,'global');tr.scale.x=.055;tr.color=color([.1,.75,1.,1.]);tr.points=[point([p[0],p[1],p[2]+1.7]) for p in trajectory];m.append(tr);result.append(m)
    h=z['local_elevation'];xy=xy_grid(h,z['local_center'],r)-origin;known=np.isfinite(h)
    xyz=np.column_stack((xy[known],h[known]))
    m=[cells(0,xyz,terrain_colors(xyz[:,2]),[r,r,.015],'local',typ=Marker.POINTS)]+robot_marker(2,robot,'local',origin)
    result.append(m)
    # Eight separate maps with the exact saved world heading channel labels.
    valid=z['ht_valid'][::2,::2]>=.5;xy=xy_grid(z['ht_valid'],z['center'],r)[::2,::2]-z['center'];m=[]
    for k in range(8):
        shift=np.array([(k%4-1.5)*11.,(.5-k//4)*12.])
        bg=marker(10*k,Marker.CUBE,'directions');bg.pose.position=point([*shift,-.025]);bg.scale.x=bg.scale.y=9.64;bg.scale.z=.02;bg.color=color([.22,.25,.27,1.]);m.append(bg)
        xy2=xy[valid]+shift;xyz=np.column_stack((xy2,np.zeros(len(xy2))))
        m.append(cells(10*k+1,xyz,probability_colors(z['ht_dir_'+str(k)][::2,::2][valid]),[.08,.08,.02],'directions'))
        m.append(text(10*k+2,f'{k*45} deg',[shift[0],shift[1]+5.4,.2],'directions',.7))
        rbt=robot.copy();rbt[:2]=robot[:2]-z['center']+shift
        m+=robot_marker(10*k+3,rbt,'directions',np.zeros(2))
    result.append(m)
    # Contiguous theta bins, 45deg each, no empty layer gaps; display-only 4x decimation.
    valid=z['ht_valid'][::4,::4]>=.5;xy=xy_grid(z['ht_valid'],z['center'],r)[::4,::4]-origin
    xx=[];cc=[]
    for k in range(8):
        xx.append(np.column_stack((xy[valid],np.full(valid.sum(),(k+.5)*.8))))
        cc.append(probability_colors(z['ht_dir_'+str(k)][::4,::4][valid],.055))
    m=[cells(0,np.concatenate(xx),np.concatenate(cc),[.16,.16,.8],'voxel',.055)]
    line=marker(1,Marker.LINE_LIST,'voxel');line.scale.x=.006;line.color=color([.55,.65,.72,.12]);bounds=np.array(z['center'])-origin
    lo=bounds-4.82;hi=bounds+4.82
    # Wire grid at 0.64m for readable cell boundaries, theta boundaries every45deg.
    for x in np.linspace(lo[0],hi[0],16):
        for y in np.linspace(lo[1],hi[1],16):line.points.extend([point([x,y,0]),point([x,y,6.4])])
    for h in np.arange(9)*.8:
        for x in np.linspace(lo[0],hi[0],16):line.points.extend([point([x,lo[1],h]),point([x,hi[1],h])])
        for y in np.linspace(lo[1],hi[1],16):line.points.extend([point([lo[0],y,h]),point([hi[0],y,h])])
        m.append(text(10+int(h*10),f'{int(round(h/.8))*45} deg',[lo[0]-.7,hi[1]+.5,h],'voxel',.26))
    m.append(line);result.append(m)
    return [MarkerArray(markers=x) for x in result]


def configuration(path,topic,frame,index,center,global_distance):
    camera={'Class':'rviz_default_plugins/Orbit','Name':'Current View','Target Frame':'<Fixed Frame>',
        'Distance':18.,'Pitch':1.15,'Yaw':4.71,'Focal Point':{'X':0.,'Y':0.,'Z':-.3},
        'Near Clip Distance':.01,'Focal Shape Fixed Size':True,'Focal Shape Size':.05,
        'Invert Z Axis':False,'Value':'Orbit (rviz_default_plugins)'}
    if index==0:camera.update(Distance=global_distance,Pitch=1.1,**{'Focal Point':dict(zip(['X','Y','Z'],map(float,center)))})
    if index==2:camera.update(Distance=33.,Pitch=1.5707,**{'Focal Point':{'X':0.,'Y':0.,'Z':0.}})
    if index==3:camera.update(Distance=22.,Pitch=.65,Yaw=4.,**{'Focal Point':{'X':0.,'Y':0.,'Z':3.2}})
    data={'Panels':[],'Visualization Manager':{'Class':'','Enabled':True,'Name':'root','Value':True,'Transformation':{'Current':{'Class':'rviz_default_plugins/TF'}},'Global Options':{'Background Color':'16; 24; 29','Fixed Frame':frame,'Frame Rate':15},
        'Displays':[{'Class':'rviz_default_plugins/MarkerArray','Enabled':True,'Name':'Actual offline results','Value':True,
            'Topic':{'Depth':1,'Durability Policy':'Transient Local','History Policy':'Keep Last','Reliability Policy':'Reliable','Value':topic}}],
        'Views':{'Current':camera,'Saved':[]}},'Window Geometry':{'Width':1280,'Height':720,'X':(index%2)*1280,'Y':(index//2)*720}}
    path.write_text(yaml.safe_dump(data,sort_keys=False))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--label',required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    result=json.loads((a.input/'RESULTS.json').read_text());rows=[x for x in result['frames'] if x['output']]
    first=np.load(a.input/'frames'/rows[0]['file']);final=np.load(a.input/'frames'/rows[-1]['file'])
    bounds=final['global_xyz'][:,:2]
    center=np.r_[(bounds.min(0)+bounds.max(0))/2,-.3]
    global_distance=max(17.,float(np.linalg.norm(np.ptp(bounds,axis=0))*.5/math.sin(math.pi/8)*1.08))
    rclpy.init();node=Node('offline_rviz_results_only');qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
    topics=['/offline/global','/offline/local','/offline/directions','/offline/voxel'];frames=['global','local','directions','voxel']
    pubs=[node.create_publisher(MarkerArray,t,qos) for t in topics]
    processes=[];logs=[];encoder=None;last=-1;trajectory=[];captures=[]
    font=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',26)
    small=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',20)
    titles=['全局历史高程图 | 保留已观测区域，显示真实高度','局部高程图 | 11.64 × 11.64 m，历史地图裁剪','HT 八方向可通过性 | 世界坐标系 0°～315°','HT XYθ 空间 | 半透明、连续排列的体素格']
    try:
        for i,(topic,frame) in enumerate(zip(topics,frames)):
            config=a.output/f'view_{i}.rviz';configuration(config,topic,frame,i,center,global_distance)
            f=(a.output/f'rviz_{i}.log').open('w');logs.append(f)
            env=os.environ.copy();env['DISPLAY']=':98';env['QT_X11_NO_MITSHM']='1'
            processes.append(subprocess.Popen(['/opt/ros/jazzy/bin/rviz2','-d',str(config),'-geometry',f'1280x720+{i%2*1280}+{i//2*720}'],env=env,stdout=f,stderr=subprocess.STDOUT))
        for _ in range(150):
            if any(c.poll() is not None for c in processes):raise RuntimeError('RViz exited; see logs')
            if all(p.get_subscription_count()>0 for p in pubs):break
            time.sleep(.1)
        else:raise RuntimeError('Missing RViz subscriptions')
        messages=views(first,[first['robot']]);
        for pub,m in zip(pubs,messages):pub.publish(m)
        time.sleep(3.)
        with mss.MSS(display=':98') as screen:
            Image.frombytes('RGB',(2560,1440),screen.grab({'left':0,'top':0,'width':2560,'height':1440}).rgb).save(a.output/'raw_rviz_preview.png')
            target=a.output/(a.label+'_RViz.mp4')
            cmd=[imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-loglevel','error','-n','-f','rawvideo','-pix_fmt','rgb24','-s','2560x1440','-r','10','-i','-','-an','-c:v','libx264','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
            encoder=subprocess.Popen(cmd,stdin=subprocess.PIPE,stderr=(a.output/'encoder.log').open('w'))
            end=result['scans'][-1]['stamp_ns']/1e9-result['scans'][0]['stamp_ns']/1e9
            offset=(rows[0]['stamp_ns']-result['scans'][0]['stamp_ns'])/1e9
            begun=time.monotonic();index=0
            for f in range(math.ceil(end*10)+1):
                t=f/10
                while index+1<len(rows) and rows[index+1]['t_s']+offset<=t:index+=1
                if index!=last:
                    z=np.load(a.input/'frames'/rows[index]['file']);trajectory.append(z['robot'].copy())
                    messages=views(z,trajectory)
                    for pub,m in zip(pubs,messages):pub.publish(m)
                    # A source-timestamp hold, allowing render/upload before capture.
                    time.sleep(.13);last=index
                wait=begun+t-time.monotonic()
                if wait>0:time.sleep(wait)
                im=Image.frombytes('RGB',(2560,1440),screen.grab({'left':0,'top':0,'width':2560,'height':1440}).rgb);draw=ImageDraw.Draw(im)
                for k,title in enumerate(titles):
                    x=k%2*1280;y=k//2*720
                    draw.rectangle((x,y,x+1280,y+82),fill=(16,24,29));draw.text((x+18,y+6),title,fill=(235,245,250),font=font)
                    draw.text((x+18,y+41),f'{a.label} | 点云时间 t={t:05.1f}s | 实际 RViz 离线重算回放',fill=(168,195,212),font=small)
                for x,y,txt in [(18,688,'高度色标：−0.85 m 蓝 → +1.05 m 红 | 青色轮廓/线：录包位姿'),(1298,688,'高程网格 0.04 m | 空白：未知 | 显示未补点，未平滑'),(18,1408,'T：红 0 → 黄 0.5 → 绿 1 | 灰：无效 | 显示网格 0.08 m'),(1298,1408,'竖轴是方向 θ，不是高度 | 体素 0.16 m × 0.16 m × 45° | α=0.055')]:
                    draw.rectangle((x-10,y-3,x+1260,y+30),fill=(16,24,29));draw.text((x,y),txt,fill=(205,220,230),font=small)
                if f in {0,int(end*5),int(end*10)}:im.save(a.output/f'preview_{f:04d}.png')
                encoder.stdin.write(im.tobytes())
                captures.append({'video_frame':f,'source_time_s':t,'result_frame':rows[index]['file'],'source_stamp_ns':rows[index]['stamp_ns']})
            encoder.stdin.close();status=encoder.wait();assert status==0,status;encoder=None
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-v','error','-i',str(target),'-f','null','-'],check=True,stdout=subprocess.DEVNULL)
        (a.output/'VIDEO_CHECK.json').write_text(json.dumps({'actual_rviz':True,'size':[2560,1440],'fps':10,'frames':len(captures),'source_duration_s':end,'full_decode_passed':True,'capture_manifest':captures,'command':cmd,'limitations':'Fixed input replay, no exploration/control or ARM runtime validation'},indent=2)+'\n')
        print(target,flush=True)
    finally:
        if encoder is not None:encoder.kill();encoder.wait()
        for c in processes:
            c.terminate()
        for c in processes:
            try:c.wait(timeout=10)
            except subprocess.TimeoutExpired:c.kill();c.wait()
        for f in logs:f.close()
        node.destroy_node();rclpy.try_shutdown()


if __name__=='__main__':main()
