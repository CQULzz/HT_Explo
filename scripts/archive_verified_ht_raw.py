#!/usr/bin/env python3
"""Losslessly compact verified, published trials; retain every file and a restore index."""
import argparse,hashlib,json,os,shutil,subprocess,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'presentations/scheduled_results'
DEST=ROOT/'presentations/local_raw_archives'
INDEX=ROOT/'docs/experiments/local_raw_archives.json'

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as stream:
  for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def inventory(raw):
 files={};links={}
 for p in sorted(raw.rglob('*')):
  name=str(p.relative_to(raw))
  if p.is_symlink():
   target=os.readlink(p)
   if not p.resolve().is_relative_to(raw):raise ValueError('External symlink: '+str(p))
   links[name]=target
  elif p.is_file():files[name]=dict(bytes=p.stat().st_size,sha256=digest(p))
 return dict(files=files,symlinks=links)

def verify_archive(archive,raw,expected):
 actual={};links={}
 with tarfile.open(archive,'r:gz') as tf:
  for member in tf:
   rel=Path(member.name)
   if rel.is_absolute() or '..' in rel.parts or rel.parts[0]!=raw.name:raise ValueError('Unsafe member')
   name=str(Path(*rel.parts[1:]))
   if member.issym():links[name]=member.linkname
   elif member.isfile() or member.islnk():
    stream=tf.extractfile(member);h=hashlib.sha256();size=0
    for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk);size+=len(chunk)
    actual[name]=dict(bytes=size,sha256=h.hexdigest())
   elif not member.isdir():raise ValueError('Unsupported archive member')
 if dict(files=actual,symlinks=links)!=expected:raise ValueError('Archive differs from complete source inventory')

def write_index(data):
 INDEX.parent.mkdir(parents=True,exist_ok=True);tmp=INDEX.with_suffix('.json.tmp')
 tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,INDEX)

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('mode',choices=['archive','restore']);ap.add_argument('receipt',type=Path);args=ap.parse_args()
 receipt=json.loads(args.receipt.read_text());raw=Path(receipt['raw_suite']).absolute()
 if raw.parent!=BASE or not raw.name.startswith('ht_'):raise ValueError('Source outside owned trial root')
 tag=receipt['tag'];data=json.loads(INDEX.read_text()) if INDEX.exists() else {};entry=data.get(tag)
 if args.mode=='restore':
  if not entry or raw.exists():raise ValueError('Missing index or source already exists')
  archive=Path(entry['archive'])
  if not archive.is_file():raise ValueError('Local raw was removed under the retention policy; download the verified complete release: '+entry['release'])
  if digest(archive)!=entry['archive_sha256']:raise ValueError('Compressed archive SHA mismatch')
  verify_archive(archive,raw,entry['inventory'])
  # Only our checked archive is trusted; absolute links must reproduce internal
  # aliases at this same canonical source path, never at a relocated target.
  for target in entry['inventory']['symlinks'].values():
   resolved=(raw/target).resolve()
   if not resolved.is_relative_to(raw):raise ValueError('Unsafe restored link')
  with tarfile.open(archive,'r:gz') as tf:tf.extractall(raw.parent,filter='fully_trusted')
  if inventory(raw)!=entry['inventory']:raise ValueError('Restored files differ')
  entry['status']='restored_and_verified';write_index(data);print('Restored and verified:',raw);return
 if not raw.is_dir():raise ValueError('Source directory missing')
 manifest=json.loads(next(raw.glob('*/manifest.json')).read_text())
 if manifest['git_head']!=receipt['tested_commit']:raise ValueError('Measured commit mismatch')
 remote=json.loads(subprocess.check_output(['gh','api','repos/CQULzz/HT_Explo/releases/tags/'+tag],text=True))
 for asset in receipt['assets']:
  item=next((x for x in remote['assets'] if x['name']==asset['name']),None)
  if not item or item['state']!='uploaded' or item['size']!=asset['bytes'] or item.get('digest')!='sha256:'+asset['sha256']:
   raise ValueError('Published asset is not fully verified: '+asset['name'])
 if not any('-raw.tar' in asset['name'] for asset in receipt['assets']):raise ValueError('No complete raw archive receipt')
 expected=inventory(raw);DEST.mkdir(parents=True,exist_ok=True);archive=DEST/(raw.name+'.tar.gz')
 if archive.exists():
  if not entry or str(archive)!=entry['archive'] or digest(archive)!=entry['archive_sha256']:raise ValueError('Unindexed existing archive')
  if entry['inventory']!=expected:raise ValueError('Restored source changed since archive')
 else:
  if shutil.disk_usage(DEST).free<sum(v['bytes'] for v in expected['files'].values())+1024**3:raise ValueError('Insufficient staging space')
  partial=archive.with_suffix('.gz.partial')
  with tarfile.open(partial,'w:gz',compresslevel=1,dereference=False) as tf:tf.add(raw,arcname=raw.name)
  os.replace(partial,archive)
 verify_archive(archive,raw,expected)
 if inventory(raw)!=expected:raise ValueError('Source changed while archiving')
 data[tag]=dict(raw_suite=str(raw),archive=str(archive),archive_sha256=digest(archive),compressed_bytes=archive.stat().st_size,
   original_file_bytes=sum(v['bytes'] for v in expected['files'].values()),release=receipt['release'],inventory=expected,status='archive_verified_source_still_present')
 write_index(data)
 # All original bytes remain in a verified local lossless archive and in the
 # independently verified complete GitHub raw attachment. Reports/videos stay.
 shutil.rmtree(raw)
 data[tag]['status']='source_replaced_by_verified_lossless_archive';write_index(data)
 print(json.dumps({k:v for k,v in data[tag].items() if k!='inventory'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
