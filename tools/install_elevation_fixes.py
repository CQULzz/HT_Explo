#!/usr/bin/env python3
"""Install verified CuPy patches into an independent workspace, after preflight."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tempfile

import yaml


def digest(data):
    return None if data is None else hashlib.sha256(data).hexdigest()


def run_git(repository, *args, check=True):
    result = subprocess.run(['git', *args], cwd=repository, capture_output=True, check=False)
    if check and result.returncode:
        raise RuntimeError(result.stderr.decode(errors='replace').strip())
    return result


def safe_relative(value):
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise RuntimeError(f'Unsupported managed path: {value}')
    return str(path)


def patch_paths(patch):
    # git apply restricts reported/applied paths to the current Git subdir.
    # The bundle normally lives under HT/tools, outside the patch's CuPy paths;
    # enumerating from there can misleadingly succeed with no reported files.
    with tempfile.TemporaryDirectory(prefix='ht-patch-paths-') as neutral:
        rows = run_git(Path(neutral), 'apply', '--numstat', '-z', str(patch)).stdout.split(b'\0')
    paths = {safe_relative(row.split(b'\t', 2)[2].decode()) for row in rows if row}
    if not paths:
        raise RuntimeError(f'Patch has no managed paths: {patch}')
    return paths


def read_file(path, boundary):
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents
                                if parent != boundary and boundary in parent.parents):
        raise RuntimeError(f'Refusing managed symlink: {path}')
    if not path.exists():
        return None
    if not path.is_file():
        raise RuntimeError(f'Managed path is not a regular file: {path}')
    return path.read_bytes()


def expected_states(repository, bundle, staging, *, surface_registration=False):
    base = json.loads((bundle / 'manifest.json').read_text())['base_commit']
    candidate = json.loads((bundle / 'deterministic_manifest.json').read_text())
    if candidate['upstream_base'] != base:
        raise RuntimeError('Patch manifests name different upstream bases')
    patches = [bundle / 'cupy_ht_mapping.patch', bundle / 'deterministic_fusion.patch']
    labels = ['base', 'stable']
    if surface_registration:
        patches.append(bundle / 'surface_registration.patch')
        labels.append('surface_registered')
    managed = sorted(set().union(*(patch_paths(patch) for patch in patches)))
    if not managed:
        raise RuntimeError('Patch bundle has no managed mapper files')
    run_git(repository, 'cat-file', '-e', base + '^{commit}')
    clean = {}
    for name in managed:
        result = run_git(repository, 'show', base + ':' + name, check=False)
        clean[name] = result.stdout if not result.returncode else None
        if clean[name] is not None:
            target = staging / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(clean[name])
    states = [('upstream', clean)]
    for label, patch in zip(labels, patches, strict=True):
        run_git(staging, 'apply', '--check', str(patch))
        run_git(staging, 'apply', str(patch))
        states.append((label, {name: read_file(staging / name, staging) for name in managed}))
    for row in candidate['files']:
        name = safe_relative(row['file'])
        if name not in managed or digest(states[1][1][name]) != row['before_sha256']:
            raise RuntimeError(f'Unexpected intermediate patch bytes: {name}')
        if digest(states[2][1][name]) != row['after_sha256']:
            raise RuntimeError(f'Final candidate SHA256 mismatch: {name}')
    if surface_registration:
        surface = json.loads((bundle / 'surface_registration_manifest.json').read_text())
        if surface['upstream_base'] != base:
            raise RuntimeError('Surface registration manifest names a different upstream base')
        for row in surface['files']:
            name = safe_relative(row['file'])
            if name not in managed or digest(states[2][1][name]) != row['before_sha256']:
                raise RuntimeError(f'Unexpected stable-stage bytes: {name}')
            if digest(states[3][1][name]) != row['after_sha256']:
                raise RuntimeError(f'Final surface registration SHA256 mismatch: {name}')
    return managed, states


def generated_configs(workspace, repository, bundle, *, surface_registration=False):
    config = workspace / 'config'
    weights = repository / 'elevation_mapping_cupy/config/core/weights.dat'
    if not weights.is_file():
        raise RuntimeError(f'Missing independent mapper weights: {weights}')
    original = yaml.safe_load((bundle / 'trial_core.yaml').read_text())
    original['plugin_config_file'] = str(config / 'trial_plugins.yaml')
    legacy = dict(original, weight_file='$(rospack find elevation_mapping_cupy)/config/core/weights.dat')
    core = dict(original, weight_file=str(weights), enable_deterministic_fusion=True)
    stable_core = dict(core)
    if surface_registration:
        core['enable_surface_registration'] = True
    encode = lambda value: yaml.safe_dump(value, sort_keys=False).encode()
    result = {config / 'trial_core.yaml': (encode(core), [encode(core), encode(stable_core), encode(legacy)])}
    for name in ['trial_setup.yaml', 'trial_plugins.yaml']:
        data = (bundle / name).read_bytes()
        result[config / name] = (data, [data])
    return result


def atomic_write(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix='.' + path.name + '.ht-', dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(handle, 'wb') as stream:
            stream.write(data)
        temporary.chmod(mode)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def install_publication_performance(workspace, bundle, *, build=False):
    """Patch only the known ROS wrapper; preserve all mapper/config choices.

    This independent opt-in deliberately does not enable surface registration
    or regenerate trial configs just because that candidate is installed.
    """
    workspace=Path(workspace).expanduser().resolve()
    repository=workspace/'src/elevation_mapping_cupy_2204'
    bundle=Path(bundle).resolve()
    if not (repository/'.git').exists() or repository.is_symlink():
        raise RuntimeError(f'Missing independent checkout: {repository}')
    manifest=json.loads((bundle/'publication_performance_manifest.json').read_text())
    run_git(repository,'cat-file','-e',manifest['upstream_base']+'^{commit}')
    patch=bundle/'publication_performance.patch'
    rows=manifest['files']
    if len(rows)!=1:raise RuntimeError('Publication patch must manage exactly the ROS wrapper')
    name=safe_relative(rows[0]['file'])
    if patch_paths(patch)!={name}:raise RuntimeError('Publication patch/manifest paths disagree')
    target=repository/name;before=read_file(target,repository)
    current=digest(before);row=rows[0]
    if current not in (row['before_sha256'],row['after_sha256']):
        raise RuntimeError('Unsupported edits in mapper ROS wrapper; no files were changed')
    with tempfile.TemporaryDirectory(prefix='ht-publish-preflight-') as temporary:
        staging=Path(temporary);p=staging/name;p.parent.mkdir(parents=True);p.write_bytes(before)
        if current==row['after_sha256']:
            run_git(staging,'apply','--reverse','--check',str(patch))
            run_git(staging,'apply','--reverse',str(patch))
        if digest(p.read_bytes())!=row['before_sha256']:
            raise RuntimeError('Publication preimage SHA256 mismatch')
        run_git(staging,'apply','--check',str(patch));run_git(staging,'apply',str(patch))
        desired=p.read_bytes()
        if digest(desired)!=row['after_sha256']:
            raise RuntimeError('Publication candidate SHA256 mismatch')
    if read_file(target,repository)!=before:
        raise RuntimeError('Mapper ROS wrapper changed during preflight')
    changed=[]
    if before!=desired:
        mode=target.stat().st_mode&0o777
        try:
            atomic_write(target,desired,mode)
            if read_file(target,repository)!=desired:raise RuntimeError('Publication post-write check failed')
        except Exception:
            atomic_write(target,before,mode);raise
        changed=[str(target.relative_to(workspace))]
    if build:
        subprocess.run(['colcon','build','--packages-select','elevation_mapping_cupy'],cwd=workspace,check=True)
    return {'workspace':str(workspace),'source_stage_before':('publication_performance' if before==desired else 'publication_base'),
            'source_stage_after':'publication_performance','changed_files':changed,'built':build,
            'configs_and_fusion_sources_unchanged':True}


def install(workspace, bundle, *, build=False, surface_registration=False, publication_performance=False):
    if publication_performance:
        if surface_registration:
            raise RuntimeError('Install surface registration separately; publication-only installation preserves existing configs')
        return install_publication_performance(workspace,bundle,build=build)
    workspace = Path(workspace).expanduser().resolve()
    repository = workspace / 'src/elevation_mapping_cupy_2204'
    bundle = Path(bundle).resolve()
    if not (repository / '.git').exists():
        raise RuntimeError(f'Missing independent checkout: {repository}')
    if repository.is_symlink():
        raise RuntimeError(f'Refusing checkout symlink: {repository}')
    with tempfile.TemporaryDirectory(prefix='ht-mapper-preflight-') as temporary:
        managed, states = expected_states(repository, bundle, Path(temporary),
                                          surface_registration=surface_registration)
        current = {name: read_file(repository / name, repository) for name in managed}
        matching = [label for label, values in states if values == current]
        if not matching:
            raise RuntimeError('Unsupported edits or partially applied patches in managed mapper files; '
                               'no files were changed. Preserve your edits and reconcile them explicitly.')
        final = states[-1][1]
        planned = {repository / name: final[name] for name in managed if final[name] != current[name]}
        originals = {repository / name: value for name, value in current.items()}
        for target, (desired, allowed) in generated_configs(workspace, repository, bundle,
                                                           surface_registration=surface_registration).items():
            existing = read_file(target, workspace)
            if existing is not None and existing not in allowed:
                raise RuntimeError(f'Unsupported edits in generated config: {target}; no files were changed')
            originals[target] = existing
            if existing != desired:
                planned[target] = desired
        # Re-read all affected source/config files before the first mutation.
        for target, value in originals.items():
            if read_file(target, workspace) != value:
                raise RuntimeError(f'Managed file changed during preflight: {target}')
        modes = {target: target.stat().st_mode & 0o777 if target.exists() else 0o644 for target in planned}
        written = []
        try:
            for target, desired in planned.items():
                written.append(target)
                if desired is None:
                    target.unlink(missing_ok=True)
                else:
                    atomic_write(target, desired, modes[target])
            if any(read_file(repository / name, repository) != value for name, value in final.items()):
                raise RuntimeError('Post-install mapper bytes differ from staged candidate')
        except Exception:
            for target in reversed(written):
                if originals[target] is None:
                    target.unlink(missing_ok=True)
                else:
                    atomic_write(target, originals[target], modes[target])
            raise
    if build:
        subprocess.run(['colcon', 'build', '--packages-select', 'elevation_mapping_cupy'],
                       cwd=workspace, check=True)
    return {'workspace': str(workspace), 'source_stage_before': matching[0],
            'source_stage_after': states[-1][0], 'changed_files': [str(p.relative_to(workspace)) for p in planned],
            'verified_manifest_files': len(json.loads((bundle / 'deterministic_manifest.json').read_text())['files']),
            'built': build, 'weight_file': str(repository / 'elevation_mapping_cupy/config/core/weights.dat')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--surface-registration', action='store_true',
                        help='Install and explicitly enable the offline-tested Z/tilt registration candidate')
    parser.add_argument('--publication-performance',action='store_true',
                        help='Only skip unused publication; preserve installed fusion sources and configs')
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parent / 'elevation_mapping_fixes'
    print(json.dumps(install(args.workspace, bundle, build=args.build,
                             surface_registration=args.surface_registration,
                             publication_performance=args.publication_performance), indent=2))


if __name__ == '__main__':
    main()
