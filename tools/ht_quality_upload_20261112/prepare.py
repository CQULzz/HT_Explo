"""Prepare immutable original-byte release assets without copying large MCAPs."""
from pathlib import Path
import hashlib,json,os,subprocess,tarfile,time

PROJECT=Path('/home/lzz/HT_Explo_quality_20261111')
OUT=Path('/home/lzz/ht_quality_github_20261112')
REPO='CQULzz/HT_Explo'
BRANCH='sim/ht-height-quality-20261111'
SPECS=[
    ('ht-quality-300s-20261111',Path('/home/lzz/ht_quality_20261111'),
     '68e53304ca3296a7a863fdb2c41ec52e5caafceb','300s quality-fix experiment'),
    ('ht-quality-600s-20261112',Path('/home/lzz/ht_quality_600s_20261112'),
     '03521b858e9b7e48ee5ce3111fe640ce6c627dd5','600s repeat and interrupted first attempt'),
]

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    OUT.mkdir(exist_ok=True)
    plans=[]
    for tag,root,commit,label in SPECS:
        directory=OUT/tag;directory.mkdir(exist_ok=True)
        assets=[];inventory=[];links=[]
        expected=json.loads((root/'evidence/RAW_SHA256.json').read_text())
        paths=sorted(root.rglob('*'))
        for number,p in enumerate(paths):
            if any(x in p.parts for x in ['__pycache__','.git']) or p.suffix in ['.pyc','.nbi','.nbc']:continue
            rel=str(Path(root.name)/p.relative_to(root))
            if p.is_symlink():links.append({'path':rel,'target':os.readlink(p)});continue
            if not p.is_file():continue
            sha=digest(p);size=p.stat().st_size
            if str(p) in expected and (size!=expected[str(p)]['bytes'] or sha!=expected[str(p)]['sha256']):
                raise RuntimeError('Original raw receipt mismatch: '+str(p))
            item={'path':rel,'bytes':size,'sha256':sha};inventory.append(item)
            if p.suffix=='.mcap':
                run=p.parent.parent.name
                name=tag+'--'+run+'--'+p.name
                target=directory/name
                if target.exists():
                    if not os.path.samefile(p,target):raise RuntimeError('Unexpected existing transport file: '+str(target))
                else:os.link(p,target)
                assets.append({'name':name,'path':str(target),'restore_path':rel,
                               'bytes':size,'sha256':sha,'kind':'original_mcap'})
                print(json.dumps({'tag':tag,'prepared_original_mcap':name,'bytes':size}),flush=True)
        missing=[p for p in expected if not any(x['path']==str(Path(root.name)/Path(p).relative_to(root)) for x in inventory)]
        if missing:raise RuntimeError('Raw receipt files missing: '+repr(missing))
        (directory/'FILES_SHA256.json').write_text(json.dumps(inventory,indent=2))
        (directory/'DEPENDENCY_LINKS.json').write_text(json.dumps({'scope':'Original dependency symlinks are inventoried but not dereferenced into this data backup. Full raw recordings, regular evidence files, and frozen runtime archives are included. Shared Python/ROS/CMU installations are not repackaged.','links':links},indent=2))
        archive=directory/(tag+'--evidence.tar.gz')
        if archive.exists():
            backup=archive.with_name(archive.name+'.previous-'+str(time.time_ns()))
            archive.rename(backup)
        with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
            for item in inventory:
                p=root/Path(item['path']).relative_to(root.name)
                if p.suffix!='.mcap':tar.add(p,arcname=item['path'],recursive=False)
            tar.add(directory/'FILES_SHA256.json',arcname='FILES_SHA256.json')
            tar.add(directory/'DEPENDENCY_LINKS.json',arcname='DEPENDENCY_LINKS.json')
        # Verify packaged bytes, not just the generated transport filename.
        by_path={x['path']:x for x in inventory}
        with tarfile.open(archive,'r:gz') as tar:
            for member in tar:
                if member.name not in by_path:continue
                stream=tar.extractfile(member);h=hashlib.sha256()
                for block in iter(lambda:stream.read(4*1024*1024),b''):h.update(block)
                if member.size!=by_path[member.name]['bytes'] or h.hexdigest()!=by_path[member.name]['sha256']:
                    raise RuntimeError('Archive member mismatch: '+member.name)
        for path,kind in [(archive,'evidence_archive'),(directory/'FILES_SHA256.json','file_inventory'),(directory/'DEPENDENCY_LINKS.json','dependency_inventory')]:
            assets.append({'name':path.name,'path':str(path),'bytes':path.stat().st_size,'sha256':digest(path),'kind':kind})
        # The full source already exists in GitHub Git; avoid fetching unrelated
        # historical blobs into this sparse checkout just to duplicate it.
        code=directory/(tag+'--SOURCE_REFERENCE.json')
        code.write_text(json.dumps({'repository':REPO,'branch':BRANCH,'commit':commit,
            'tree_url':f'https://github.com/{REPO}/tree/{commit}',
            'full_source_archive_url':f'https://github.com/{REPO}/archive/{commit}.tar.gz',
            'tested_runtime_source':'Each run/evidence archive retains its frozen_runtime.tar.gz with tested source, parameters and binaries.'},indent=2))
        assets.append({'name':code.name,'path':str(code),'bytes':code.stat().st_size,'sha256':digest(code),'kind':'source_reference'})
        for source in sorted((root/'delivery').glob('*.mp4')):
            target=directory/(tag+'--'+source.name)
            if not target.exists():os.link(source,target)
            elif not os.path.samefile(source,target):raise RuntimeError('Unexpected existing video transport')
            assets.append({'name':target.name,'path':str(target),'bytes':target.stat().st_size,'sha256':digest(target),'kind':'trajectory_video'})
        if any(x['bytes']>=2*1024**3 for x in assets):raise RuntimeError('Asset exceeds the verified GitHub release limit')
        manifest={'repository':REPO,'branch':BRANCH,'tag':tag,'target_commit':commit,'label':label,
                  'original_file_count':len(inventory),'original_regular_bytes':sum(x['bytes'] for x in inventory),
                  'assets':[{k:v for k,v in x.items() if k!='path'} for x in assets],
                  'scope':'Original MCAP byte streams, including interrupted data, with evidence/metadata archive. Restore original MCAP basenames and paths using restore_path. Never relabel interrupted attempt as complete.'}
        manifest_path=directory/(tag+'--MANIFEST.json');manifest_path.write_text(json.dumps(manifest,indent=2))
        assets.append({'name':manifest_path.name,'path':str(manifest_path),'bytes':manifest_path.stat().st_size,'sha256':digest(manifest_path),'kind':'publication_manifest'})
        notes=directory/'RELEASE_NOTES.md'
        notes.write_text(f'实验数据：{label}\n\n对应分支：`{BRANCH}`\n对应代码及报告提交：`{commit}`\n\n完整原始MCAP逐文件保留；包含中断/失败记录，不把失败当成功。其他CSV、参数、日志、冻结、审计、地图快照和报告在evidence.tar.gz，视频单列。MANIFEST.json给出逐附件SHA256与原始还原路径；FILES_SHA256.json核对还原后的全部常规文件。外部共享ROS/CMU/Python环境不随数据打包，依赖链接在DEPENDENCY_LINKS.json中列明。\n\n本附件是实验归档，不是实车部署或算法无缺陷声明。\n')
        plans.append({'tag':tag,'target_commit':commit,'branch':BRANCH,'title':tag+' | '+label,
                      'notes':str(notes),'assets':assets,'manifest':str(manifest_path)})
        print(json.dumps({'prepared_tag':tag,'assets':len(assets),'original_files':len(inventory)}),flush=True)
    plan={'repository':REPO,'branch':BRANCH,'status':'prepared_awaiting_authenticated_upload',
          'prepared_wall_time':time.time(),'releases':plans}
    (OUT/'PLAN.json').write_text(json.dumps(plan,indent=2))
    print(json.dumps({'prepared':True,'releases':len(plans),'total_assets':sum(len(x['assets']) for x in plans)}),flush=True)

if __name__=='__main__':main()
