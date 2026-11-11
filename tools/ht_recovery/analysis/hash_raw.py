from pathlib import Path
import hashlib,json
ROOT=Path('/home/lzz/ht_recovery_20261111');records={}
for run in sorted((ROOT/'runs').iterdir()):
 for path in sorted((run/'bag').glob('*')):
  if not path.is_file():continue
  sha=hashlib.sha256()
  with path.open('rb') as f:
   for block in iter(lambda:f.read(8*1024*1024),b''):sha.update(block)
  records[str(path)]={'bytes':path.stat().st_size,'sha256':sha.hexdigest()}
(ROOT/'evidence/RAW_SHA256.json').write_text(json.dumps(records,indent=2));print('raw files',len(records),'bytes',sum(v['bytes'] for v in records.values()))
