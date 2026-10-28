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


def expected_states(repository, bundle, staging):
    base = json.loads((bundle / 'manifest.json').read_text())['base_commit']
    candidate = json.loads((bundle / 'deterministic_manifest.json').read_text())
    if candidate['upstream_base'] != base:
        raise RuntimeError('Patch manifests name different upstream bases')
    patches = [bundle / 'cupy_ht_mapping.patch', bundle / 'deterministic_fusion.patch']
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
    for label, patch in zip(['base', 'stable'], patches, strict=True):
        run_git(staging, 'apply', '--check', str(patch))
        run_git(staging, 'apply', str(patch))
        states.append((label, {name: read_file(staging / name, staging) for name in managed}))
    for row in candidate['files']:
        name = safe_relative(row['file'])
        if name not in managed or digest(states[1][1][name]) != row['before_sha256']:
            raise RuntimeError(f'Unexpected intermediate patch bytes: {name}')
        if digest(states[2][1][name]) != row['after_sha256']:
            raise RuntimeError(f'Final candidate SHA256 mismatch: {name}')
    return managed, states


def generated_configs(workspace, repository, bundle):
    config = workspace / 'config'
    weights = repository / 'elevation_mapping_cupy/config/core/weights.dat'
    if not weights.is_file():
        raise RuntimeError(f'Missing independent mapper weights: {weights}')
    original = yaml.safe_load((bundle / 'trial_core.yaml').read_text())
    original['plugin_config_file'] = str(config / 'trial_plugins.yaml')
    legacy = dict(original, weight_file='$(rospack find elevation_mapping_cupy)/config/core/weights.dat')
    core = dict(original, weight_file=str(weights), enable_deterministic_fusion=True)
    encode = lambda value: yaml.safe_dump(value, sort_keys=False).encode()
    result = {config / 'trial_core.yaml': (encode(core), [encode(core), encode(legacy)])}
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


def install(workspace, bundle, *, build=False):
    workspace = Path(workspace).expanduser().resolve()
    repository = workspace / 'src/elevation_mapping_cupy_2204'
    bundle = Path(bundle).resolve()
    if not (repository / '.git').exists():
        raise RuntimeError(f'Missing independent checkout: {repository}')
    if repository.is_symlink():
        raise RuntimeError(f'Refusing checkout symlink: {repository}')
    with tempfile.TemporaryDirectory(prefix='ht-mapper-preflight-') as temporary:
        managed, states = expected_states(repository, bundle, Path(temporary))
        current = {name: read_file(repository / name, repository) for name in managed}
        matching = [label for label, values in states if values == current]
        if not matching:
            raise RuntimeError('Unsupported edits or partially applied patches in managed mapper files; '
                               'no files were changed. Preserve your edits and reconcile them explicitly.')
        final = states[-1][1]
        planned = {repository / name: final[name] for name in managed if final[name] != current[name]}
        originals = {repository / name: value for name, value in current.items()}
        for target, (desired, allowed) in generated_configs(workspace, repository, bundle).items():
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
            'source_stage_after': 'stable', 'changed_files': [str(p.relative_to(workspace)) for p in planned],
            'verified_manifest_files': len(json.loads((bundle / 'deterministic_manifest.json').read_text())['files']),
            'built': build, 'weight_file': str(repository / 'elevation_mapping_cupy/config/core/weights.dat')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--build', action='store_true')
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parent / 'elevation_mapping_fixes'
    print(json.dumps(install(args.workspace, bundle, build=args.build), indent=2))


if __name__ == '__main__':
    main()
