from pathlib import Path
import argparse,json,hashlib,zipfile
p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();folder=a.trial/'current/inference_context';files=[];bad=[]
for f in sorted(folder.glob('*.npz')):
 try:
  with zipfile.ZipFile(f) as packed:
   failed=packed.testzip()
   if failed:raise ValueError('CRC mismatch: '+failed)
  files.append(dict(file=str(f),bytes=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
 except Exception as error:bad.append(dict(file=str(f),error=str(error)))
partials=[str(f) for f in sorted(folder.glob('*.partial'))];history=a.trial/'current/historical_elevation.npz';history_ok=False
try:
 with zipfile.ZipFile(history) as packed:history_ok=packed.testzip() is None
except Exception as error:bad.append(dict(file=str(history),error=str(error)))
result=dict(completed_npz_files=len(files),all_completed_npz_readable=bool(files) and not bad,history_snapshot_crc_passed=history_ok,damaged_files=bad,remaining_partial_files=partials,passed=bool(files) and not bad and not partials and history_ok,files=files,limitations='ZIP CRC and final-file completeness only; semantic map/model agreement is checked separately.')
a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
if not result['passed']:raise SystemExit(1)
