import datetime as dt,fcntl,gzip,hashlib,json,os,shutil,subprocess,sys,tarfile
from pathlib import Path
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from archive_legacy_ht_data import release,sha,matches,write
out=ROOT/'docs/results/ht_xytheta_transparent_voxels_2026-10-22';runtime=ROOT/'.git/transparent-voxel-runtime';tag='ht-stage-20261021-campus-matched';branch='codex/ht-transparent-voxels-20261022';base='ffab5bd03642c49872fd0aefe8fb58a21ec2d4e1'
assert json.loads((out/'validation.json').read_text())['raw_snapshot_matches_cached_display_channels']
shutil.copy2(out/'renderer_snapshot.py',ROOT/'presentations/rviz_transparent_voxel_replay.py')
shutil.copy2(__file__,out/'publish_snapshot.py')
write(out/'files_sha256.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file() and p.name!='files_sha256.json'})
upload=runtime/'upload';upload.mkdir(exist_ok=True)
movie=upload/'stage48-xytheta-transparent-voxels-4x.mp4';png=upload/'stage48-ht-eight-direction-grid.png'
for source,dest in [(out/'video/rviz_detail_4x.mp4',movie),(out/'audit/eight_directions.png',png)]:
 if not dest.exists():dest.hardlink_to(source)
 if sha(source)!=sha(dest):raise RuntimeError('Upload alias has different bytes')
archive=upload/'stage48-transparent-voxel-supplement.tar.gz'
with archive.open('wb') as raw:
 with gzip.GzipFile(filename='',mode='wb',fileobj=raw,mtime=0) as zipped:
  with tarfile.open(fileobj=zipped,mode='w|',format=tarfile.PAX_FORMAT) as tar:
   for p in [out]+sorted(out.rglob('*')):
    info=tar.gettarinfo(str(p),arcname=str(Path(out.name)/p.relative_to(out)))
    info.uid=info.gid=info.mtime=0;info.uname=info.gname=''
    if p.is_file():
     with p.open('rb') as f:tar.addfile(info,f)
    elif p.is_dir():tar.addfile(info)
    else:raise RuntimeError('Unexpected source type')
before=release(tag);existing={x['name']:x for x in before['assets']};assets=[]
for file in [movie,png,archive]:
 expect=dict(name=file.name,bytes=file.stat().st_size,sha256=sha(file));found=existing.get(file.name)
 if found is None:
  print('Uploading',file.name,expect['bytes'],flush=True)
  subprocess.run(['gh','release','upload',tag,str(file),'--repo','CQULzz/HT_Explo'],check=True,timeout=600)
  found=next(x for x in release(tag)['assets'] if x['name']==file.name)
 if not matches(found,expect):raise RuntimeError('Remote size/SHA verification failed')
 assets.append(dict(**expect,url=found['browser_download_url']));print('Verified',file.name,flush=True)
after=release(tag);current={x['id']:x for x in after['assets']}
prior_unchanged=all(x['id'] in current and (x['name'],x['state'],x['size'],x.get('digest'))==(current[x['id']]['name'],current[x['id']]['state'],current[x['id']]['size'],current[x['id']].get('digest')) for x in before['assets'])
if not prior_unchanged:raise RuntimeError('An existing Release asset changed')
receipt=ROOT/'docs/experiments/publication_addenda/stage48_transparent_voxels.json'
write(receipt,dict(tag=tag,assets=assets,verified_at=dt.datetime.now().astimezone().isoformat(),existing_assets_preserved=len(before['assets']),existing_assets_unchanged=True,source_branch=branch,publication_branch_base=base,recorded_candidate='f7fd77b66fc442752599ead359e8aa60e7773ae4',scope='Visualization supplement of existing Campus data; not a new navigation experiment. Shared main worktree/index/HEAD and concurrent CuPy/RViz changes are not staged or reset.'))
# A private index creates a scoped side branch without staging another task's work.
index=runtime/'publication.index';env=dict(os.environ,GIT_INDEX_FILE=str(index))
paths=['.gitignore','presentations/audit_ht_direction_layers.py','presentations/rviz_transparent_voxel_replay.py','scripts/play_ht_transparent_voxels.sh',str(out.relative_to(ROOT)),str(receipt.relative_to(ROOT))]
with (ROOT/'.git/ht-results-publication.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 if subprocess.run(['git','show-ref','--verify','--quiet','refs/heads/'+branch]).returncode==0:raise RuntimeError('Publication branch already exists; inspect before moving it')
 subprocess.run(['git','read-tree',base],check=True,env=env)
 subprocess.run(['git','add','--',*paths],check=True,env=env)
 tree=subprocess.check_output(['git','write-tree'],text=True,env=env).strip()
 message=runtime/'commit_message.txt';message.write_text('Visualize recorded HT headings as transparent voxels and audit layer differences\n\nRecorded stage48 data only; preserve the shared worktree and concurrent navigation changes.\n')
 commit=subprocess.check_output(['git','-c','user.name=Codex','-c','user.email=codex@local','commit-tree',tree,'-p',base,'-F',str(message)],text=True,env=env).strip()
 subprocess.run(['git','update-ref','refs/heads/'+branch,commit,'0'*40],check=True)
 subprocess.run(['git','push','origin',commit+':refs/heads/'+branch],check=True)
write(runtime/'publication_complete.json',dict(branch=branch,commit=commit,assets=assets,all_remote_verified=True,old_assets_unchanged=prior_unchanged))
print('COMPLETE',commit,branch,flush=True)
