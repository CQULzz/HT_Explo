#!/usr/bin/env python3
"""Wait for complete measurement/postprocessing, then publish the recorded evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'presentations'))
from finalize_tare_multiscene import active_evidence_workers


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    job=json.loads(a.state.read_text());archive=Path(job['archive'])
    while True:
        result=subprocess.check_output(['systemctl','--user','show','ht-tare-multiscene.service','-p','MainPID','--value'],text=True).strip()
        if result=='0' and not active_evidence_workers(Path(job['suite'])):break
        time.sleep(5)
    if not (archive/'files_sha256.json').exists():
        # Service is no longer running. Preserve partial captures via the explicit
        # interrupted exporter instead of making failed evidence unpublishable.
        subprocess.run(['bash','-c','source "$1" && shift && exec "$@"','ht-evidence-export',
                        '/opt/ros/jazzy/setup.bash',sys.executable,
                        str(ROOT/'presentations/finalize_tare_multiscene.py'),job['suite'],
                        '--state',str(a.state),'--allow-interrupted'],cwd=ROOT,check=True)
    if not (archive/'files_sha256.json').exists():
        raise RuntimeError('Evidence export failed; retain all source data and inspect logs')
    subprocess.run([sys.executable,str(ROOT/'scripts/finalize_tare_multiscene_publication.py'),'--state',str(a.state)],cwd=ROOT,check=True)


if __name__=='__main__':main()
