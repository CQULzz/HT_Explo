from pathlib import Path
import hashlib,json,shutil,subprocess
root=Path('/mnt/d/HT-URDF-Compare-20261115');runtime=Path('/home/lzz/ht_urdf_compare_20261115');workspace=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');dest=workspace/'validation/urdf_envelope_20261115';records=[]
for variant in ['baseline','urdf']:
    p=root/'video'/variant;video=p/'rviz_exploration_full_4x.mp4'
    info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration,size:stream=codec_name,width,height,r_frame_rate','-of','json',str(video)]))
    assert float(info['format']['duration'])==155 and info['streams'][0]['width']==1920 and info['streams'][0]['height']==1080
    assert (p/'full_decode.log').stat().st_size==0
    info.update(variant=variant,local_path=str(video),sha256=hashlib.sha256(video.read_bytes()).hexdigest(),full_decode_passed=True,preview_visually_checked=True,uploaded=False)
    records.append(info);target=dest/'video'/variant;target.mkdir(parents=True,exist_ok=True)
    for name in ['preview.png','PROVENANCE.json','BODY.json','full_decode.log']:
        shutil.copy2(p/name,target/name)
    shutil.copy2(p/'failed_attempt_01/FAILURE.json',target/'FIRST_RECORDING_FAILURE.json')
(root/'analysis/VIDEO_VALIDATION.json').write_text(json.dumps(records,indent=2))
shutil.copy2(root/'analysis/VIDEO_VALIDATION.json',dest/'VIDEO_VALIDATION.json')
for p in (root/'setup').glob('*.py'):shutil.copy2(p,dest/'source'/p.name)
shutil.copytree(root/'video_tools',dest/'source/video_tools',dirs_exist_ok=True)
shutil.copy2(dest/'REPORT_zh.md',root/'REPORT_zh.md');shutil.copy2(dest/'REPORT_zh.md',runtime/'REPORT_zh.md')
status={'navigation_runs_complete':2,'planned_navigation_runs':2,'budget_closed':True,'code_mode':'opt-in URDF envelope; legacy configs retained','hardware_started':False,'video_recording_attempts':2,'videos_complete_and_checked':2,'raw_data_uploaded':False,'new_video_uploaded':False,'raw_data_retained':str(runtime/'runs')}
(root/'FINAL_STATUS.json').write_text(json.dumps(status,indent=2));shutil.copy2(root/'FINAL_STATUS.json',dest/'FINAL_STATUS.json')
print(json.dumps(records,indent=2))
