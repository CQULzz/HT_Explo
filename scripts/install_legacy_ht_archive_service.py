#!/usr/bin/env python3
"""Install login-resumable historical publication without copying credentials."""
import argparse
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--start',action='store_true')
    ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args()
    runtime=ROOT/'.git/legacy-archive-runtime'
    unit=Path.home()/'.config/systemd/user/ht-legacy-archive.service'
    text=f'''[Unit]
Description=Resume HT historical experiment publication and verify GitHub data
StartLimitIntervalSec=3600
StartLimitBurst=3

[Service]
Type=oneshot
WorkingDirectory={ROOT}
ExecStart=/usr/bin/bash "{ROOT}/scripts/run_legacy_ht_archive.sh"
TimeoutStartSec=infinity
Restart=on-failure
RestartSec=60
StandardOutput=append:{runtime}/service.log
StandardError=inherit

[Install]
WantedBy=default.target
'''
    if args.dry_run:
        print(text)
        return
    runtime.mkdir(parents=True,exist_ok=True)
    unit.parent.mkdir(parents=True,exist_ok=True)
    unit.write_text(text)
    subprocess.run(['systemd-analyze','--user','verify',str(unit)],check=True)
    subprocess.run(['systemctl','--user','daemon-reload'],check=True)
    subprocess.run(['systemctl','--user','enable',unit.name],check=True)
    if args.start:
        subprocess.run(['systemctl','--user','reset-failed',unit.name],check=True)
        subprocess.run(['systemctl','--user','start','--no-block',unit.name],check=True)
    print('Installed',unit,'; runtime log',runtime/'service.log')


if __name__=='__main__':main()
