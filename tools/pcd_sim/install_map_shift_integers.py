#!/usr/bin/env python3
"""Apply only the hash-verified map shift integer patch in a separate CuPy workspace."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,subprocess

def install(workspace,bundle):
    m=json.loads((bundle/'map_shift_integers_manifest.json').read_text())
    relative=PurePosixPath(m['file'])
    if relative.is_absolute() or '..' in relative.parts:raise RuntimeError('Invalid managed path')
    repo=workspace.resolve()/'src/elevation_mapping_cupy_2204';target=repo/relative
    if target.is_symlink() or any(p.is_symlink() for p in target.parents if p!=repo and repo in p.parents):raise RuntimeError('Managed symlink refused')
    subprocess.run(['git','cat-file','-e',m['upstream_base']+'^{commit}'],cwd=repo,check=True)
    before=hashlib.sha256(target.read_bytes()).hexdigest()
    if before==m['after_sha256']:return {'stage':'map_shift_integers','changed':False,'sha256':before}
    if before!=m['before_sha256']:raise RuntimeError('Unexpected source hash; preserving local differences')
    patch=(bundle/'map_shift_integers.patch').resolve()
    rows=subprocess.check_output(['git','apply','--numstat','-z',str(patch)],cwd=repo).split(b'\0')
    if {row.split(b'\t',2)[2].decode() for row in rows if row}!={str(relative)}:raise RuntimeError('Unexpected patch paths')
    # Preflight patch context before mutation; verify the resulting bytes afterward.
    subprocess.run(['git','apply','--check',str(patch)],cwd=repo,check=True)
    original=target.read_bytes()
    try:
        subprocess.run(['git','apply',str(patch)],cwd=repo,check=True)
        after=hashlib.sha256(target.read_bytes()).hexdigest()
        if after!=m['after_sha256']:raise RuntimeError('Patched hash mismatch')
    except BaseException:
        target.write_bytes(original);raise
    return {'stage':'map_shift_integers','changed':True,'sha256':after}

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workspace',type=Path,required=True);ap.add_argument('--bundle',type=Path,default=Path(__file__).resolve().parents[1]/'elevation_mapping_fixes');args=ap.parse_args();print(json.dumps(install(args.workspace,args.bundle),indent=2))
