from pathlib import Path
import json,time,subprocess
r=Path('/mnt/d/HT-Execution-300s/rviz_video_20261114')
(r/'left_title.txt').write_text('整体探索范围与车辆轨迹',encoding='utf-8')
(r/'right_title.txt').write_text('车辆跟随近景',encoding='utf-8')
(r/'legend.txt').write_text('红：车辆及朝向   黄：实际轨迹   白：规划路线   蓝：已观测表面   绿：观测自由空间投影（不代表可通行性判定）',encoding='utf-8')
font='/mnt/c/Windows/Fonts/msyh.ttc'
def text(file,x,y,size):return f"drawtext=fontfile='{font}':textfile='{r/file}':reload=1:x={x}:y={y}:fontsize={size}:fontcolor=white"
filters=','.join([text('left_title.txt',25,12,30),text('right_title.txt',1145,12,30),text('hud.txt',24,1024,25),text('legend.txt',24,1057,20)])
def control(value):
    p=r/'control.tmp';p.write_text(json.dumps(value));p.replace(r/'control.json')
def record(name,start,end,rate):
    control({'mode':'hold','time':start,'rate':rate,'end_time':end});time.sleep(2)
    duration=(end-start)/rate+5
    args=['ffmpeg','-hide_banner','-y','-f','x11grab','-draw_mouse','0','-framerate','20','-video_size','1920x1080','-i',':89','-t',str(duration),'-vf',filters,'-c:v','libx264','-preset','veryfast','-crf','21','-pix_fmt','yuv420p','-threads','4','-movflags','+faststart',str(r/name)]
    with (r/(name+'.log')).open('w') as log:
        p=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT);time.sleep(1.5);control({'mode':'play','time':start,'rate':rate,'end_time':end});rc=p.wait()
    if rc:raise RuntimeError('ffmpeg failed: '+name)
    print('Recorded',name,flush=True)
record('rviz_exploration_full_4x.mp4',0,600,4)
record('rviz_recovery_detail_1x.mp4',200,245,1)
control({'mode':'hold','time':600,'rate':4})
print('RECORDING_COMPLETE',flush=True)
