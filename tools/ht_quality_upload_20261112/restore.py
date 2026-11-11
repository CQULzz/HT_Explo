"""Restore downloaded release files into a fresh directory, verifying all bytes."""
from pathlib import Path,PurePosixPath
import argparse,hashlib,json,os,shutil,tarfile

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def safe(root,name):
    p=PurePosixPath(name)
    if p.is_absolute() or '..' in p.parts:raise RuntimeError('Unsafe archive path')
    return root/Path(*p.parts)

def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--assets-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();manifest=json.loads(a.manifest.read_text())
    if a.output.exists():raise RuntimeError('Use a fresh output directory; existing files are never overwritten')
    for x in manifest['assets']:
        path=a.assets_dir/x['name']
        if path.stat().st_size!=x['bytes'] or sha(path)!=x['sha256']:raise RuntimeError('Downloaded asset mismatch: '+x['name'])
    a.output.mkdir(parents=True)
    archive=next(x for x in manifest['assets'] if x['kind']=='evidence_archive')
    with tarfile.open(a.assets_dir/archive['name'],'r:gz') as tar:
        for member in tar:
            if not member.isfile():raise RuntimeError('Unexpected archive entry type')
            target=safe(a.output,member.name);target.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(member) as src,target.open('xb') as dest:shutil.copyfileobj(src,dest)
    for x in manifest['assets']:
        if x['kind']!='original_mcap':continue
        target=safe(a.output,x['restore_path']);target.parent.mkdir(parents=True,exist_ok=True)
        try:os.link(a.assets_dir/x['name'],target)
        except OSError:shutil.copy2(a.assets_dir/x['name'],target)
    inventory=json.loads((a.output/'FILES_SHA256.json').read_text())
    for x in inventory:
        target=safe(a.output,x['path'])
        if not target.is_file() or target.stat().st_size!=x['bytes'] or sha(target)!=x['sha256']:
            raise RuntimeError('Restored original file mismatch: '+x['path'])
    print(json.dumps({'restored':True,'verified_original_files':len(inventory),'output':str(a.output)},indent=2))

if __name__=='__main__':main()
