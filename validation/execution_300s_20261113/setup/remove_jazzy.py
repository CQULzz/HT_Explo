import subprocess,json
from pathlib import Path
out=Path('/mnt/d/HT-Execution-300s/setup/jazzy_removal')
out.mkdir(exist_ok=True)
raw=subprocess.check_output(['dpkg-query','-W','-f=${binary:Package}\t${db:Status-Status}\n'],text=True)
packages=[line.split('\t')[0] for line in raw.splitlines() if line.startswith('ros-jazzy-') and line.endswith('\tinstalled')]
(out/'packages.json').write_text(json.dumps(packages,indent=2))
assert packages and all(p.startswith('ros-jazzy-') for p in packages)
result=subprocess.run(['apt-get','--simulate','purge',*packages],capture_output=True,text=True)
(out/'dry_run.log').write_text(result.stdout+result.stderr)
result.check_returncode()
removed=[line.split()[1] for line in result.stdout.splitlines() if line.startswith(('Remv ','Purg '))]
print(json.dumps({'jazzy_packages':len(packages),'removed_packages':len(removed),'additional_removals':[p for p in removed if not p.startswith('ros-jazzy-')]},indent=2))
assert all(p.startswith('ros-jazzy-') for p in removed)
with (out/'purge.log').open('w') as log:
    subprocess.run(['apt-get','-y','purge',*packages],stdout=log,stderr=subprocess.STDOUT,check=True)
print('Jazzy packages removed')
