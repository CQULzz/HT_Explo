from pathlib import Path
import json,urllib.request,tarfile,hashlib
root=Path('/home/lzz/pcd_test_20261110/source')
inv=json.load(open('/home/lzz/pcd_navigation_archive_inventory_20261110.json'))
release=json.loads((root/'release.json').read_text());assets={a['name']:a for a in release['assets']}
wanted={'runtime/local_map.npy','runtime/scene.sdf','runtime/scene_meshes.npz','model_assets/environment/ground.dae','model_assets/environment/obstacles.dae'}
offset=0;receipt=[]
for entry in inv['files']:
 header=offset+1024;offset+=1536+((entry['bytes']+511)//512)*512
 if entry['path'] not in wanted:continue
 part=header//536870912;lo=header%536870912;hi=lo+512+entry['bytes']-1
 asset=assets[f'navigation-fix.tar.part{part:03d}'];url=asset['browser_download_url']+'?map_range='+str(lo)
 request=urllib.request.Request(url,headers={'Range':f'bytes={lo}-{hi}','Accept-Encoding':'identity'})
 with urllib.request.urlopen(request,timeout=60) as response:
  if response.status!=206:raise RuntimeError('Server did not honor selective range: '+str(response.status))
  if response.headers.get('Content-Range','').split('/')[0]!=f'bytes {lo}-{hi}':raise RuntimeError('Wrong range')
  data=response.read(hi-lo+2)
 if len(data)!=hi-lo+1:raise RuntimeError('Wrong range length')
 member=tarfile.TarInfo.frombuf(data[:512],'utf-8','surrogateescape')
 assert member.name=='navigation-fix/'+entry['path'],(member.name,entry['path'])
 assert member.size==entry['bytes']
 payload=data[512:];digest=hashlib.sha256(payload).hexdigest();assert digest==entry['sha256']
 dest=root/entry['path'];dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists():assert dest.read_bytes()==payload
 else:dest.write_bytes(payload)
 receipt.append({'path':entry['path'],'sha256':digest,'bytes':len(payload),'asset':asset['browser_download_url'],'byte_range':[lo,hi],'archive_member':member.name})
 print('Recovered and SHA256 verified',entry['path'],len(payload),flush=True)
(root/'RECOVERY.json').write_text(json.dumps({'release':release['html_url'],'source_inventory':'navigation-fix-files.json','files':receipt,'scope':'Only selected map/runtime assets recovered by HTTP byte range; entire multipart archive was not downloaded or reverified.'},indent=2))
