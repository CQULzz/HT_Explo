#!/usr/bin/env python3
"""Recompute sampled endurance evidence without changing the original archive."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

import summarize_tare_ht_pair as common


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trial',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();trial=args.trial.resolve();out=args.output.resolve()
    out.mkdir(parents=True,exist_ok=False);common.cv2.setNumThreads(1)
    duration=json.loads((trial/'summary.json').read_text())['duration_s']
    original=json.loads((trial/'endurance_audit.json').read_text())['external_metrics']
    original_reader=common.reader
    def sampled_reader(path,topics):
        return original_reader(path,['/endurance/registered_scan' if t=='/registered_scan' else t for t in topics])
    with tempfile.TemporaryDirectory(prefix='ht_metric_reanalysis_') as temporary:
        shadow=Path(temporary);(shadow/'current').mkdir()
        for name in ('timeseries.csv','measurement_started.json'):
            shutil.copy2(trial/'current'/name,shadow/'current'/name)
        (shadow/'current_bag').symlink_to(trial/'evidence_bag',target_is_directory=True)
        common.reader=sampled_reader
        try:_,_,result=common.evaluate(shadow,'current',duration,scan_selection='source_second')
        finally:common.reader=original_reader
        for name in ('external_metrics.json','observation_volume.csv'):
            shutil.copy2(shadow/'current'/name,out/name)
    inputs=[trial/'evidence_bag/metadata.yaml',trial/'current/measurement_started.json',trial/'current/timeseries.csv']
    record=dict(source=str(trial),original=original,recomputed=result,
        evaluator_sha256=hashlib.sha256(Path(common.__file__).read_bytes()).hexdigest(),
        input_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},
        selection='Keep first recorded scan in each absolute source second inside the measurement window; do not downsample again in origin-relative seconds.',
        scope='Offline evaluation only. Original simulation outputs and reports are unchanged.')
    (out/'comparison.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(source=str(trial),old_frames=original['processed_volume_scans'],
        new_frames=result['processed_volume_scans'],old_volume=original['observed_free_volume_m3'],
        new_volume=result['observed_free_volume_m3']),indent=2))


if __name__=='__main__':main()
