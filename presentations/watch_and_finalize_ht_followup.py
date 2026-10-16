#!/usr/bin/env python3
"""Wait for the independent recorder/analysis job, then export its audited results."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import time

from run_scheduled_comparison import source,q


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('folder',type=Path)
    ap.add_argument('--baseline',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    folder=args.folder.resolve()
    deadline=time.monotonic()+10800
    while not (folder/'ANALYSIS_COMPLETED.json').exists():
        if any((folder/name).exists() for name in ('POSTPROCESS_FAILED.json','FAILURE.json','STOP_REASON.json')):
            print('Trial interrupted or failed; evidence preserved, no successful result exported.',flush=True)
            return 1
        if time.monotonic()>deadline:
            raise TimeoutError('No completed analysis after 3 hours')
        time.sleep(5)
    script=Path(__file__).with_name('finalize_ht_followup.py')
    cmd=source('/opt/ros/jazzy/setup.bash')+' exec python3 '+q(script)+' '+q(folder)+\
        ' --baseline '+q(args.baseline.resolve())+' --output '+q(args.output.resolve())
    with (folder/'finalize.log').open('w') as log:
        result=subprocess.run(['bash','-lc',cmd],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
    if result.returncode:
        (folder/'FINALIZE_FAILED.json').write_text(json.dumps(dict(
            returncode=result.returncode,log=str(folder/'finalize.log'),
            finished_at=dt.datetime.now().astimezone().isoformat()),indent=2)+'\n')
    return result.returncode


if __name__=='__main__':
    sys.exit(main())
