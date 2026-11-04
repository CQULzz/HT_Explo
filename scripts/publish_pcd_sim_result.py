"""Immutable multipart evidence upload; verify archived bytes and GitHub digests."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,tarfile,time,io
ap=argparse.ArgumentParser();ap.add_argument('--config',type=Path,required=True);ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args();cfg=json.loads(a.config.read_text());out=Path(cfg['output']);out.mkdir(exist_ok=True);repo=cfg['repo'];tag=cfg['tag']
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
def gh(*args):
 return subprocess.check_output(['gh',*args],text=True)
class Writer:
 def __init__(self,label):self.label=label;self.i=-1;self.f=None;self.size=0;self.parts=[];self.total=hashlib.sha256()
 def write(self,b):
  total=len(b);self.total.update(b)
  while b:
   if self.f is None or self.size==512*1024*1024:
    self.finish();self.i+=1;self.path=out/f'{self.label}.tar.part{self.i:03d}';assert not self.path.exists(),self.path;self.f=self.path.open('wb');self.h=hashlib.sha256();self.size=0
   n=min(len(b),512*1024*1024-self.size);chunk=b[:n];self.f.write(chunk);self.h.update(chunk);self.size+=n;b=b[n:]
  return total
 def finish(self):
  if self.f:self.f.close();self.parts.append({'name':self.path.name,'bytes':self.size,'sha256':self.h.hexdigest()});self.f=None
 def flush(self):
  if self.f:self.f.flush()
class PartsReader:
 def __init__(self,paths):self.paths=iter(paths);self.f=None
 def read(self,n=-1):
  if n<0:n=8*1024*1024
  chunks=[];remaining=n
  while remaining:
   if self.f is None:
    try:self.f=next(self.paths).open('rb')
    except StopIteration:break
   b=self.f.read(remaining)
   if not b:self.f.close();self.f=None;continue
   chunks.append(b);remaining-=len(b)
  return b''.join(chunks)
statefile=out/'PREPARED.json'
if statefile.exists():state=json.loads(statefile.read_text())
else:
 state={'repo':repo,'tag':tag,'tested_commit':cfg['tested_commit'],'recording_scope':cfg['recording_scope'],'archives':[],'assets':[]}
 for spec in cfg['archives']:
  root=Path(spec['root']).resolve();excluded=spec.get('exclude_components',[]);files=[]
  for p in sorted(root.rglob('*')):
   if any(part in excluded for part in p.relative_to(root).parts) or not p.is_file():continue
   if p.is_symlink() and not p.resolve().is_relative_to(root):raise ValueError('External evidence symlink: '+str(p))
   files.append(p)
  inventory=[]
  for p in files:inventory.append({'path':str(p.relative_to(root)),'bytes':p.stat().st_size,'sha256':digest(p)})
  w=Writer(spec['label'])
  with tarfile.open(fileobj=w,mode='w|',dereference=True) as tar:
   for p in files:tar.add(p,arcname=str(Path(spec['label'])/p.relative_to(root)),recursive=False)
  w.finish();print('Packed',spec['label'],sum(p['bytes'] for p in w.parts),flush=True)
  reader=PartsReader([out/p['name'] for p in w.parts]);count=0
  with tarfile.open(fileobj=reader,mode='r|') as tar:
   for member in tar:
    expected=inventory[count];assert member.name==str(Path(spec['label'])/expected['path']);assert member.size==expected['bytes'];h=hashlib.sha256();f=tar.extractfile(member)
    while b:=f.read(8*1024*1024):h.update(b)
    assert h.hexdigest()==expected['sha256'],member.name;count+=1
  assert count==len(inventory)
  inv=out/(spec['label']+'-files.json');inv.write_text(json.dumps({'source':str(root),'excluded_components':excluded,'exclusion_note':spec.get('exclusion_note',''),'files':inventory},ensure_ascii=False,indent=2))
  entry={'label':spec['label'],'whole_tar_sha256':w.total.hexdigest(),'parts':w.parts,'inventory':inv.name,'verified_archive_entries':count};state['archives'].append(entry);state['assets']+=w.parts+[{'name':inv.name,'bytes':inv.stat().st_size,'sha256':digest(inv)}]
 for spec in cfg['files']:
  src=Path(spec['path']);dst=out/spec['name'];assert not dst.exists();dst.write_bytes(src.read_bytes());state['assets'].append({'name':dst.name,'bytes':dst.stat().st_size,'sha256':digest(dst)})
 statefile.write_text(json.dumps(state,ensure_ascii=False,indent=2))
for asset in state['assets']:
 p=out/asset['name'];assert p.stat().st_size==asset['bytes'] and digest(p)==asset['sha256']
if a.prepare_only:print('Prepared and verified',len(state['assets']),'assets',flush=True);raise SystemExit
obj=json.loads(gh('api',f'repos/{repo}/git/ref/tags/{tag}'))['object']
while obj['type']=='tag':obj=json.loads(gh('api',f'repos/{repo}/git/tags/'+obj['sha']))['object']
assert obj['type']=='commit' and obj['sha']==cfg['tested_commit'],'Remote tag must identify tested code'
try:release=json.loads(gh('api',f'repos/{repo}/releases/tags/{tag}'))
except subprocess.CalledProcessError:
 gh('release','create',tag,'--repo',repo,'--verify-tag','--draft','--prerelease','--title',cfg['title'],'--notes-file',cfg['notes']);release=json.loads(gh('api',f'repos/{repo}/releases/tags/{tag}'))
proof=out/'EVIDENCE_MANIFEST.json'
if not proof.exists():proof.write_text(json.dumps(state,ensure_ascii=False,indent=2))
assets=state['assets']+[{'name':proof.name,'bytes':proof.stat().st_size,'sha256':digest(proof)}];verified=[]
for asset in assets:
 release=json.loads(gh('api',f'repos/{repo}/releases/tags/{tag}'));existing={x['name']:x for x in release['assets']}
 if asset['name'] not in existing:
  for attempt in range(3):
   print('Uploading',asset['name'],asset['bytes'],flush=True)
   r=subprocess.run(['gh','release','upload',tag,str(out/asset['name']),'--repo',repo])
   if not r.returncode:break
   # A timed-out request may have completed server-side. Reuse only a
   # verified completed object; delete only an empty draft transport stub.
   check=json.loads(gh('api',f'repos/{repo}/releases/tags/{tag}'))
   item=next((x for x in check['assets'] if x['name']==asset['name']),None)
   if item:
    detail=json.loads(gh('api',f'repos/{repo}/releases/assets/'+str(item['id'])))
    if item['size']==asset['bytes'] and detail.get('digest')=='sha256:'+asset['sha256']:break
    if check['draft'] and item.get('state')=='starter' and item['size']==0:
     gh('api','--method','DELETE',f'repos/{repo}/releases/assets/'+str(item['id']))
    else:raise RuntimeError('Unverified conflicting asset; refusing overwrite: '+asset['name'])
   time.sleep(min(5*(attempt+1),15))
  else:raise RuntimeError('Upload failed: '+asset['name'])
  release=json.loads(gh('api',f'repos/{repo}/releases/tags/{tag}'));existing={x['name']:x for x in release['assets']}
 remote=existing[asset['name']];detail=json.loads(gh('api',f'repos/{repo}/releases/assets/'+str(remote['id'])))
 assert remote['size']==asset['bytes'] and detail.get('digest')=='sha256:'+asset['sha256'],('Remote size/digest differs; never overwrite',asset['name'],detail.get('digest'))
 verified.append({**asset,'url':remote['browser_download_url'],'id':remote['id']});(out/'UPLOAD_PROGRESS.json').write_text(json.dumps({'verified':verified,'total_assets':len(assets)},indent=2));print('Verified',asset['name'],flush=True)
receipt={'release':f'https://github.com/{repo}/releases/tag/{tag}','tested_commit':cfg['tested_commit'],'all_assets_verified':True,'assets':verified,'recording_scope':cfg['recording_scope']};receiptfile=out/'PUBLICATION_RECEIPT.json';receiptfile.write_text(json.dumps(receipt,ensure_ascii=False,indent=2))
gh('release','upload',tag,str(receiptfile),'--repo',repo)
release=json.loads(gh('api',f'repos/{repo}/releases/tags/{tag}'));item=next(x for x in release['assets'] if x['name']==receiptfile.name);detail=json.loads(gh('api',f'repos/{repo}/releases/assets/'+str(item['id'])));assert item['size']==receiptfile.stat().st_size and detail.get('digest')=='sha256:'+digest(receiptfile)
gh('release','edit',tag,'--repo',repo,'--draft=false','--prerelease','--latest=false')
release=json.loads(gh('api',f'repos/{repo}/releases/tags/{tag}'));assert release['draft'] is False
(out/'PUBLISHED.json').write_text(json.dumps({'release':release['html_url'],'tested_commit':cfg['tested_commit'],'receipt_sha256':digest(receiptfile),'published':True},indent=2));print('Published and verified:',release['html_url'],flush=True)
