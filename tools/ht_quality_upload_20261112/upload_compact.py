"""Upload only the user-selected compact experiment data, without videos/MCAP."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import argparse,json,subprocess,time
from with_keyring import credential_environment

ROOT=Path('/home/lzz/ht_quality_compact_20261112')
PROJECT=Path('/home/lzz/HT_Explo_quality_20261111')
REPO='CQULzz/HT_Explo'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--commit',required=True);a=parser.parse_args()
    plan=json.loads((ROOT/'PLAN.json').read_text());tag=plan['tag'];env=credential_environment()
    def gh(*args,check=True,timeout=180):
        result=subprocess.run(['gh',*args],env=env,capture_output=True,text=True,timeout=timeout)
        if check and result.returncode:raise RuntimeError(result.stderr[-1200:])
        return result
    def api(path):return json.loads(gh('api','-H','X-GitHub-Api-Version: 2022-11-28',path).stdout)
    def valid(remote,asset):return remote.get('state')=='uploaded' and remote.get('size')==asset['bytes'] and remote.get('digest')=='sha256:'+asset['sha256']
    subprocess.run(['git','-C',str(PROJECT),'merge-base','--is-ancestor',a.commit,plan['branch']],check=True)
    local=subprocess.run(['git','-C',str(PROJECT),'rev-parse','--verify',tag+'^{commit}'],capture_output=True,text=True)
    if local.returncode:subprocess.run(['git','-C',str(PROJECT),'tag',tag,a.commit],check=True)
    elif local.stdout.strip()!=a.commit:raise RuntimeError('Existing data tag mismatch')
    subprocess.run(['git','-C',str(PROJECT),'push','origin','refs/tags/'+tag],check=True)
    ref=api('repos/'+REPO+'/git/ref/tags/'+tag)['object']
    if ref['type']!='commit' or ref['sha']!=a.commit:raise RuntimeError('Remote data tag does not match intended branch commit')
    matches=[x for x in api('repos/'+REPO+'/releases?per_page=100') if x['tag_name']==tag]
    if len(matches)>1:raise RuntimeError('Ambiguous data release')
    if matches:release=matches[0]
    else:
        payload={'tag_name':tag,'target_commitish':a.commit,'name':'HT quality compact experiment data | 300s + 600s',
            'body':'按用户最新要求，只上传精简实验数据：CSV指标、JSON审计、参数、地图快照、诊断日志和必要冻结证据。两个数据包分别包含300秒和600秒实验（含中断记录）。不包含原始MCAP或视频，原始大录包保留本机，不构成原始录包的完整远端备份。代码和可读指标在sim/ht-height-quality-20261111分支；DATA_MANIFEST.json提供附件SHA256，包内DATA_FILES_SHA256.json提供逐文件校验。',
            'draft':True,'prerelease':True,'make_latest':'false'}
        request=ROOT/'REQUEST.json';request.write_text(json.dumps(payload));release=json.loads(gh('api','--method','POST','repos/'+REPO+'/releases','--input',str(request)).stdout)
    release_id=release['id'];verified=[]
    def upload(asset):
        print(json.dumps({'uploading':asset['name'],'bytes':asset['bytes']}),flush=True)
        remote={x['name']:x for x in api(f'repos/{REPO}/releases/{release_id}/assets?per_page=100')}
        if asset['name'] not in remote:
            gh('release','upload',tag,asset['path'],'--repo',REPO,timeout=1800)
            remote={x['name']:x for x in api(f'repos/{REPO}/releases/{release_id}/assets?per_page=100')}
        r=remote.get(asset['name'])
        if r is None or not valid(r,asset):raise RuntimeError('Remote size/SHA256 did not verify: '+asset['name'])
        return {'name':asset['name'],'bytes':r['size'],'sha256':asset['sha256'],'remote_digest':r['digest'],'asset_id':r['id'],'url':r['browser_download_url'],'verified':True}
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in as_completed([pool.submit(upload,x) for x in plan['assets']]):
            verified.append(result.result());print(json.dumps({'verified':len(verified),'total':len(plan['assets'])}),flush=True)
            (ROOT/'REMOTE_RECEIPT.json').write_text(json.dumps({'status':'uploading','scope':plan['scope'],'assets':verified},indent=2))
    release=json.loads(gh('api','--method','PATCH',f'repos/{REPO}/releases/{release_id}','-F','draft=false','-F','prerelease=true','-f','make_latest=false').stdout)
    final={x['name']:x for x in api(f'repos/{REPO}/releases/{release_id}/assets?per_page=100')}
    for x in plan['assets']:
        if x['name'] not in final or not valid(final[x['name']],x):raise RuntimeError('Final compact asset verification failed')
    for x in verified:x['url']=final[x['name']]['browser_download_url']
    receipt={'status':'complete_verified','scope':plan['scope'],'branch':plan['branch'],'commit':a.commit,
        'tag':tag,'release_id':release_id,'release_url':release['html_url'],'assets':verified,
        'original_mcap_uploaded':False,'new_video_uploaded':False,'verified_wall_time':time.time()}
    (ROOT/'REMOTE_RECEIPT.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2),flush=True)

if __name__=='__main__':main()
