from pathlib import Path
import hashlib, json, shutil, tarfile, os, re

out = Path('/mnt/d/HT-Execution-300s/github_publish_20261114')
repo = Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes')
stage = Path('/home/lzz/ht_github_publish_20261114/ht-execution-runtime-source-20261114')
stage.mkdir(parents=True, exist_ok=True)
excludes = {'.git', '__pycache__', '.pytest_cache', '.venv', 'venv', 'build', 'install', 'log', '.mypy_cache'}

def copy_tree(src, dst, skip=()):
    src, dst = Path(src), Path(dst)
    for root, dirs, files in os.walk(src, followlinks=False):
        rel = Path(root).relative_to(src)
        dirs[:] = sorted(d for d in dirs if d not in excludes and str(rel / d) not in skip)
        for name in sorted(files):
            p = Path(root) / name
            r = rel / name
            if str(r) in skip or name.endswith(('.pyc', '.pyo')):
                continue
            q = dst / r
            q.parent.mkdir(parents=True, exist_ok=True)
            if p.is_symlink():
                target = os.readlink(p)
                # Preserve relative library symlinks; record external links instead.
                if os.path.isabs(target):
                    q.with_name(q.name + '.external-symlink.txt').write_text(target + '\n')
                elif not q.exists() and not q.is_symlink():
                    q.symlink_to(target)
            else:
                shutil.copy2(p, q)

tested = Path('/home/lzz/HT_Explo_execution_20261113')
candidate = json.loads(Path('/home/lzz/ht_execution_300s_20261113/setup/CANDIDATE_SOURCE.json').read_text())
for name, sha in candidate['files'].items():
    assert hashlib.sha256((tested / name).read_bytes()).hexdigest() == sha, name
copy_tree(tested, stage / 'ht_project_tested')
shutil.copy2('/home/lzz/ht_execution_300s_20261113/setup/CANDIDATE_SOURCE.json', stage / 'TESTED_PROJECT_SOURCE.json')
copy_tree('/home/lzz/tare_native_20261110', stage / 'tare_native')
copy_tree('/home/lzz/cmu_sim_20261110', stage / 'cmu_sim', skip=('src/vehicle_simulator/mesh/campus', 'src/vehicle_simulator/mesh/indoor'))
copy_tree('/home/lzz/ht_execution_300s_20261113/mapper_source/elevation_mapping_cupy_2204', stage / 'elevation_mapping_cupy')
copy_tree('/home/lzz/pcd_test_20261110', stage / 'recorded_pcd_scene')

roots = ['ht_execution_300s_20261113', 'ht_repeat_20261114', 'ht_600s_20261114', 'ht_campus_pcd_20261114']
text_exts = {'.py', '.sh', '.yaml', '.yml', '.xml', '.json', '.world', '.sdf', '.rviz', '.patch'}
for name in roots:
    src = Path('/home/lzz') / name
    dst = stage / 'experiment_runtimes' / name
    dst.mkdir(parents=True, exist_ok=True)
    for p in src.iterdir():
        if p.is_file() and p.suffix in text_exts:
            shutil.copy2(p, dst / p.name)
    for sub in ['runtime', 'config', 'scene_assets', 'original_tare_source']:
        if (src / sub).is_dir():
            copy_tree(src / sub, dst / sub)
    for p in (src / 'setup').glob('*'):
        if p.is_file() and p.suffix in text_exts:
            (dst / 'setup').mkdir(exist_ok=True)
            shutil.copy2(p, dst / 'setup' / p.name)

helper = stage / 'windows_setup_and_render_helpers'
helper.mkdir(exist_ok=True)
for p in Path('/mnt/d/HT-Execution-300s/setup').iterdir():
    if p.is_file() and p.suffix in {'.py', '.sh'}:
        shutil.copy2(p, helper / p.name)
copy_tree('/mnt/d/HT-Execution-300s/campus_pcd_videos_20261114/tools', stage / 'case_video_tools')

readme = '''# HT execution runtime source snapshot — 2026-11-14

This bundle complements the full HT_Explo Git repository. It preserves the exact
tested 176-file project snapshot, external CMU/TARE/mapper source trees (with
licenses), experiment launch/configuration/analysis helpers, video tools, and the
recovered recorded-PCD scene. It is source and runtime input, not a complete OS
or prebuilt ROS/virtualenv backup.

Main repository: https://github.com/CQULzz/HT_Explo
Branch: fix/ht-execution-20261113
Tested navigation commit: 7957e72f8e8b921912d6064cfb02eac22c1d9ec3
CMU base: HongbiaoZ/autonomous_exploration_development_environment,
158e67b31b644ed1e8b06eb1d7f70e183cc62591
TARE base: CQULzz/tare-planner, b6760adb4280b379567c76f4e684ce628e28ef71
TARE contains the parameter-declaration compatibility patch and diagnostic-only
logging; no exploration completion/return-home algorithm fix is claimed.

Build/run reference: validation/execution_300s_20261113 and the later experiment
reports in the Git repository. Use Ubuntu 22.04, ROS Humble, Python 3.10,
PyTorch 2.8 CUDA 12.8 and CuPy 13.6. The scripts retain original absolute paths
under /home/lzz and /mnt/d; adapt those to your workspace. OR-tools shared
libraries are included with the TARE source and require the documented library
path. No credentials, virtualenv, build/install output, raw MCAP, or GPU wheels
are included.

The two large official CMU scene mesh directories (campus, indoor) are excluded
from cmu_sim. Obtain them using the upstream AEDE scene instructions; the campus
per-file SHA256 inventory is preserved in experiment_runtimes/
ht_campus_pcd_20261114/scene_assets/CAMPUS_MANIFEST.json. The recorded-PCD scene
is included. This is a simulation snapshot, not vehicle deployment approval.

PCD coverage interpretation: the user confirms its actual explorable region
was already covered. Software finish=false and subsequent HT score rejection
still leave task termination unresolved; they do not independently prove
insufficient physical coverage. The observed NaN waypoint defect is documented
and has not been fixed in the planner.
'''
(stage / 'README.md').write_text(readme)

files = []
for p in sorted(stage.rglob('*')):
    if p.is_symlink():
        files.append({'path': str(p.relative_to(stage)), 'symlink': os.readlink(p)})
    elif p.is_file():
        files.append({'path': str(p.relative_to(stage)), 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
manifest = {'schema': 1, 'tested_commit': candidate['commit'], 'tested_project_files_verified': len(candidate['files']), 'files': files}
(stage / 'SOURCE_MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
shutil.copy2(stage / 'SOURCE_MANIFEST.json', out / 'SOURCE_MANIFEST.json')
archive = out / 'ht-execution-runtime-source-20261114.tar.gz'
with tarfile.open(archive, 'w:gz', compresslevel=6) as tar:
    tar.add(stage, arcname=stage.name)

evidence = out / 'ht-execution-evidence-20261114.tar.gz'
cohorts = ['execution_20261113', 'execution_300s_20261113', 'repeats_20261114', 'execution_600s_20261114', 'rviz_video_20261114', 'campus_pcd_20261114']
with tarfile.open(evidence, 'w:gz', compresslevel=6) as tar:
    for name in cohorts:
        assert (repo / 'validation' / name).is_dir(), name
        tar.add(repo / 'validation' / name, arcname='validation/' + name)

# Reopen and verify every source regular file and symlink from archived bytes.
with tarfile.open(archive, 'r:gz') as tar:
    for entry in files:
        name = stage.name + '/' + entry['path']
        member = tar.getmember(name)
        if 'symlink' in entry:
            assert member.issym() and member.linkname == entry['symlink'], name
        else:
            data = tar.extractfile(member).read()
            assert len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256'], name

for p in (archive, evidence):
    print(json.dumps({'file': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}), flush=True)
print(json.dumps({'source_entries_verified': len(files), 'tested_project_files_verified': len(candidate['files'])}), flush=True)
