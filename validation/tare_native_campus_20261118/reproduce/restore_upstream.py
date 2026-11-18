from pathlib import Path
import json,urllib.request,hashlib,difflib,shutil,concurrent.futures
work=Path('/mnt/d/TARE-Native-Campus-20261118');root=Path('/home/lzz/tare_native_campus_20261118');root.mkdir(exist_ok=False);(root/'setup').mkdir();(root/'runs').mkdir();(root/'analysis').mkdir()
src=root/'project/src/tare_planner';shutil.copytree('/home/lzz/tare_native_20261110/src/tare_planner',src)
check=json.loads((work/'tare_SOURCE_CHECK.json').read_text())
def restore(e):
 if e['status']=='missing' if 'status' in e else False:return None
 path=e['path'];url='https://raw.githubusercontent.com/'+check['repository']+'/'+check['commit']+'/'+path
 with urllib.request.urlopen(url,timeout=40) as r:data=r.read()
 assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==e['upstream_git_blob']
 original=Path(check['source_root'])/path;relative=Path(path).relative_to('src/tare_planner');target=src/relative
 patch=''.join(difflib.unified_diff(data.decode().splitlines(True),original.read_text().splitlines(True),fromfile='upstream/'+path,tofile='existing/'+path));(work/(relative.name+'.existing.diff')).write_text(patch);target.write_bytes(data);return {'path':str(relative),'existing_diff':patch[:18000]}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for e in pool.map(restore,check['changed']):
  if e:print(json.dumps(e))
# Verify every original package file before any documented ROS compatibility edit.
bad=[];n=0
for e in check['records']:
 if not e['path'].startswith('src/tare_planner/'):continue
 p=src/Path(e['path']).relative_to('src/tare_planner');data=p.read_bytes();n+=1
 if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=e['upstream_git_blob']:bad.append(str(p))
assert not bad,bad
(root/'setup/UPSTREAM_RESTORED.json').write_text(json.dumps({'commit':check['commit'],'package_files_verified':n,'all_match_upstream':True,'shared_source_unchanged':True},indent=2));print('Allpackagefilesverified',n)
p=src/'src/sensor_coverage_planner/sensor_coverage_planner_ground.cpp';text=p.read_text();print('FRONTIER_LINES',[(i+1,l) for i,l in enumerate(text.splitlines()) if 'kUseFrontier' in l])
