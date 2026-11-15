from pathlib import Path
import shutil,json
root=Path('/mnt/d/HT-URDF-Compare-20261115/video')
for variant in ['baseline','urdf']:
    p=root/variant;target=p/'failed_attempt_01';target.mkdir(exist_ok=True)
    for name in ['rviz_exploration_full_4x.mp4','rviz_exploration_full_4x.mp4.log','record.log','start.log']:
        if (p/name).exists():shutil.copy2(p/name,target/name)
    (target/'FAILURE.json').write_text(json.dumps({'reason':'First recording inherited DISPLAY=:0 instead of isolated RViz display; URDF also hit a missing subtitle file during NTFS rename. Both recordings rejected; raw simulation unchanged.','fix':'Explicit encoder display; hot subtitles on Linux filesystem using atomic rename.'},indent=2))
