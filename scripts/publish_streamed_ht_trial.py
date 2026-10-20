#!/usr/bin/env python3
"""Publish a frozen measured suite with bounded spool and explicit failed-capture status."""
import argparse
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time

from archive_legacy_ht_data import inventory, stream_parts, sha, gh, release, matches, write, REPO


def validate(suite,archive,tag,include_failed):
    state=json.loads((suite/'suite.json').read_text())
    if state.get('duration_s')!=600 or not state.get('runs'):
        raise ValueError('Expected a measured600s suite, not a planned-duration label alone')
    candidate=state['git_head']
    local=subprocess.check_output(['git','rev-parse',tag+'^{commit}'],text=True).strip()
    if local!=candidate:raise ValueError('Tag must identify the exact recorded candidate')
    tracked=json.loads((archive/'files_sha256.json').read_text())
    for name,expected in tracked.items():
        if sha(archive/name)!=expected:raise ValueError('Selected archive changed: '+name)
    validations={}
    for run in state['runs']:
        trial=suite/run['scenario'];manifest=trial/'manifest.json'
        if not manifest.exists():
            if not include_failed:raise ValueError('Missing measurement manifest')
            validations[run['scenario']]=dict(recorded_state=run['state'],complete600s=False,error='No measurement manifest')
            continue
        if json.loads(manifest.read_text())['git_head']!=candidate:
            raise ValueError('Mixed measured candidates in one suite')
        summary=trial/'summary.json'
        complete=(trial/'COMPLETED.json').exists() and summary.exists() and json.loads(summary.read_text()).get('duration_s')==600
        check_path=trial/'suite_validation.json'
        checks=json.loads(check_path.read_text())['checks'] if check_path.exists() else {}
        failed=[k for k,v in checks.items() if not v]
        if not include_failed and (not complete or run['state']!='RECORDED' or not checks or failed):
            raise ValueError('Unvalidated/incomplete recording; retain original failures with explicit --include-failed-recordings')
        validations[run['scenario']]=dict(recorded_state=run['state'],complete600s=complete,checks=checks,failed_checks=failed)
    all_good=all(r['complete600s'] and r.get('checks') and not r.get('failed_checks') and r['recorded_state']=='RECORDED' for r in validations.values())
    if not include_failed and state['state']!='COMPLETED':raise ValueError('Suite is not complete')
    return state,validations,'COMPLETE_VALIDATED_COLLECTION' if all_good else 'RETAINED_FAILURES_NOT_A_VALIDATED_COMPLETE_SUITE'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    for flag in ['suite','archive','notes','receipt']:ap.add_argument('--'+flag,type=Path,required=True)
    ap.add_argument('--tag',required=True);ap.add_argument('--title',required=True)
    ap.add_argument('--include-failed-recordings',action='store_true')
    ap.add_argument('--dry-run',action='store_true')
    ap.add_argument('--upload-timeout-seconds',type=float,default=180,
                    help='Deadline per asset attempt; bounded retries preserve local source and verify any completed remote asset.')
    a=ap.parse_args();suite=a.suite.resolve();archive=a.archive.resolve()
    if not 0<a.upload_timeout_seconds<float('inf'):ap.error('--upload-timeout-seconds must be finite and positive')
    state,validation,status=validate(suite,archive,a.tag,a.include_failed_recordings)
    print(json.dumps(dict(tested_commit=state['git_head'],collection_status=status,validation=validation),ensure_ascii=False,indent=2),flush=True)
    if a.dry_run:return
    obj=json.loads(gh('api',f'repos/{REPO}/git/ref/tags/{a.tag}'))['object']
    while obj['type']=='tag':obj=json.loads(gh('api',f'repos/{REPO}/git/tags/'+obj['sha']))['object']
    if obj['type']!='commit' or obj['sha']!=state['git_head']:raise ValueError('Remote measured tag mismatch')
    tags=json.loads(gh('release','list','--repo',REPO,'--limit','100','--json','tagName'))
    if not any(r['tagName']==a.tag for r in tags):
        gh('release','create',a.tag,'--repo',REPO,'--verify-tag','--prerelease','--title',a.title,'--notes-file',str(a.notes))
    else:
        gh('release','edit',a.tag,'--repo',REPO,'--title',a.title,'--notes-file',str(a.notes))
    existing={r['name']:r for r in release(a.tag)['assets']}
    previous=json.loads(a.receipt.read_text()) if a.receipt.exists() else None
    receipt=dict(tag=a.tag,tested_commit=state['git_head'],raw_suite=str(suite),result_archive=str(archive),
                 release=f'https://github.com/{REPO}/releases/tag/{a.tag}',publication_status=status,
                 collection_validation=validation,
                 recording_scope='All published HT/control/odom/status/TARE routes; source-second lidar and periodic maps/model inputs; not lossless all-frequency raw sensor data.',
                 transport='Deterministic streaming tar+zstd,512MiB parts; three shared spool slots, at most1.5GiB temporary transport.',assets=[])
    def upload(path):
        expected=dict(name=path.name,bytes=path.stat().st_size,sha256=sha(path))
        if path.name not in existing:
            for attempt in range(4):
                current={x['name']:x for x in release(a.tag)['assets']}
                if path.name in current:
                    if not matches(current[path.name],expected):raise ValueError('Existing asset differs: '+path.name)
                    existing[path.name]=current[path.name];break
                print('Uploading',path.name,expected['bytes'],flush=True)
                try:subprocess.run(['gh','release','upload',a.tag,str(path),'--repo',REPO],check=True,
                                   timeout=a.upload_timeout_seconds)
                except (subprocess.CalledProcessError,subprocess.TimeoutExpired) as error:
                    print('Upload attempt interrupted',path.name,type(error).__name__,
                          'local source retained; rechecking remote before retry',flush=True)
                    if attempt==3:raise
                    time.sleep(2**attempt)
            current={x['name']:x for x in release(a.tag)['assets']}
            if path.name not in current or not matches(current[path.name],expected):raise ValueError('Remote verification failed: '+path.name)
            existing[path.name]=current[path.name]
        elif not matches(existing[path.name],expected):raise ValueError('Refuse to clobber asset: '+path.name)
        return expected
    with tempfile.TemporaryDirectory(prefix='ht-streamed-release-') as temporary:
        temp=Path(temporary);slots=threading.BoundedSemaphore(3)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            for label,source in [('raw',suite),('results',archive)]:
                print('Inventory',label,source,flush=True)
                entries=inventory(source)
                file_list=[{k:e[k] for k in ['path','bytes','sha256']} for e in entries if e['kind']=='file']
                inventory_file=temp/(a.tag+'-'+label+'-files.json');write(inventory_file,file_list)
                topology_hash=hashlib.sha256(json.dumps(entries,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
                receipt[label+'_inventory_sha256']=sha(inventory_file)
                receipt[label+'_topology_sha256']=topology_hash
                if previous and (previous.get(label+'_inventory_sha256')!=sha(inventory_file) or previous.get(label+'_topology_sha256')!=topology_hash):
                    raise ValueError('Previously published source changed; preserve differences instead of skipping')
                prefix=a.tag+'-'+label
                receipt['assets']+=stream_parts(source,entries,temp,prefix,upload,upload_pool=pool,spool_slots=slots)
                receipt['assets'].append(upload(inventory_file))
        for run in state['runs']:
            video=archive/run['scenario']/'camera_h264.mp4'
            if video.exists():
                target=temp/(a.tag+'-'+run['scenario']+'.mp4');target.hardlink_to(video)
                receipt['assets'].append(upload(target))
        proof=temp/(a.tag+'-SHA256.json');write(proof,receipt)
        receipt['assets'].append(upload(proof))
        final={r['name']:r for r in release(a.tag)['assets']}
        if not all(x['name'] in final and matches(final[x['name']],x) for x in receipt['assets']):raise ValueError('Complete remote verification failed')
        receipt['verified_at']=datetime.datetime.now().astimezone().isoformat()
        write(a.receipt,receipt)
    print('Verified:',receipt['release'],flush=True)


if __name__=='__main__':main()
