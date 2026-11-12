"""Use the account-specific saved GitHub credential without writing its value."""
from pathlib import Path
import argparse,json,os,re,subprocess,sys
import gi
gi.require_version('Secret','1')
from gi.repository import Secret

def credential_environment():
    service=Secret.Service.get_sync(Secret.ServiceFlags.OPEN_SESSION|Secret.ServiceFlags.LOAD_COLLECTIONS,None)
    found=[]
    for collection in service.get_collections():
        collection.load_items_sync(None)
        for item in collection.get_items():
            if item.get_label()=='GitHub - https://api.github.com/CQULzz':found.append(item)
    if len(found)!=1 or found[0].get_locked():raise RuntimeError('Account-specific saved GitHub credential unavailable')
    found[0].load_secret_sync(None);token=found[0].get_secret().get_text()
    if not isinstance(token,str) or not re.fullmatch(r'(?:(?:gh[pousr]_|github_pat_)[A-Za-z0-9_]+|[a-fA-F0-9]{40})',token):
        raise RuntimeError('Unsupported saved GitHub credential format; value not displayed')
    env=os.environ.copy();env['GH_TOKEN']=token;env.pop('GH_DEBUG',None)
    for command,expected in [(['gh','api','user','--jq','.login'],'CQULzz'),
                             (['gh','api','repos/CQULzz/HT_Explo','--jq','.permissions.push'],'true')]:
        result=subprocess.run(command,env=env,capture_output=True,text=True,timeout=45)
        if result.returncode or result.stdout.strip()!=expected:raise RuntimeError('Saved GitHub identity/write-access validation failed; response omitted')
    return env

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--upload',action='store_true');a=parser.parse_args()
    env=credential_environment()
    record={'account':'CQULzz','repository':'CQULzz/HT_Explo','write_access_verified':True,
            'source':'account-specific unlocked system keyring','secret_written_to_file':False}
    Path('/home/lzz/ht_quality_github_20261112/AUTH_SOURCE.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)
    if a.upload:
        result=subprocess.run(['systemd-inhibit','--what=sleep:idle','--mode=block',
            '--who=GitHub experiment upload','--why=Finish requested experiment upload and verify remote checksums',
            sys.executable,str(Path(__file__).with_name('upload.py'))],env=env)
        raise SystemExit(result.returncode)

if __name__=='__main__':main()
