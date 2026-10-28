"""CPU-only installer transactions on a minimal, immutable upstream fixture.

The five fixture files are actual `git show 88f4c0...:path` bytes. Tests commit
those files into a fresh minimal repository and adjust only the copied bundle's
base-commit metadata to that fixture commit. No real checkout, ROS or GPU runs.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tarfile

import pytest
import yaml

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('elevation_fix_installer', HERE / 'install_elevation_fixes.py')
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def git(repository, *args):
    return subprocess.check_output(['git', *args], cwd=repository).decode().strip()


@pytest.fixture
def workspace(tmp_path):
    work = tmp_path / 'independent workspace'
    repository = work / 'src/elevation_mapping_cupy_2204'
    repository.mkdir(parents=True)
    with tarfile.open(HERE / 'testdata/elevation_upstream_88f4c0.tar.gz') as archive:
        for member in archive.getmembers():
            assert member.isfile() and '..' not in Path(member.name).parts
            target = repository / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
    source = json.loads((repository / 'FIXTURE_SOURCE.json').read_text())
    assert source['commit'] == '88f4c0c2eb3542faeb7bd8fa9df2f18bd25eed91'
    for row in source['files']:
        assert hashlib.sha256((repository / row['path']).read_bytes()).hexdigest() == row['sha256']
    git(repository, 'init', '-q')
    git(repository, 'add', '.')
    git(repository, '-c', 'user.name=Installer fixture', '-c', 'user.email=fixture@local',
        'commit', '-qm', 'Isolated minimal fixture')
    base = git(repository, 'rev-parse', 'HEAD')
    bundle = tmp_path / 'bundle'
    shutil.copytree(HERE / 'elevation_mapping_fixes', bundle)
    for name, key in [('manifest.json', 'base_commit'), ('deterministic_manifest.json', 'upstream_base')]:
        p = bundle / name
        data = json.loads(p.read_text())
        data[key] = base
        p.write_text(json.dumps(data))
    return work, repository, bundle


def stable_hashes(repository, bundle):
    for row in json.loads((bundle / 'deterministic_manifest.json').read_text())['files']:
        assert hashlib.sha256((repository / row['file']).read_bytes()).hexdigest() == row['after_sha256']


def contents(work):
    return {str(path.relative_to(work)): path.read_bytes()
            for path in work.rglob('*') if path.is_file() and '.git' not in path.parts}


def test_clean_upstream_installs_both_stages_with_ros2_weight_path(workspace):
    work, repository, bundle = workspace
    keep = repository / 'unmanaged-user-data.txt'
    keep.write_text('Preserve unrelated edits\n')
    result = installer.install(work, bundle)
    assert result['source_stage_before'] == 'upstream'
    assert result['source_stage_after'] == 'stable'
    assert not result['built']
    assert keep.read_text() == 'Preserve unrelated edits\n'
    stable_hashes(repository, bundle)
    core = yaml.safe_load((work / 'config/trial_core.yaml').read_text())
    assert core['weight_file'] == str(repository / 'elevation_mapping_cupy/config/core/weights.dat')
    assert Path(core['weight_file']).is_file()
    assert '$(' not in core['weight_file']
    assert core['enable_deterministic_fusion'] is True


def test_base_patched_checkout_receives_only_stable_stage(workspace):
    work, repository, bundle = workspace
    git(repository, 'apply', str(bundle / 'cupy_ht_mapping.patch'))
    result = installer.install(work, bundle)
    assert result['source_stage_before'] == 'base'
    stable_hashes(repository, bundle)


def test_already_stable_install_is_idempotent_and_preserves_mtimes(workspace):
    work, repository, bundle = workspace
    installer.install(work, bundle)
    before = contents(work)
    times = {str(p): p.stat().st_mtime_ns for p in work.rglob('*')
             if p.is_file() and '.git' not in p.parts}
    result = installer.install(work, bundle)
    assert result['source_stage_before'] == 'stable'
    assert result['changed_files'] == []
    assert contents(work) == before
    assert times == {str(p): p.stat().st_mtime_ns for p in work.rglob('*')
                     if p.is_file() and '.git' not in p.parts}


@pytest.mark.parametrize('stage', ['upstream', 'base', 'stable'])
def test_unsupported_managed_edit_fails_without_modifying_other_files(workspace, stage):
    work, repository, bundle = workspace
    if stage in ['base', 'stable']:
        git(repository, 'apply', str(bundle / 'cupy_ht_mapping.patch'))
    if stage == 'stable':
        git(repository, 'apply', str(bundle / 'deterministic_fusion.patch'))
    target = repository / 'elevation_mapping_cupy/script/elevation_mapping_cupy/elevation_mapping_ros.py'
    with target.open('ab') as stream:
        stream.write(b'\n# User modification outside patch hunks\n')
    before = contents(work)
    with pytest.raises(RuntimeError, match='Unsupported edits'):
        installer.install(work, bundle)
    assert contents(work) == before
    assert not (work / 'config').exists()


def test_bad_final_manifest_fails_before_applying_base_stage(workspace):
    work, repository, bundle = workspace
    p = bundle / 'deterministic_manifest.json'
    manifest = json.loads(p.read_text())
    manifest['files'][0]['after_sha256'] = '0' * 64
    p.write_text(json.dumps(manifest))
    before = contents(work)
    with pytest.raises(RuntimeError, match='Final candidate SHA256 mismatch'):
        installer.install(work, bundle)
    assert contents(work) == before


def test_unknown_generated_config_is_preserved_and_source_remains_upstream(workspace):
    work, repository, bundle = workspace
    config = work / 'config'
    config.mkdir()
    (config / 'trial_core.yaml').write_text('resolution: 0.123456\n')
    before = contents(work)
    with pytest.raises(RuntimeError, match='Unsupported edits in generated config'):
        installer.install(work, bundle)
    assert contents(work) == before


def test_known_old_rospack_config_migrates_to_independent_ros2_weights(workspace):
    work, repository, bundle = workspace
    config = work / 'config'
    config.mkdir()
    old = yaml.safe_load((bundle / 'trial_core.yaml').read_text())
    old['weight_file'] = '$(rospack find elevation_mapping_cupy)/config/core/weights.dat'
    old['plugin_config_file'] = str(config / 'trial_plugins.yaml')
    (config / 'trial_core.yaml').write_text(yaml.safe_dump(old, sort_keys=False))
    installer.install(work, bundle)
    new = yaml.safe_load((config / 'trial_core.yaml').read_text())
    assert new['weight_file'] == str(repository / 'elevation_mapping_cupy/config/core/weights.dat')
    assert new['enable_deterministic_fusion'] is True


def test_bundle_inside_ht_git_subdirectory_enumerates_every_mapper_path(workspace, tmp_path):
    work, repository, bundle = workspace
    # This is the ordinary installation layout. Running git apply --numstat
    # from HT/tools/elevation_mapping_fixes silently filters out CuPy paths.
    ht_checkout = tmp_path / 'HT checkout'
    ht_checkout.mkdir()
    git(ht_checkout, 'init', '-q')
    nested_bundle = ht_checkout / 'tools/elevation_mapping_fixes'
    shutil.copytree(bundle, nested_bundle)
    assert len(installer.patch_paths(nested_bundle / 'cupy_ht_mapping.patch')) == 4
    assert len(installer.patch_paths(nested_bundle / 'deterministic_fusion.patch')) == 4
    result = installer.install(work, nested_bundle)
    assert result['source_stage_before'] == 'upstream'
    stable_hashes(repository, nested_bundle)
