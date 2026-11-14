from pathlib import Path
import subprocess,json,hashlib,shutil
r=Path('/mnt/d/HT-Execution-300s/rviz_video_20261114')
files=[]
for name in ['rviz_exploration_full_4x.mp4','rviz_recovery_detail_1x.mp4']:
    p=r/name
    subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,r_frame_rate','-of','json',str(p)],text=True))
    files.append({'file':name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'probe':probe,'full_decode_passed':True})
for name,second,outname in [('rviz_exploration_full_4x.mp4',145,'video_end_preview.png'),('rviz_recovery_detail_1x.mp4',25,'recovery_preview.png')]:
    subprocess.run(['ffmpeg','-v','error','-y','-ss',str(second),'-i',str(r/name),'-frames:v','1',str(r/outname)],check=True)
(r/'VIDEO_MANIFEST.json').write_text(json.dumps({'files':files,'capture':'Actual RViz 2 windows captured with ffmpeg x11grab.','new_navigation_experiment':False,'source':'Completed 600s experiment execution_600s_01','full_video_source_seconds':[0,600],'normal_speed_clip_source_seconds':[200,245]},indent=2))
(r/'README_zh.md').write_text('''# RViz探索过程视频

由2026-11-14已完成的600秒实验录包回放生成，没有新增探索实验。

- rviz_exploration_full_4x.mp4：全程4倍速，155秒（含首尾停留）。
- rviz_recovery_detail_1x.mp4：实验200至245秒原速片段，50秒（含首尾停留），包含第二次恢复。
- 左侧为固定全局视角，右侧为跟随车辆的近景；红色为0.6×0.6m配置包络及朝向箭头，黄色为实际轨迹，白色为录制的TARE局部规划路线。
- 蓝色是实际registered_scan累计表面，0.2m体素显示，显示高度0.15至2.5m以减少地面/天花板遮挡。
- 绿色是实际扫描射线中0至0.5m高自由空间体素的地面投影，采用0.5m栅格、每秒约1024端点、12m截断；不是可通行性或地面真值判断。
- 车辆按原指标CSV位姿采样回放，规划路线来自原录包；HUD的里程/观测体积代理沿用原指标。静态视角范围用录制轨迹选取，未加入未知区域的地面或墙体。

这是真实RViz界面录屏，显示数据由原录包只读提取后发布到独立ROS域217。视频不含声音。两个视频已完整解码检查，格式、大小和SHA256见VIDEO_MANIFEST.json。未上传视频到GitHub。
''',encoding='utf-8')
for name in ['prepare_rviz_video.py','configure_rviz_video.py','rviz_video_player.py','start_rviz_video.sh','record_rviz_video.py','finalize_rviz_video.py']:
    shutil.copy2(Path('/mnt/d/HT-Execution-300s/setup')/name,r/name)
(r/'STOP').touch()
print(json.dumps(files,indent=2))
