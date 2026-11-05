"""Upload a prepared immutable recording with remote size/SHA256 verification."""
import pathlib,json,subprocess,hashlib,time,concurrent.futures,threading,sys,argparse,shutil
ap=argparse.ArgumentParser();ap.add_argument('--config',type=pathlib.Path,required=True);ap.add_argument('--gh',default=shutil.which('gh'));args=ap.parse_args()
if not args.gh:ap.error('Install/authenticate native gh or pass --gh explicitly')
cfg=json.loads(args.config.read_text(encoding='utf-8'));OUT=pathlib.Path(cfg['output']);GH=args.gh;REPO=cfg['repo'];TAG=cfg['tag']
try:RID=json.loads(subprocess.check_output([GH,'release','view',TAG,'--repo',REPO,'--json','databaseId'],text=True))['databaseId']
except subprocess.CalledProcessError:
 subprocess.run([GH,'release','create',TAG,'--repo',REPO,'--verify-tag','--draft','--prerelease','--title',cfg['title'],'--notes-file',cfg['notes']],check=True)
 RID=json.loads(subprocess.check_output([GH,'release','view',TAG,'--repo',REPO,'--json','databaseId'],text=True))['databaseId']

def gh(*args):return subprocess.check_output([GH,*args],text=True,encoding='utf-8',stderr=subprocess.PIPE,timeout=60)
def api(endpoint,*args):return json.loads(gh('api',endpoint,*args))
def release():return api(f'repos/{REPO}/releases/{RID}')
def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while b:=f.read(8*1024*1024):h.update(b)
 return h.hexdigest()
state=json.loads((OUT/'PREPARED.json').read_text(encoding='utf-8'));proof=OUT/'EVIDENCE_MANIFEST.json'
if not proof.exists():proof.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
assets=state['assets']+[{'name':proof.name,'bytes':proof.stat().st_size,'sha256':sha(proof)}]
assert api(f'repos/{REPO}/git/ref/tags/{TAG}')['object']['sha']==state['tested_commit']
initial=release();assert initial['tag_name']==TAG
for a in assets:assert (OUT/a['name']).stat().st_size==a['bytes']

def find(name):return next((x for x in release()['assets'] if x['name']==name),None)
def checked(a,x):return x and x['size']==a['bytes'] and x.get('digest')=='sha256:'+a['sha256']
def upload(a):
 name=a['name'];x=find(name)
 for attempt in range(4):
  if checked(a,x):return {**a,'url':f'https://github.com/{REPO}/releases/download/{TAG}/'+a['name'],'id':x['id']}
  if x:
   if x.get('state')=='starter' and x['size']==0 and release()['draft']:
    gh('api','--method','DELETE',f'repos/{REPO}/releases/assets/{x["id"]}')
   else:raise RuntimeError('Conflicting asset: '+name)
  print('Uploading '+name+' '+str(a['bytes']),flush=True)
  try:
   proc=subprocess.run([GH,'release','upload',TAG,str(OUT/name),'--repo',REPO],text=True,encoding='utf-8',capture_output=True,timeout=900)
   error=proc.stderr[-500:]
  except subprocess.TimeoutExpired:error='Upload request timed out'
  x=find(name)
  if checked(a,x):return {**a,'url':f'https://github.com/{REPO}/releases/download/{TAG}/'+a['name'],'id':x['id']}
  print('Retry '+name+' '+error,flush=True);time.sleep(5)
 raise RuntimeError('Upload could not be verified: '+name)
verified=[];started=time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 futures={pool.submit(upload,a):a for a in assets}
 for f in concurrent.futures.as_completed(futures):
  a=f.result();verified.append(a)
  (OUT/'UPLOAD_PROGRESS.json').write_text(json.dumps({'verified':verified,'total_assets':len(assets),'elapsed_s':time.monotonic()-started},indent=2),encoding='utf-8')
  print(f'Verified {len(verified)}/{len(assets)} '+a['name'],flush=True)
verified.sort(key=lambda x:next(i for i,a in enumerate(assets) if a['name']==x['name']))
# Recheck the complete draft in a fresh server response before declaring success.
remote={x['name']:x for x in release()['assets']}
assert all(checked(a,remote.get(a['name'])) for a in assets)
receipt={'release':f'https://github.com/{REPO}/releases/tag/{TAG}','tested_commit':state['tested_commit'],'all_assets_verified':True,'assets':verified,'recording_scope':state['recording_scope']}
rp=OUT/'PUBLICATION_RECEIPT.json';rp.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8');upload({'name':rp.name,'bytes':rp.stat().st_size,'sha256':sha(rp)})
gh('release','edit',TAG,'--repo',REPO,'--draft=false','--prerelease','--latest=false')
r=release();assert r['draft'] is False
(OUT/'PUBLISHED.json').write_text(json.dumps({'release':r['html_url'],'tested_commit':state['tested_commit'],'receipt_sha256':sha(rp),'published':True},indent=2),encoding='utf-8')
print('Published and verified: '+r['html_url'],flush=True)
