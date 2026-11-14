from pathlib import Path
import json,subprocess,hashlib,shutil
base=Path('/mnt/d/HT-Execution-300s/campus_pcd_videos_20261114');repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/validation/campus_pcd_20261114')
receipts=[]
for name,case in [('campus','campus_600s_02'),('user_pcd','user_pcd_600s_02')]:
    r=base/name;p=r/'rviz_exploration_full_4x.mp4'
    subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,r_frame_rate','-of','json',str(p)],text=True))
    assert abs(float(probe['format']['duration'])-155)<.1
    for second,filename in [(75,'video_preview.png'),(148,'video_end_preview.png')]:
        subprocess.run(['ffmpeg','-v','error','-y','-ss',str(second),'-i',str(p),'-frames:v','1',str(r/filename)],check=True)
    receipt={'case':case,'file':str(p),'windows_file':'D:/HT-Execution-300s/campus_pcd_videos_20261114/'+name+'/rviz_exploration_full_4x.mp4','sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'probe':probe,'full_decode_passed':True,'capture':'Actual RViz 2 windows, x11grab, recorded data replay in domain 221','source_seconds':[0,600],'playback_rate':4}
    (r/'VIDEO_MANIFEST.json').write_text(json.dumps(receipt,indent=2));receipts.append(receipt)
    dst=repo/'videos'/name;dst.mkdir(parents=True,exist_ok=True)
    for n in ['VIDEO_MANIFEST.json','PROVENANCE.json','overview.rviz','detail.rviz']:
        shutil.copy2(r/n,dst/n)
for p in (base/'tools').glob('*'):
    if p.suffix in ['.py','.sh']:
        d=repo/'source/video_tools';d.mkdir(exist_ok=True);shutil.copy2(p,d/p.name)
(base/'VIDEO_MANIFEST.json').write_text(json.dumps(receipts,indent=2))
(base/'README_zh.md').write_text('''# Campus / 历史PCD实验RViz视频

两个子目录campus、user_pcd各包含完整600秒实验的4倍速RViz回放，视频155秒（含首尾停留），1920×1080/20fps/H.264，无声音，已完整解码验证。

左侧整体探索与轨迹，右侧车辆跟随近景；保留原实验时间、里程、观测体积代理和当前HT门禁状态。红色是当前0.6×0.6m车辆包络及朝向，黄色实际轨迹，白色原TARE局部规划路线。车辆位姿按原CSV采样回放。

蓝色为真实扫描的已观测表面，显示12m内、相对扫描时地面参考+0.15至+2.5m的0.2m显示体素。绿色为近地射线自由空间的XY投影，仅在存在低表面测量的栅格显示，显示高度取实测低表面；没有补未测地面。颜色只作观测可视化，不能当作可通行或地形真值。绝对高度随实测地形变化，未把campus或PCD平铺到indoor高度。

campus来自campus_600s_02，持续探索；user_pcd来自user_pcd_600s_02，在约66秒后停止，HT_DIRECTION_LOW状态如实显示。PCD的显示范围来自现有30×30m重建区，不代表整张远距离点云。此回放不启动新导航实验。

视频本体只保存在本机D盘；仓库保存代码、说明和校验回执。SHA256和格式见VIDEO_MANIFEST.json。
''',encoding='utf-8')
(base/'user_pcd/STOP').touch()
print(json.dumps(receipts,indent=2))
