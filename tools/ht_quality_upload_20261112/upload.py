"""Publish prepared experiment data; verify every server-side size and SHA256."""
from pathlib import Path
import json,subprocess,time

ROOT=Path('/home/lzz/ht_quality_github_20261112')
PROJECT=Path('/home/lzz/HT_Explo_quality_20261111')
REPO='CQULzz/HT_Explo'

def gh(*args,check=True,timeout=180):
    p=subprocess.run(['gh',*args],capture_output=True,text=True,timeout=timeout)
    if check and p.returncode:raise RuntimeError('gh command failed: '+p.stderr[-1500:])
    return p

def api(path,payload=None):
    args=['api','-H','Accept: application/vnd.github+json','-H','X-GitHub-Api-Version: 2022-11-28',path]
    if payload is not None:
        request=ROOT/'api_request.json';request.write_text(json.dumps(payload))
        args+=['--method','POST','--input',str(request)]
    return json.loads(gh(*args).stdout)

def matches(remote,local):
    return remote.get('state')=='uploaded' and remote['size']==local['bytes'] and remote.get('digest')=='sha256:'+local['sha256']

def main():
    plan=json.loads((ROOT/'PLAN.json').read_text())
    # Authentication is supplied by the user's normal gh login, never by a logged token.
    gh('auth','status')
    permissions=api('repos/'+REPO).get('permissions',{})
    if not permissions.get('push'):raise RuntimeError('Authenticated account lacks repository write access')
    receipts=[]
    for release_plan in plan['releases']:
        tag=release_plan['tag'];commit=release_plan['target_commit']
        subprocess.run(['git','-C',str(PROJECT),'merge-base','--is-ancestor',commit,'HEAD'],check=True)
        local=subprocess.run(['git','-C',str(PROJECT),'rev-parse','--verify','refs/tags/'+tag+'^{commit}'],capture_output=True,text=True)
        if local.returncode:
            subprocess.run(['git','-C',str(PROJECT),'tag',tag,commit],check=True)
        elif local.stdout.strip()!=commit:raise RuntimeError('Existing local tag has a different commit')
        subprocess.run(['git','-C',str(PROJECT),'push','origin','refs/tags/'+tag],check=True)
        ref=api('repos/'+REPO+'/git/ref/tags/'+tag)['object']
        while ref['type']=='tag':ref=api('repos/'+REPO+'/git/tags/'+ref['sha'])['object']
        if ref['sha']!=commit or ref['type']!='commit':raise RuntimeError('Remote experiment tag mismatch')
        existing=gh('api','repos/'+REPO+'/releases/tags/'+tag,check=False)
        if existing.returncode:
            if '404' not in existing.stderr:raise RuntimeError(existing.stderr[-1000:])
            release=api('repos/'+REPO+'/releases',{'tag_name':tag,'target_commitish':commit,
                'name':release_plan['title'],'body':Path(release_plan['notes']).read_text(),
                'draft':True,'prerelease':True,'make_latest':'false'})
        else:release=json.loads(existing.stdout)
        release_id=release['id'];verified=[]
        for i,asset in enumerate(release_plan['assets']):
            print(json.dumps({'tag':tag,'asset':asset['name'],'number':i+1,'total':len(release_plan['assets']),'bytes':asset['bytes'],'stage':'checking_or_uploading'}),flush=True)
            remote={x['name']:x for x in api(f'repos/{REPO}/releases/{release_id}/assets?per_page=100')}
            if asset['name'] in remote:
                detail=api(f'repos/{REPO}/releases/assets/'+str(remote[asset['name']]['id']))
                if not matches(detail,asset):raise RuntimeError('Existing remote asset conflict; preserved: '+asset['name'])
            else:
                failure=None
                for attempt in range(3):
                    try:
                        result=gh('release','upload',tag,asset['path'],'--repo',REPO,check=False,timeout=2400)
                        failure=result.stderr[-1200:] if result.returncode else None
                    except subprocess.TimeoutExpired:failure='Upload command timed out'
                    remote={x['name']:x for x in api(f'repos/{REPO}/releases/{release_id}/assets?per_page=100')}
                    if asset['name'] in remote:
                        detail=api(f'repos/{REPO}/releases/assets/'+str(remote[asset['name']]['id']))
                        if matches(detail,asset):break
                        if detail.get('state')=='starter':
                            # Only this newly-created owned upload can be quarantined.
                            renamed='incomplete-'+str(detail['id'])+'-'+asset['name']
                            gh('api','--method','PATCH',f'repos/{REPO}/releases/assets/'+str(detail['id']),'-f','name='+renamed)
                            print(json.dumps({'preserved_incomplete_asset':renamed,'attempt':attempt+1}),flush=True)
                        else:raise RuntimeError('Remote digest/size mismatch; preserved asset: '+asset['name'])
                    if attempt==2:raise RuntimeError('Upload failed after retries: '+str(failure))
                    time.sleep(3)
                else:raise RuntimeError('Asset never verified')
            verified.append({'name':asset['name'],'asset_id':detail['id'],'bytes':detail['size'],
                             'sha256':asset['sha256'],'remote_digest':detail['digest'],
                             'url':detail['browser_download_url'],'size_and_sha256_verified':True})
            receipt={'tag':tag,'target_commit':commit,'branch':release_plan['branch'],
                     'release_id':release_id,'status':'uploading','verified_assets':verified,
                     'expected_assets':len(release_plan['assets'])}
            (ROOT/(tag+'--REMOTE_RECEIPT.json')).write_text(json.dumps(receipt,indent=2))
            print(json.dumps({'tag':tag,'verified':i+1,'total':len(release_plan['assets'])}),flush=True)
        # Publish only once every original-byte asset is verified. No incomplete release is called complete.
        updated=gh('api','--method','PATCH',f'repos/{REPO}/releases/{release_id}',
                   '-F','draft=false','-F','prerelease=true','-f','make_latest=false')
        release=json.loads(updated.stdout)
        final_assets=api(f'repos/{REPO}/releases/{release_id}/assets?per_page=100')
        by_name={x['name']:x for x in final_assets}
        if any(x['name'] not in by_name or not matches(by_name[x['name']],x) for x in release_plan['assets']):
            raise RuntimeError('Final remote verification failed')
        receipt.update(status='complete_verified',release_url=release['html_url'],verified_wall_time=time.time())
        (ROOT/(tag+'--REMOTE_RECEIPT.json')).write_text(json.dumps(receipt,indent=2));receipts.append(receipt)
    (ROOT/'REMOTE_VERIFIED.json').write_text(json.dumps({'status':'complete_verified','repository':REPO,'branch':plan['branch'],'releases':receipts},indent=2))
    print(json.dumps({'all_releases_verified':True,'releases':len(receipts)}),flush=True)

if __name__=='__main__':main()
