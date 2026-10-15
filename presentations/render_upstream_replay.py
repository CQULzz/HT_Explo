#!/usr/bin/env python3
"""Build synchronized real-camera/elevation/HT artifacts from replay outputs."""
import argparse,csv,json
from pathlib import Path
import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize

plt.rcParams.update({'font.family':'Noto Sans CJK JP','axes.unicode_minus':False})

def main():
    ap=argparse.ArgumentParser();ap.add_argument('folder',type=Path);ap.add_argument('--skip-video',action='store_true');ap.add_argument('--driver',choices=['original','current'],default='original');a=ap.parse_args();folder=a.folder.resolve()
    driver_title='CURRENT HT XYtheta DRIVE' if a.driver=='current' else 'ORIGINAL TARE DRIVE'
    driver_cn='当前 HT 控车' if a.driver=='current' else '原版 TARE'
    index=json.loads((folder/'snapshots/index.json').read_text());origin=json.loads((folder/'original/measurement_started.json').read_text())['wall_time']
    frames=index['frames'];times=np.array([f['ht_stamp'] for f in frames]);duration=json.loads((folder/'record_summary.json').read_text())['duration_s']
    out=folder/'visuals';out.mkdir(exist_ok=True)
    if not frames:raise RuntimeError('No replay HT snapshots were captured')
    # Re-align camera frames offline by the original bag receive timestamps.
    # The live replay camera can advance while HT inference is still running.
    import rosbag2_py
    from rclpy.serialization import deserialize_message
    from sensor_msgs.msg import Image
    from cv_bridge import CvBridge
    camera_reader=rosbag2_py.SequentialReader();camera_reader.open(rosbag2_py.StorageOptions(uri=str(folder/'original_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));camera_reader.set_filter(rosbag2_py.StorageFilter(topics=['/camera/image_raw']))
    camera_bridge=CvBridge();aligned_camera={};camera_offsets=[];previous=None;previous_time=None;target=0
    while camera_reader.has_next() and target<len(times):
        _,message,t_ns=camera_reader.read_next();t=t_ns/1e9
        image=camera_bridge.imgmsg_to_cv2(deserialize_message(message,Image),'bgr8')
        while target<len(times) and times[target]<=t:
            old=previous is not None and abs(previous_time-times[target])<abs(t-times[target])
            aligned_camera[target]=(previous if old else image).copy()
            camera_offsets.append(float((previous_time if old else t)-times[target]));target+=1
        previous=image;previous_time=t
    while target<len(times):
        aligned_camera[target]=previous.copy();camera_offsets.append(float(previous_time-times[target]));target+=1
    (out/'camera_alignment.json').write_text(json.dumps({'method':'nearest original bag image receive time to HT map timestamp','offset_abs_p95_s':float(np.percentile(abs(np.array(camera_offsets)),95)),'offset_abs_max_s':float(max(abs(np.array(camera_offsets))))},indent=2)+'\n')
    rows=list(csv.DictReader((folder/'original/timeseries.csv').open()))
    pose_t=np.array([float(r['t_s']) for r in rows]);pose_x=np.array([float(r['x_m']) for r in rows]);pose_y=np.array([float(r['y_m']) for r in rows]);pose_yaw=np.unwrap([float(r['yaw_rad']) for r in rows])
    def robot_at(i):return np.array([np.interp(times[i]-origin,pose_t,pose_x),np.interp(times[i]-origin,pose_t,pose_y),np.interp(times[i]-origin,pose_t,pose_yaw)])
    def load(i):return np.load(folder/'snapshots'/frames[i]['file'])
    def plane(ax,z,g,cmap='terrain',limits=None):
        cx,cy,r=g;n,m=z.shape;ext=[cx-n*r/2,cx+n*r/2,cy-m*r/2,cy+m*r/2]
        return ax.imshow(z[::-1,::-1].T,origin='lower',extent=ext,cmap=cmap,interpolation='nearest',vmin=limits[0] if limits else None,vmax=limits[1] if limits else None)
    selected=[int(np.argmin(abs(times-(origin+t)))) for t in np.linspace(0,duration-5,6)]
    fig,axes=plt.subplots(2,6,figsize=(21,7),constrained_layout=True)
    for col,i in enumerate(selected):
        with load(i) as d:
            axes[0,col].imshow(cv2.cvtColor(aligned_camera[i],cv2.COLOR_BGR2RGB));axes[0,col].axis('off');axes[0,col].set_title(f'{times[i]-origin:.0f} s：{driver_cn}场景')
            plane(axes[1,col],d['history_elevation'],d['history_geometry']);axes[1,col].plot(*robot_at(i)[:2],'r+',ms=9);axes[1,col].set_title('同期历史局部高程');axes[1,col].set_xlabel('Map X (m)')
    fig.suptitle(f'{driver_cn}实际行驶与同期高程（各图色阶自动缩放，仅比较结构）')
    fig.savefig(out/'camera_elevation_timeline.png',dpi=170);plt.close(fig)
    # Late-run complete eight-direction probability map, paired with recorded camera.
    i=selected[-1]
    with load(i) as d:
        fig,axes=plt.subplots(2,4,figsize=(16,9),constrained_layout=True)
        cmap=plt.get_cmap('RdYlGn').copy();cmap.set_bad('#bfc3c6')
        for k,ax in enumerate(axes.flat):
            z=np.where(d['ht_ht_valid']>=.5,d[f'ht_ht_dir_{k}'],np.nan);im=plane(ax,z,d['ht_geometry'],cmap,(0,1));ax.plot(*robot_at(i)[:2],'b+',ms=8);ax.set(title=f'HT 通道 {k}（实际角度待标定）',xlabel='Map X (m)',ylabel='Map Y (m)')
        fig.colorbar(im,ax=axes,label='HT 可通过概率');fig.suptitle(f'{driver_cn}：t={times[i]-origin:.1f} s，蓝点为车辆')
        fig.savefig(out/'late_eight_direction_ht.png',dpi=170);plt.close(fig)
        cv2.imwrite(str(out/'late_camera.png'),aligned_camera[i])
    metrics=[]
    for f in frames:
        with np.load(folder/'snapshots'/f['file']) as d:
            valid=d['ht_ht_valid']>=.5;p=np.stack([d[f'ht_ht_dir_{k}'] for k in range(8)])
            metrics.append({'t_s':f['ht_stamp']-origin,'valid_fraction':float(valid.mean()),'all_directions_pass_fraction':float((valid&np.all(p>=.5,axis=0)).mean()),'camera_offset_s':f['camera_offset_s']})
    (out/'map_metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    rows=list(csv.DictReader((folder/'original/timeseries.csv').open()));fig,axes=plt.subplots(2,1,figsize=(11,7),constrained_layout=True)
    axes[0].plot([float(r['t_s']) for r in rows],[float(r['distance_m']) for r in rows]);axes[0].set(ylabel='累计里程（m）',title=f'{driver_cn}行驶与 HT 输出')
    axes[1].plot([r['t_s'] for r in metrics],[r['valid_fraction'] for r in metrics],label='HT 有观测支撑比例');axes[1].plot([r['t_s'] for r in metrics],[r['all_directions_pass_fraction'] for r in metrics],label='八方向均 ≥0.5 的比例（未膨胀）');axes[1].set(xlabel='实验时间（s）',ylabel='当前局部图面积比例',ylim=(0,1));axes[1].legend()
    for ax in axes:ax.grid(alpha=.2)
    fig.savefig(out/'replay_metrics.png',dpi=180);plt.close(fig)
    if not a.skip_video:
        import rosbag2_py
        from rclpy.serialization import deserialize_message
        from sensor_msgs.msg import Image
        from cv_bridge import CvBridge
        from nav_msgs.msg import Path as RosPath
        from std_msgs.msg import String, Bool
        events=[]
        if a.driver=='current':
            control=rosbag2_py.SequentialReader();control.open(rosbag2_py.StorageOptions(uri=str(folder/'original_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));control.set_filter(rosbag2_py.StorageFilter(topics=['/ht_xytheta_path','/ht_execution_status','/ht_navigation_allowed']))
            while control.has_next():
                topic,payload,ns=control.read_next()
                if topic=='/ht_xytheta_path':
                    msg=deserialize_message(payload,RosPath);value=np.array([[p.pose.position.x,p.pose.position.y,np.arctan2(2*(p.pose.orientation.w*p.pose.orientation.z+p.pose.orientation.x*p.pose.orientation.y),1-2*(p.pose.orientation.y**2+p.pose.orientation.z**2))] for p in msg.poses])
                elif topic=='/ht_execution_status':value=deserialize_message(payload,String).data
                else:value=deserialize_message(payload,Bool).data
                events.append((ns/1e9,topic,value))
        event_i=0;active_path=np.empty((0,3));execution_status='WAITING';allowed=False;permission_time=-1e20
        reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(folder/'original_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));reader.set_filter(rosbag2_py.StorageFilter(topics=['/camera/image_raw']))
        video_name='current_ht_exploration.mp4' if a.driver=='current' else 'original_tare_cupy_ht_sync.mp4'
        writer=cv2.VideoWriter(str(out/video_name),cv2.VideoWriter_fourcc(*'mp4v'),10,(1920,1080));bridge=CvBridge();next_time=origin;cached=-1;base=None;count=0
        if not writer.isOpened():raise RuntimeError('Video encoder failed to open')
        trail_t=np.array([float(r['t_s']) for r in rows]);trail_xy=np.array([[float(r['x_m']),float(r['y_m'])] for r in rows])
        velocity=np.gradient(trail_xy,trail_t,axis=0)
        palette=(plt.get_cmap('RdYlGn')(np.linspace(0,1,256))[:,:3][:,::-1]*255).astype(np.uint8)
        while reader.has_next():
            topic,data,t_ns=reader.read_next();t=t_ns/1e9
            if t<next_time or t>origin+duration:continue
            while event_i<len(events) and events[event_i][0]<=t:
                et,topic,value=events[event_i]
                if topic=='/ht_xytheta_path':active_path=value
                elif topic=='/ht_execution_status':execution_status=value
                else:allowed=value;permission_time=et
                event_i+=1
            i=max(0,int(np.searchsorted(times,t,side='right')-1))
            if i!=cached:
                with load(i) as d:
                    base=np.full((1080,1920,3),25,np.uint8)
                    robot=robot_at(i)
                    vel=np.array([np.interp(times[i]-origin,trail_t,velocity[:,axis]) for axis in [0,1]])
                    trail=trail_xy[(trail_t<=times[i]-origin)&(trail_t>=times[i]-origin-30)]
                    valid=d['ht_ht_valid']>=.5
                    ht_geometry=d['ht_geometry'].copy();ht_shape=valid.shape
                    for k in range(8):
                        z=d[f'ht_ht_dir_{k}'][::-1,::-1].T;colors=palette[np.clip(np.nan_to_num(z)*255,0,255).astype(np.uint8)];colors[~valid[::-1,::-1].T]=180
                        x=650+(k%4)*315;y=90+(k//4)*375;side=300
                        base[y:y+side,x:x+side]=cv2.resize(colors,(side,side),interpolation=cv2.INTER_NEAREST)
                        cx,cy,res=d['ht_geometry'];n,m=valid.shape
                        px=int(x+side*((robot[0]-cx)/(n*res)+.5));py=int(y+side*(.5-(robot[1]-cy)/(m*res)))
                        cv2.circle(base,(px,py),5,(255,100,20),-1)
                        if len(trail)>1:
                            uv=np.c_[side*((trail[:,0]-cx)/(n*res)+.5),side*(.5-(trail[:,1]-cy)/(m*res))].astype(np.int32)
                            cv2.polylines(base[y:y+side,x:x+side],[uv],False,(255,110,30),1)
                        heading=np.array([np.cos(robot[2]),np.sin(robot[2])])*.8
                        target=(int(px+side*heading[0]/(n*res)),int(py-side*heading[1]/(m*res)))
                        cv2.arrowedLine(base,(px,py),target,(10,10,10),2,tipLength=.3)
                        if np.linalg.norm(vel)>.1:
                            direction=vel/np.linalg.norm(vel)*.8
                            target=(int(px+side*direction[0]/(n*res)),int(py-side*direction[1]/(m*res)))
                            cv2.arrowedLine(base,(px,py),target,(230,220,10),2,tipLength=.3)
                        cv2.putText(base,f'HT channel {k}',(x,y-15),cv2.FONT_HERSHEY_SIMPLEX,.7,(230,230,230),1)
                    z=d['history_elevation'][::-1,::-1].T;good=np.isfinite(z);lo,hi=np.percentile(z[good],[2,98]) if good.any() else (0,1);norm=np.clip((z-lo)/max(hi-lo,.001),0,1);colors=(plt.get_cmap('terrain')(np.nan_to_num(norm))[:,:,:3][:,:,::-1]*255).astype(np.uint8);colors[~good]=170
                    base[440:1040,20:620]=cv2.resize(colors,(600,600),interpolation=cv2.INTER_NEAREST)
                    if len(trail)>1:
                        cx,cy,res=d['history_geometry'];n,m=z.shape;uv=np.c_[600*((trail[:,0]-cx)/(n*res)+.5),600*(.5-(trail[:,1]-cy)/(m*res))].astype(np.int32)
                        cv2.polylines(base[440:1040,20:620],[uv],False,(255,110,30),2)
                    cv2.putText(base,'HISTORICAL LOCAL ELEVATION',(20,428),cv2.FONT_HERSHEY_SIMPLEX,.65,(230,230,230),1)
                    cv2.putText(base,f'Height color range: {lo:.2f} to {hi:.2f} m (auto)',(20,1065),cv2.FONT_HERSHEY_SIMPLEX,.55,(230,230,230),1)
                    cv2.putText(base,f'XY=({robot[0]:.1f}, {robot[1]:.1f}) m  Yaw={np.degrees(robot[2])%360:.1f} deg',(650,825),cv2.FONT_HERSHEY_SIMPLEX,.75,(230,230,230),1)
                    cv2.putText(base,'Blue: trail | Black: heading | Cyan: motion',(650,865),cv2.FONT_HERSHEY_SIMPLEX,.5,(230,230,230),1)
                    cv2.putText(base,'World up=+Y, right=+X | Gray: unknown',(650,900),cv2.FONT_HERSHEY_SIMPLEX,.5,(230,230,230),1)
                    cv2.putText(base,'HT physical channel angles: calibration pending',(650,935),cv2.FONT_HERSHEY_SIMPLEX,.48,(230,230,230),1)
                cached=i
            frame=base.copy();camera=bridge.imgmsg_to_cv2(deserialize_message(data,Image),'bgr8');frame[72:410,20:620]=cv2.resize(camera,(600,338))
            mode='LIVE-COMPUTED MAPS' if a.driver=='current' else 'OFFLINE CuPy + HT'
            cv2.putText(frame,f'{driver_title} | {mode} | t={t-origin:.1f}s | Map age={max(0,t-times[i]):.2f}s',(20,38),cv2.FONT_HERSHEY_SIMPLEX,.75,(240,240,240),1)
            if a.driver=='current':
                for k in range(8):
                    if len(active_path)>1:
                        cx,cy,res=ht_geometry;n,m=ht_shape
                        x=650+(k%4)*315;y=90+(k//4)*375
                        uv=np.c_[300*((active_path[:,0]-cx)/(n*res)+.5),300*(.5-(active_path[:,1]-cy)/(m*res))].astype(np.int32)
                        cv2.polylines(frame[y:y+300,x:x+300],[uv],False,(210,50,230),2)
                cv2.putText(frame,f'Status: {execution_status}',(650,970),cv2.FONT_HERSHEY_SIMPLEX,.53,(235,235,235),1)
                age_label=f'{t-permission_time:.2f}s' if permission_time>0 else 'N/A'
                expired=' EXPIRED' if permission_time>0 and t-permission_time>1.5 else ''
                cv2.putText(frame,f'Allowed={allowed}  Age={age_label}{expired}',(650,1000),cv2.FONT_HERSHEY_SIMPLEX,.5,(235,235,235),1)
                cv2.putText(frame,'Magenta: XY projection of actual published plan',(650,1025),cv2.FONT_HERSHEY_SIMPLEX,.46,(210,50,230),1)
                # This inset uses actual path pose orientations, not a shadow
                # planner or an assumed correspondence of HT channel angles.
                inset=frame[795:1030,1290:1900];inset[:]=(30,30,30)
                cv2.putText(inset,'ACTUAL XY-theta PLAN',(10,22),cv2.FONT_HERSHEY_SIMPLEX,.5,(230,230,230),1)
                def project(px,py,theta):
                    dx=px-robot[0];dy=py-robot[1]
                    return (int(300+24*dx+14*dy),int(210-4*dx-8*dy-100*(theta+np.pi)/(2*np.pi)))
                for angle in np.linspace(-np.pi,np.pi,9):
                    for axis in [-4,0,4]:
                        aa=project(robot[0]+axis,robot[1]-4,angle);bb=project(robot[0]+axis,robot[1]+4,angle);cv2.line(inset,aa,bb,(60,60,60),1)
                        aa=project(robot[0]-4,robot[1]+axis,angle);bb=project(robot[0]+4,robot[1]+axis,angle);cv2.line(inset,aa,bb,(60,60,60),1)
                if len(active_path)>1:
                    pp=[project(*pose) for pose in active_path]
                    for j in range(len(pp)-1):
                        if abs(active_path[j+1,2]-active_path[j,2])<np.pi:cv2.line(inset,pp[j],pp[j+1],(210,50,230),2)
                cv2.circle(inset,project(robot[0],robot[1],(robot[2]+np.pi)%(2*np.pi)-np.pi),4,(60,220,100),-1)
                cv2.putText(inset,'Local XY +/-4m; theta -180..180 (periodic)',(10,230),cv2.FONT_HERSHEY_SIMPLEX,.4,(190,190,190),1)
            cv2.putText(frame,'Green: high probability  Red: low  Gray: unsupported',(650,1040),cv2.FONT_HERSHEY_SIMPLEX,.65,(230,230,230),1)
            writer.write(frame);count+=1;next_time+=.1
        writer.release();(out/'video_metadata.json').write_text(json.dumps({'fps':10,'frames':count,'duration_s':count/10,'resolution':[1920,1080],'HT_panel_pixels':[300,300],'HT_resampling':'nearest; each panel larger than native 241x241','camera_alignment':'original bag receive timestamp; latest preceding replay HT snapshot','HT_snapshot_interval_median_s':float(np.median(np.diff(times)))},indent=2)+'\n')
    print(out)
if __name__=='__main__':main()
