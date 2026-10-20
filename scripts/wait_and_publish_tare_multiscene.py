#!/usr/bin/env python3
"""Wait for complete measurement/postprocessing, then publish the recorded evidence."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    while True:
        result=subprocess.check_output(['systemctl','--user','show','ht-tare-multiscene.service','-p','MainPID','--value'],text=True).strip()
        if result=='0':break
        time.sleep(5)
    job=json.loads(a.state.read_text());archive=Path(job['archive'])
    if not (archive/'files_sha256.json').exists():
        raise RuntimeError('Measurement/postprocessing did not produce a complete selected archive; preserve partial recordings and inspect logs')
    subprocess.run([sys.executable,str(ROOT/'scripts/finalize_tare_multiscene_publication.py'),'--state',str(a.state)],cwd=ROOT,check=True)


if __name__=='__main__':main()
