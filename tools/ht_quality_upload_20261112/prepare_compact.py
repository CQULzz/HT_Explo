"""Package experiment evidence without videos, MCAPs, or shared dependencies."""
from pathlib import Path
import hashlib,json,os,tarfile

OUT=Path('/home/lzz/ht_quality_compact_20261112')
ROOTS=[Path('/home/lzz/ht_quality_20261111'),Path('/home/lzz/ht_quality_600s_20261112')]
VIDEO_SUFFIXES={'.mp4','.mov','.avi','.mkv','.webm'}

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    OUT.mkdir(exist_ok=False);assets=[];datasets=[]
    for root in ROOTS:
        inventory=[];links=[];excluded=[]
        for p in sorted(root.rglob('*')):
            if any(x in p.parts for x in ['__pycache__','.git']) or p.suffix in ['.pyc','.nbi','.nbc']:continue
            rel=str(Path(root.name)/p.relative_to(root))
            if p.is_symlink():links.append({'path':rel,'target':os.readlink(p)});continue
            if not p.is_file():continue
            if p.suffix=='.mcap' or p.suffix.lower() in VIDEO_SUFFIXES:
                excluded.append({'path':rel,'bytes':p.stat().st_size,'reason':'raw_mcap' if p.suffix=='.mcap' else 'video'});continue
            inventory.append({'path':rel,'bytes':p.stat().st_size,'sha256':sha(p)})
        listing=OUT/(root.name+'--DATA_FILES_SHA256.json');listing.write_text(json.dumps(inventory,indent=2))
        deps=OUT/(root.name+'--DEPENDENCY_LINKS.json');deps.write_text(json.dumps(links,indent=2))
        archive=OUT/(root.name+'--data-no-video.tar.gz')
        with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
            for item in inventory:tar.add(root/Path(item['path']).relative_to(root.name),arcname=item['path'],recursive=False)
            tar.add(listing,arcname=root.name+'/DATA_FILES_SHA256.json',recursive=False)
            tar.add(deps,arcname=root.name+'/DEPENDENCY_LINKS.json',recursive=False)
        by_name={x['path']:x for x in inventory}
        with tarfile.open(archive,'r:gz') as tar:
            for member in tar:
                if not member.isfile() or Path(member.name).suffix.lower() in VIDEO_SUFFIXES or member.name.endswith('.mcap'):
                    raise RuntimeError('Unexpected media or non-regular member in compact data archive')
                if member.name in by_name:
                    h=hashlib.sha256();f=tar.extractfile(member)
                    for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
                    if h.hexdigest()!=by_name[member.name]['sha256']:raise RuntimeError('Packaged evidence bytes mismatch')
        assets.append({'name':archive.name,'path':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'kind':'compact_experiment_data'})
        datasets.append({'source':str(root),'included_files':len(inventory),'included_regular_bytes':sum(x['bytes'] for x in inventory),'excluded':excluded,'inventory':str(listing)})
        print(json.dumps({'archive':archive.name,'archive_bytes':archive.stat().st_size,'included_files':len(inventory),'excluded_mcap_or_video':len(excluded)}),flush=True)
    manifest={'scope':'Compact experiment data only: metrics/CSV, audits/JSON, parameters, snapshots, logs and recorded runtime evidence. No raw MCAP or video files. Shared dependency symlinks are inventoried but not followed. Raw data remains local.',
              'branch':'sim/ht-height-quality-20261111','tag':'ht-quality-data-20261112','datasets':datasets,
              'assets':[{k:v for k,v in x.items() if k!='path'} for x in assets]}
    path=OUT/'DATA_MANIFEST.json';path.write_text(json.dumps(manifest,indent=2))
    assets.append({'name':path.name,'path':str(path),'bytes':path.stat().st_size,'sha256':sha(path),'kind':'compact_data_manifest'})
    (OUT/'PLAN.json').write_text(json.dumps({'scope':'compact_no_mcap_no_video','tag':manifest['tag'],'branch':manifest['branch'],'assets':assets},indent=2))

if __name__=='__main__':main()
