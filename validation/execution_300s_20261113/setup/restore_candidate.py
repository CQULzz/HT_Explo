from pathlib import Path
import hashlib,json
src=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes')
dst=Path('/home/lzz/HT_Explo_execution_20261113')
receipt={}
for row in Path('/mnt/d/HT-Execution-300s/setup/candidate_index.txt').read_text(encoding='utf-8-sig').splitlines():
    metadata,name=row.split('\t',1)
    mode,expected,stage=metadata.split()
    data=(src/name).read_bytes()
    def digest(b):return hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
    if digest(data)!=expected:data=data.replace(b'\r\n',b'\n')
    assert digest(data)==expected,name
    target=dst/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    if mode=='100755':target.chmod(0o755)
    receipt[name]=hashlib.sha256(data).hexdigest()
Path('/home/lzz/ht_execution_300s_20261113/setup/CANDIDATE_SOURCE.json').write_text(json.dumps({'commit':'7957e72f8e8b921912d6064cfb02eac22c1d9ec3','files':receipt},indent=2))
print('Verified and restored',len(receipt),'Git blobs')
