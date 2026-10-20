#!/usr/bin/env python3
"""Independently recheck all legacy remote assets, receipts and source inventories."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import subprocess
from archive_legacy_ht_data import ROOT, OUT, inventory, sha, release, write, REPO


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check-local-bytes',action='store_true')
    args=ap.parse_args()
    records=json.loads((OUT/'mapping.json').read_text())['datasets']
    receipts={p.stem:json.loads(p.read_text()) for p in (OUT/'receipts').glob('*.json')}
    if set(receipts)!={r['dataset'] for r in records}:
        raise ValueError('Not all selected datasets have complete receipts')
    tags=sorted({r['tag'] for r in records})
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        remotes=dict(zip(tags,pool.map(release,tags),strict=True))
    results=[]
    for record in records:
        name=record['dataset'];r=receipts[name]
        inv_path=OUT/'inventories'/(name+'.json')
        inv=json.loads(inv_path.read_text())
        assert sha(inv_path)==r['inventory_sha256'],name
        assert r['file_bytes']==sum(e.get('bytes',0) for e in inv['entries']),name
        assert r['files']==sum(e['kind']=='file' for e in inv['entries']),name
        assert r['tag']==record['tag'] and inv['provenance']==record,name
        remote={a['name']:a for a in remotes[r['tag']]['assets']}
        for a in r['assets']:
            actual=remote[a['name']]
            assert actual['state']=='uploaded' and actual['size']==a['bytes'],a['name']
            assert actual.get('digest')=='sha256:'+a['sha256'],a['name']
        parts=[a['name'] for a in r['assets'] if '.tar.zst.part' in a['name']]
        assert parts==[r['content_key']+f'.tar.zst.part{i:03d}' for i in range(len(parts))],name
        assert len(parts)>0,name
        if args.check_local_bytes:
            assert inventory(ROOT/record['source'])==inv['entries'],name
        results.append(dict(dataset=name,tag=r['tag'],file_bytes=r['file_bytes'],assets=len(r['assets']),verified=True))
        print('PASS',name,flush=True)
    total=dict(datasets=len(results),file_bytes=sum(r['file_bytes'] for r in results),
               assets=sum(r['assets'] for r in results),release_count=len(tags),
               local_file_bytes_rechecked=args.check_local_bytes,results=results)
    write(OUT/'final_verification.json',total)
    print(json.dumps({k:v for k,v in total.items() if k!='results'},indent=2))


if __name__=='__main__':main()
