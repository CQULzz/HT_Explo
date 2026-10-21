#!/usr/bin/env python3
"""Side-by-side real cameras, aligned to each trial's own measurement origin."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from finalize_matched_tare_comparison import read, write, run, sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    job=read(a.state);suite=Path(job['suite']);out=Path(job['archive']);encoder=job['encoder']
    if read(suite/'suite.json')['state']!='COMPLETED':
        raise RuntimeError('Both camera recordings must already pass collection validation')
    movie=suite/'comparison.mp4'
    run([encoder,'-nostdin','-y','-i',suite/'original/camera_h264.mp4','-i',suite/'ht/camera_h264.mp4',
         '-filter_complex_threads','2','-filter_complex','[0:v][1:v]hstack=inputs=2:shortest=1',
         '-t','600','-c:v','libx264','-preset','fast','-crf','25','-pix_fmt','yuv420p','-threads','2',
         '-movflags','+faststart',movie],suite/'comparison_video_encode.log')
    run([encoder,'-nostdin','-v','error','-threads','2','-i',movie,'-progress','pipe:1','-nostats','-f','null','-'],suite/'comparison_video_decode.log',600)
    progress=dict(line.split('=',1) for line in (suite/'comparison_video_decode.log').read_text().splitlines() if '=' in line)
    frames=int(progress['frame']);duration=frames/15
    if abs(duration-600)>1/15+.001:
        raise RuntimeError('Comparison video duration mismatch')
    result=dict(left='Original TARE, matched motion envelope',right='Latest HT with native TARE decisions',
                alignment='Each individual camera trimmed to its own first TARE-cycle measurement origin; no temporal interpolation.',
                width=1920,height=600,fps=15,decoded_frames=frames,duration_s=duration,
                full_decode_returncode=0,bytes=movie.stat().st_size,sha256=sha(movie))
    write(suite/'comparison_video_validation.json',result)
    shutil.copy2(movie,out/movie.name)
    shutil.copy2(suite/'comparison_video_validation.json',out/'comparison_video_validation.json')
    shutil.copy2(Path(__file__),out/Path(__file__).name)
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
