import ast
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys

import pytest
import install_mapper_execution as installer


@pytest.fixture
def fixture(tmp_path):
    runtime = tmp_path / 'runtime'; runtime.mkdir()
    bundle = tmp_path / 'bundle'; bundle.mkdir()
    before = b'original wrapper\n'; after = b'candidate wrapper\n'; helper = b'known helper\n'
    manifest = {'before_sha256': installer.sha(before), 'after_sha256': installer.sha(after),
                'helper_sha256': installer.sha(helper),
                'replacements': [['original wrapper', 'candidate wrapper']]}
    (runtime / 'mapper_strict.py').write_bytes(before)
    (bundle / 'mapper_execution.py').write_bytes(helper)
    (bundle / 'mapper_execution_manifest.json').write_text(json.dumps(manifest))
    return runtime, bundle, before, after, helper


def test_dry_run_then_apply_then_idempotent(fixture):
    runtime, bundle, before, after, helper = fixture
    assert installer.install(runtime, bundle)['would_change']
    assert (runtime / 'mapper_strict.py').read_bytes() == before
    assert not (runtime / 'mapper_execution.py').exists()
    assert installer.install(runtime, bundle, apply=True)['applied']
    assert (runtime / 'mapper_strict.py').read_bytes() == after
    assert (runtime / 'mapper_execution.py').read_bytes() == helper
    mtime = (runtime / 'mapper_strict.py').stat().st_mtime_ns
    assert not installer.install(runtime, bundle, apply=True)['applied']
    assert (runtime / 'mapper_strict.py').stat().st_mtime_ns == mtime


@pytest.mark.parametrize('which', ['wrapper', 'helper', 'symlink'])
def test_unknown_edits_and_links_are_preserved(fixture, which):
    runtime, bundle, before, _, _ = fixture
    wrapper = runtime / 'mapper_strict.py'; helper = runtime / 'mapper_execution.py'
    if which == 'wrapper':
        wrapper.write_bytes(b'user modification')
    elif which == 'helper':
        helper.write_bytes(b'user helper')
    else:
        helper.symlink_to(wrapper)
    snapshots = {p: p.read_bytes() for p in [wrapper, helper] if p.exists()}
    with pytest.raises(RuntimeError):
        installer.install(runtime, bundle, apply=True)
    assert all(p.read_bytes() == content for p, content in snapshots.items())


def test_failed_second_replace_restores_both_originals(fixture, monkeypatch):
    runtime, bundle, before, _, _ = fixture
    real = os.replace
    def fail_wrapper(source, target):
        if Path(target).name == 'mapper_strict.py':
            raise OSError('injected replacement failure')
        return real(source, target)
    monkeypatch.setattr(installer.os, 'replace', fail_wrapper)
    with pytest.raises(OSError):
        installer.install(runtime, bundle, apply=True)
    assert (runtime / 'mapper_strict.py').read_bytes() == before
    assert not (runtime / 'mapper_execution.py').exists()
    assert sorted(p.name for p in runtime.iterdir()) == ['mapper_strict.py']


def test_actual_patch_preserves_all_map_operations():
    baseline = os.environ.get('MAPPER_TEST_BASELINE')
    candidate = os.environ.get('MAPPER_TEST_WRAPPER')
    if not baseline or not candidate:
        pytest.skip('Provide exact original and staged runtime paths')
    def methods(path):
        tree = ast.parse(Path(path).read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'ElevationMappingNode')
        return {n.name: ast.dump(n, include_attributes=False) for n in cls.body
                if isinstance(n, ast.FunctionDef) and n.name != '__init__'}
    assert methods(baseline) == methods(candidate)


def test_runner_rejects_unverified_candidate_before_any_child(tmp_path, monkeypatch):
    runner = Path(__file__).with_name('run_sim.py')
    repo = runner.parents[2]
    output = tmp_path / 'output'
    monkeypatch.setattr(sys, 'argv', [str(runner), '--label', 'must_not_run',
        '--project', str(repo), '--runtime', str(tmp_path), '--output-root', str(output),
        '--mapper-executor', 'single'])
    def forbidden(*args, **kwargs):
        raise AssertionError('No child process may start in this test')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    with pytest.raises(RuntimeError, match='hash-verified'):
        runpy.run_path(str(runner), run_name='__main__')
    assert not output.exists()


def test_known_previous_scheduler_upgrade_then_idempotent(fixture):
    runtime,bundle,_,after,_=fixture
    old=b'known previous scheduler\n'
    (runtime/'mapper_strict.py').write_bytes(old)
    path=bundle/'mapper_execution_manifest.json'
    manifest=json.loads(path.read_text())
    manifest.update(upgrade_from_sha256=installer.sha(old),
        upgrade_replacements=[['known previous scheduler','candidate wrapper']])
    path.write_text(json.dumps(manifest))
    assert installer.install(runtime,bundle,apply=True)['applied']
    assert (runtime/'mapper_strict.py').read_bytes()==after
    assert not installer.install(runtime,bundle,apply=True)['applied']
