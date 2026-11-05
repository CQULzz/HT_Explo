"""Copy known CMU packages into a new workspace and defer context shutdown.

Never writes the source workspace or reuses an existing destination.
"""
from pathlib import Path
import argparse
import hashlib
import json
import shutil


def stage(source,destination):
    source=Path(source).resolve(strict=True);destination=Path(destination)
    manifest=json.loads(Path(__file__).with_name('cmu_shutdown_manifest.json').read_text())
    candidates={}
    for name,sums in manifest['files'].items():
        raw=(source/'src'/name).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=sums['before_sha256']:
            raise RuntimeError('Unknown CMU source; preserving: '+name)
        text=raw.decode()
        for old,new in manifest['replacements']:
            if text.count(old)!=1:raise RuntimeError('Unexpected CMU patch context')
            text=text.replace(old,new)
        after=(manifest['header']+text).encode()
        if hashlib.sha256(after).hexdigest()!=sums['after_sha256']:
            raise RuntimeError('CMU candidate hash mismatch')
        candidates[name]=after
    destination.mkdir(exist_ok=False)
    for package in ['local_planner','terrain_analysis','terrain_analysis_ext']:
        shutil.copytree(source/'src'/package,destination/'src'/package)
    for name,payload in candidates.items():(destination/'src'/name).write_bytes(payload)
    receipt={'source_workspace':str(source),'destination':str(destination.resolve()),
             'source_unchanged':True,'manifest':manifest}
    (destination/'STAGED.json').write_text(json.dumps(receipt,indent=2))
    return receipt


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source-workspace',type=Path,required=True)
    ap.add_argument('--destination',type=Path,required=True)
    args=ap.parse_args();print(json.dumps(stage(args.source_workspace,args.destination),indent=2))
