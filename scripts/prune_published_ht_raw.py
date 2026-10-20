#!/usr/bin/env python3
"""Keep recent full trials locally; remove older bytes only after GitHub verification."""
import argparse,concurrent.futures,datetime,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
import psutil
from archive_verified_ht_raw import BASE,ROOT,INDEX,inventory,digest
JOURNAL=ROOT/'docs/experiments/local_raw_retention.json'

def write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp')
 tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n');os.replace(tmp,path)

def verify_remote(receipt):
 remote=json.loads(subprocess.check_output(['gh','api','repos/CQULzz/HT_Explo/releases/tags/'+receipt['tag']],text=True))
 for asset in receipt['assets']:
  match=next((r for r in remote['assets'] if r['name']==asset['name']),None)
  if not match or match['state']!='uploaded' or match['size']!=asset['bytes'] or match.get('digest')!='sha256:'+asset['sha256']:
   raise ValueError('Remote asset size/digest mismatch: '+asset['name'])
 indexes=[r for r in receipt['assets'] if r['name'].endswith('-raw-files.json')]
 if len(indexes)!=1 or not any('-raw.tar' in r['name'] for r in receipt['assets']):raise ValueError('Missing complete raw asset/inventory')
 with tempfile.TemporaryDirectory(prefix='ht-retention-') as temporary:
  target=Path(temporary)/'files.json'
  subprocess.run(['gh','release','download',receipt['tag'],'--repo','CQULzz/HT_Explo','--pattern',indexes[0]['name'],'--output',str(target)],check=True,stdout=subprocess.DEVNULL)
  if digest(target)!=indexes[0]['sha256']:raise ValueError('Downloaded inventory digest mismatch')
  files=json.loads(target.read_text())
 return {r['path']:dict(bytes=r['bytes'],sha256=r['sha256']) for r in files}

def live_users(raw):
 result=[]
 for p in psutil.process_iter(['pid','cmdline']):
  try:
   if p.pid!=os.getpid() and any(str(raw) in arg for arg in p.info['cmdline'] or []):result.append(p.pid)
  except (psutil.NoSuchProcess,psutil.AccessDenied):pass
 return result

def complete_collection(receipt):
 """Only demonstrated complete suites may displace recent complete raw data."""
 status=receipt.get('publication_status')
 if status is not None:
  validation=receipt.get('collection_validation',{})
  return status=='COMPLETE_VALIDATED_COLLECTION' and bool(receipt.get('verified_at')) and bool(validation) and all(
   r.get('complete600s') and r.get('recorded_state')=='RECORDED' and bool(r.get('checks')) and all(r['checks'].values())
   for r in validation.values())
 # Legacy stage receipts have no collection status. Require their retained
 # measured evidence, not merely a tag/stage number or a planned-duration label.
 try:
  archive=Path(receipt['result_archive']);state=json.loads((archive/'suite.json').read_text())
  if state.get('git_head')!=receipt['tested_commit'] or state.get('state')!='COMPLETED' or state.get('duration_s')!=600 or not state.get('runs') or not (archive/'FINISHED.json').is_file():return False
  for row in state['runs']:
   trial=archive/row['scenario'];checks=row.get('checks',{})
   if row.get('state')!='RECORDED' or not checks or not all(checks.values()) or not (trial/'COMPLETED.json').is_file():return False
   if json.loads((trial/'summary.json').read_text()).get('duration_s')!=600:return False
  return True
 except (OSError,ValueError,KeyError,TypeError):return False


def retention_protection(receipts,keep):
 complete={r[2]['tag'] for r in receipts if complete_collection(r[2])}
 recent=[r[2]['tag'] for r in receipts if r[2]['tag'] in complete][:keep]
 incomplete={r[2]['tag'] for r in receipts if r[2]['tag'] not in complete}
 return set(recent)|incomplete,incomplete


def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--keep',type=int,default=2);ap.add_argument('--apply',action='store_true');args=ap.parse_args()
 if args.keep<2:raise ValueError('Keep at least the latest two published trials')
 receipts=[]
 for p in (ROOT/'docs/experiments/publications').glob('stage*.json'):
  number=int(p.stem[5:]);receipts.append((number,p,json.loads(p.read_text())))
 receipts.sort(reverse=True);protected,incomplete=retention_protection(receipts,args.keep)
 compact=json.loads(INDEX.read_text()) if INDEX.exists() else {};journal=json.loads(JOURNAL.read_text()) if JOURNAL.exists() else dict(policy='GitHub keeps all complete published raw data; local keeps latest two, reports/videos and regression fixtures.',entries={})
 entries=journal['entries'];plan=[];jobs=[]
 for number,p,r in receipts:
  raw=Path(r['raw_suite']).absolute();entry=compact.get(r['tag'],{});packed=Path(entry['archive']) if entry.get('archive') else None
  if raw.parent!=BASE or not raw.name.startswith('ht_') or raw.is_symlink():raise ValueError('Unsafe owned source path')
  if r['tag'] in protected:plan.append(dict(stage=number,tag=r['tag'],status='kept_incomplete_or_unverified' if r['tag'] in incomplete else 'kept_recent',raw=str(raw)));continue
  if not raw.exists() and not (packed and packed.exists()):plan.append(dict(stage=number,tag=r['tag'],status='not_local'));continue
  if live_users(raw):plan.append(dict(stage=number,tag=r['tag'],status='kept_in_use'));continue
  jobs.append((number,p,r,raw,entry,packed))
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
  futures={pool.submit(verify_remote,item[2]):item for item in jobs}
  for future in concurrent.futures.as_completed(futures):
   number,p,r,raw,entry,packed=futures[future]
   try:
    remote=future.result()
    if raw.is_dir():
     manifest=json.loads(next(raw.glob('*/manifest.json')).read_text())
     if manifest['git_head']!=r['tested_commit']:raise ValueError('Measured commit mismatch')
     local=inventory(raw)
    else:
     if not packed or digest(packed)!=entry['archive_sha256']:raise ValueError('Local compressed archive digest mismatch')
     local=entry['inventory']
    if local['files']!=remote:
     extra=set(local['files'])-set(remote);missing=set(remote)-set(local['files']);changed=[n for n in set(remote)&set(local['files']) if remote[n]!=local['files'][n]]
     raise ValueError('Unpublished local differences: '+json.dumps(dict(extra=sorted(extra),missing=sorted(missing),changed=sorted(changed))))
    if packed and packed.exists() and digest(packed)!=entry.get('archive_sha256'):raise ValueError('Compressed archive changed')
    reclaimed=(sum(v['bytes'] for v in local['files'].values()) if raw.is_dir() else 0)+(packed.stat().st_size if packed and packed.exists() else 0)
    record=dict(stage=number,tag=r['tag'],raw_suite=str(raw),release=r['release'],publication_receipt=str(p.relative_to(ROOT)),remote_verified_at=datetime.datetime.now().astimezone().isoformat(),files=len(remote),file_bytes=sum(v['bytes'] for v in remote.values()),inventory_sha256=hashlib.sha256(json.dumps(remote,sort_keys=True).encode()).hexdigest(),symlinks=local['symlinks'],local_bytes_to_remove=reclaimed,status='verified_pending_local_removal')
    if args.apply:
     entries[r['tag']]=record;write(JOURNAL,journal)
     if live_users(raw):raise ValueError('Source became active after verification')
     if raw.is_dir() and inventory(raw)!=local:raise ValueError('Source changed while verifying')
     if raw.is_dir():shutil.rmtree(raw)
     if packed and packed.exists():packed.unlink()
     record['status']='github_only_full_raw';record['removed_at']=datetime.datetime.now().astimezone().isoformat();write(JOURNAL,journal)
     if r['tag'] in compact:
      compact[r['tag']]['status']='github_only_per_user_retention_policy';compact[r['tag']]['archive_available_locally']=False;write(INDEX,compact)
    plan.append(dict(stage=number,tag=r['tag'],status='removed_verified_local_raw' if args.apply else 'ready_to_remove',bytes=reclaimed))
   except Exception as error:plan.append(dict(stage=number,tag=r['tag'],status='kept_verification_failed',reason=str(error)))
 print(json.dumps(dict(apply=args.apply,protected=sorted(protected),plan=sorted(plan,key=lambda r:r['stage'])),ensure_ascii=False,indent=2))
if __name__=='__main__':main()
