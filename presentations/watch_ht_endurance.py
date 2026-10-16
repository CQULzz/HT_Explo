#!/usr/bin/env python3
"""Persist mapper counter checkpoints and finish analysis after a detached run."""
import argparse
import csv
import datetime as dt
import json
from pathlib import Path
import shutil
import subprocess
import time

import psutil

from run_scheduled_comparison import q, source


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', type=Path)
    ap.add_argument('--runner-pid', type=int, required=True)
    ap.add_argument('--encoder', type=Path, help='Optional standalone FFmpeg executable')
    args = ap.parse_args()
    folder = args.folder.resolve()
    start = time.monotonic()
    with (folder/'mapper_checkpoints.jsonl').open('a') as output:
        while time.monotonic()-start < 8000:
            try:
                proc = psutil.Process(args.runner_pid)
                alive = proc.is_running() and proc.status()!=psutil.STATUS_ZOMBIE
            except psutil.Error:
                alive = False
            checkpoint = {'wall_time': time.time()}
            path = folder/'current/cupy_processing_stats.json'
            try:
                checkpoint['mapper'] = json.loads(path.read_text())
            except (OSError, ValueError):
                pass
            if 'mapper' in checkpoint:
                output.write(json.dumps(checkpoint)+'\n')
                output.flush()
            status = {'updated_at': dt.datetime.now().astimezone().isoformat(),
                      'runner_alive': alive, 'output': str(folder)}
            try:
                origin = json.loads((folder/'current/measurement_started.json').read_text())['wall_time']
                status['elapsed_measurement_s'] = time.time()-origin
                with (folder/'current/timeseries.csv').open() as file:
                    rows = list(csv.DictReader(file))
                if rows:
                    status['last_flushed_motion_sample'] = rows[-1]
                with (folder/'health.csv').open() as file:
                    rows = list(csv.DictReader(file))
                if rows:
                    status['last_health_sample'] = rows[-1]
            except (OSError, ValueError, KeyError):
                pass
            temp = folder/'live_status.tmp'
            temp.write_text(json.dumps(status, ensure_ascii=False, indent=2))
            temp.replace(folder/'live_status.json')
            if not alive:
                break
            time.sleep(5)
    if not (folder/'COMPLETED.json').exists():
        (folder/'POSTPROCESS_FAILED.json').write_text(json.dumps({
            'reason': 'Trial ended without planned completion; preserve partial evidence and inspect FAILURE.json.'}, indent=2))
        return
    script = Path(__file__).with_name('summarize_ht_endurance.py')
    command = source('/opt/ros/jazzy/setup.bash')+' exec python3 '+q(script)+' '+q(folder)
    with (folder/'analysis.log').open('w') as log:
        result = subprocess.run(['bash','-lc',command], stdout=log, stderr=subprocess.STDOUT,
                                timeout=1800)
    if result.returncode:
        (folder/'POSTPROCESS_FAILED.json').write_text(json.dumps({'returncode': result.returncode}, indent=2))
        return
    # Convert the evidence video to broadly playable H.264 after recording is closed.
    encoder = str(args.encoder) if args.encoder else shutil.which('ffmpeg')
    if not encoder:
        try:
            import imageio_ffmpeg
            encoder = imageio_ffmpeg.get_ffmpeg_exe()
        except ImportError:
            # Analysis is complete and the original MPEG4 evidence is intact.
            (folder/'ANALYSIS_COMPLETED.json').write_text(json.dumps({
                'finished_at': dt.datetime.now().astimezone().isoformat(),
                'video_encode_returncode': None,
                'video_note': 'FFmpeg unavailable; camera_2fps.mp4 retained. Install imageio-ffmpeg or supply --encoder.'}, indent=2))
            return
    with (folder/'video_encode.log').open('w') as log:
        result = subprocess.run([encoder,'-nostdin','-y','-i',str(folder/'camera_2fps.mp4'),
                                 '-c:v','libx264','-preset','fast','-crf','24','-pix_fmt','yuv420p',
                                 '-threads','2',
                                 '-movflags','+faststart',str(folder/'camera_h264.mp4')],
                                stdout=log, stderr=subprocess.STDOUT, timeout=900)
    (folder/'ANALYSIS_COMPLETED.json').write_text(json.dumps({
        'finished_at': dt.datetime.now().astimezone().isoformat(),
        'video_encode_returncode': result.returncode}, indent=2))


if __name__ == '__main__':
    main()
