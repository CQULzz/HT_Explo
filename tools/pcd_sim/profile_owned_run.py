from pathlib import Path
import json,time,csv,subprocess,os
R=Path('/home/w_lzz/ht-iterations-20261105');out=R/'profile_repeat120_r05'
deadline=time.monotonic()+60
while time.monotonic()<deadline:
 try:
  rows=list(csv.DictReader((out/'metrics.csv').open()))
  if rows and float(rows[-1]['elapsed_sim'])>=20:break
 except (FileNotFoundError,ValueError,KeyError):pass
 time.sleep(1)
else:raise RuntimeError('Profiled trial did not become ready')
pids=json.loads((out/'pids.json').read_text());nav=pids['navigation'];mapper=pids['mapper']
def command(pid):return Path(f'/proc/{pid}/cmdline').read_bytes().split(b'\0')
def descendant(pid,ancestor):
 for _ in range(20):
  if pid==ancestor:return True
  try:pid=int(next(x.split()[1] for x in Path(f'/proc/{pid}/status').read_text().splitlines() if x.startswith('PPid:')))
  except (FileNotFoundError,StopIteration):return False
 return False
assert any(x==str(R/'runtime/mapper_strict.py').encode() for x in command(mapper))
ht=[]
for path in Path('/proc').iterdir():
 if not path.name.isdigit():continue
 try:
  args=command(int(path.name))
  if any(x.endswith(b'/install_real/tare_planner/lib/tare_planner/cupy_to_ht.py') for x in args) and descendant(int(path.name),nav):ht.append(int(path.name))
 except (FileNotFoundError,ProcessLookupError,PermissionError):pass
assert len(ht)==1,ht
metadata={'scope':'Read-only nonblocking Python GIL stack sampling on verified descendants of this isolated run; no locals captured. Profiling may perturb timing, not an unprofiled performance trial.','rate_hz':50,'duration_s':45,'targets':{'ht':ht[0],'mapper':mapper},'elapsed_sim_at_start':float(rows[-1]['elapsed_sim'])}
processes=[]
for label,pid in metadata['targets'].items():
 f=(out/f'profile_{label}.log').open('w');proc=subprocess.Popen([str(R/'venv/bin/py-spy'),'record','--pid',str(pid),'--format','raw','--threads','--gil','--nonblocking','--rate','50','--duration','45','--output',str(out/f'profile_{label}_gil.raw')],stdout=f,stderr=subprocess.STDOUT);processes.append((label,proc,f))
for label,proc,f in processes:metadata[label+'_exit']=proc.wait();f.close()
(out/'PROFILE_METADATA.json').write_text(json.dumps(metadata,indent=2))
for path in [out/'PROFILE_METADATA.json',*out.glob('profile_*')]:os.chown(path,1000,1000)
print(json.dumps(metadata,indent=2))
