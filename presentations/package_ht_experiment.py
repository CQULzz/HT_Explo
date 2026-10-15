#!/usr/bin/env python3
"""Prepare a browser-compatible video and complete experiment release assets.

This command writes local artifacts only. Publish them with GitHub CLI after
committing the report; large videos, snapshots and recordings stay out of Git.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
import cv2


def sha256(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def video_info(path):
    v=cv2.VideoCapture(str(path))
    if not v.isOpened():raise RuntimeError(f'Cannot open video: {path}')
    frames=int(v.get(cv2.CAP_PROP_FRAME_COUNT));fps=v.get(cv2.CAP_PROP_FPS)
    info={'frames':frames,'fps':fps,'width':int(v.get(cv2.CAP_PROP_FRAME_WIDTH)),
          'height':int(v.get(cv2.CAP_PROP_FRAME_HEIGHT))}
    for i in [0,frames//2,frames-1]:
        v.set(cv2.CAP_PROP_POS_FRAMES,i);ok,_=v.read()
        if not ok:raise RuntimeError(f'Video frame {i} cannot be decoded')
    v.release();return info


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('folder',type=Path)
    parser.add_argument('--encoder',default=shutil.which('ffmpeg'))
    parser.add_argument('--repo',default='CQULzz/HT_Explo')
    parser.add_argument('--tag',required=True)
    args=parser.parse_args();folder=args.folder.resolve()
    if not args.encoder:raise RuntimeError('Supply --encoder with an FFmpeg executable supporting libx264')
    for name in ['summary.json','delivery_and_pause_audit.json','manifest.json','snapshots/index.json']:
        if not (folder/name).is_file():raise RuntimeError(f'Incomplete experiment: {name}')
    out=folder/'publish';out.mkdir(exist_ok=True)
    source=folder/'visuals/current_ht_exploration.mp4'
    duration=int(round(json.loads((folder/'summary.json').read_text())['duration_s']))
    video=out/f'garage_ht_xytheta_{duration}s.mp4'
    subprocess.run([args.encoder,'-y','-i',str(source),'-an','-c:v','libx264','-preset','fast',
                    '-crf','20','-pix_fmt','yuv420p','-movflags','+faststart','-threads','4',str(video)],check=True)
    original_info=video_info(source);encoded_info=video_info(video)
    if original_info!=encoded_info:raise RuntimeError('Encoding changed video dimensions, frame count or rate')
    archive=out/'garage_ht_experiment_results.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for path in sorted(folder.rglob('*')):
            relative=path.relative_to(folder)
            if relative.parts[0] in {'publish','original','original_bag'} or path.is_symlink() or not path.is_file():continue
            if path.suffix.lower()=='.mp4':continue
            z.write(path,Path(folder.name)/relative)
        metadata=folder/'original_bag/metadata.yaml'
        if metadata.exists():z.write(metadata,Path(folder.name)/'original_bag/metadata.yaml')
    with zipfile.ZipFile(archive) as z:
        bad=z.testzip()
        if bad:raise RuntimeError(f'Archive CRC failed: {bad}')
    assets=[video,archive]+sorted((folder/'original_bag').glob('*.mcap'))
    manifest={'repository':args.repo,'release_tag':args.tag,
              'release_url':f'https://github.com/{args.repo}/releases/tag/{args.tag}',
              'tested_code_commit':json.loads((folder/'manifest.json').read_text())['git_head'],
              'video':encoded_info,'assets':[]}
    for path in assets:
        manifest['assets'].append({'name':path.name,'relative_path':str(path.relative_to(folder)),'bytes':path.stat().st_size,
                                   'sha256':sha256(path),
                                   'download_url':f'https://github.com/{args.repo}/releases/download/{args.tag}/{path.name}'})
    (out/'release_files.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(manifest,indent=2),flush=True)


if __name__=='__main__':main()
