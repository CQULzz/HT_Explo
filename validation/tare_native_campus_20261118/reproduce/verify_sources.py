from pathlib import Path
import urllib.request,json,hashlib,concurrent.futures
work=Path('/mnt/d/TARE-Native-Campus-20261118')
cases=[('tare','caochao39/tare_planner','b6760adb4280b379567c76f4e684ce628e28ef71',Path('/home/lzz/tare_native_20261110')),('cmu','caochao39/autonomous_exploration_development_environment','158e67b31b644ed1e8b06eb1d7f70e183cc62591',Path('/home/lzz/cmu_sim_20261110'))]
def check(case):
 label,repo,commit,root=case;url=f'https://api.github.com/repos/{repo}/git/trees/{commit}?recursive=1'
 req=urllib.request.Request(url,headers={'User-Agent':'HT-native-baseline-verification'})
 with urllib.request.urlopen(req,timeout=40) as response:tree=json.load(response)
 (work/(label+'_UPSTREAM_TREE.json')).write_text(json.dumps(tree))
 records=[]
 for entry in tree['tree']:
  path=entry['path'];p=root/path
  if entry['type']!='blob' or not path.startswith('src/') or p.suffix not in ['.cpp','.h','.hpp','.yaml','.launch','.xacro','.sdf','.world','.txt','.xml']:continue
  if not p.exists():records.append({'path':path,'status':'missing'});continue
  data=p.read_bytes();digest=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest();records.append({'path':path,'upstream_git_blob':entry['sha'],'local_git_blob':digest,'equal':digest==entry['sha']})
 out={'repository':repo,'commit':commit,'source_root':str(root),'api_tree_url':url,'records':records,'changed':[e for e in records if not e.get('equal',False)]};(work/(label+'_SOURCE_CHECK.json')).write_text(json.dumps(out,indent=2));return {'label':label,'checked':len(records),'changed':out['changed']}
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
 for result in pool.map(check,cases):print(json.dumps(result))
for name in ['aede_tare_indoor_baseline_20261117/baseline.launch.py','ht_helios_collision_20261115/scene_assets/campus.world']:
 p=Path('/home/lzz')/name;print('FILE',p);print(p.read_text()[:6500])
