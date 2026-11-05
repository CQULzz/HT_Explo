"""Stage the opt-in mapper scheduler in a known runtime without starting it."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import tempfile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def install(runtime, bundle=None, apply=False):
    runtime = Path(runtime).resolve(strict=True)
    bundle = Path(bundle or Path(__file__).parent)
    manifest = json.loads((bundle / 'mapper_execution_manifest.json').read_text())
    wrapper = runtime / 'mapper_strict.py'
    helper = runtime / 'mapper_execution.py'
    for path in (wrapper, helper):
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise RuntimeError('Refusing managed symlink or non-file: ' + str(path))
    original = wrapper.read_bytes()
    helper_before = helper.read_bytes() if helper.exists() else None
    helper_after = (bundle / 'mapper_execution.py').read_bytes()
    if sha(helper_after) != manifest['helper_sha256']:
        raise RuntimeError('Scheduler bundle hash mismatch')
    if helper_before is not None and helper_before != helper_after:
        raise RuntimeError('Unknown runtime helper; preserving local edits')
    digest = sha(original)
    if digest == manifest['before_sha256']:
        text = original.decode()
        for old, new in manifest['replacements']:
            if text.count(old) != 1:
                raise RuntimeError('Unexpected wrapper patch context')
            text = text.replace(old, new)
        candidate = text.encode()
    elif digest == manifest.get('upgrade_from_sha256'):
        text = original.decode()
        for old, new in manifest['upgrade_replacements']:
            if text.count(old) != 1:
                raise RuntimeError('Unexpected wrapper upgrade context')
            text = text.replace(old, new)
        candidate = text.encode()
    elif digest == manifest['after_sha256']:
        candidate = original
    else:
        raise RuntimeError('Unknown mapper wrapper hash; preserving local edits')
    if sha(candidate) != manifest['after_sha256']:
        raise RuntimeError('Candidate wrapper hash mismatch')
    changed = original != candidate or helper_before != helper_after
    if apply and changed:
        # Stage both payloads before touching the known originals. Roll back if
        # either atomic replacement fails; never overwrite unknown input bytes.
        staged = []
        try:
            for path, data in ((helper, helper_after), (wrapper, candidate)):
                with tempfile.NamedTemporaryFile(dir=runtime, delete=False) as stream:
                    stream.write(data)
                    staged.append((path, Path(stream.name)))
            for path, temporary in staged:
                os.chmod(temporary, path.stat().st_mode & 0o777 if path.exists() else 0o644)
                os.replace(temporary, path)
        except BaseException:
            wrapper.write_bytes(original)
            if helper_before is None:
                if helper.exists():
                    helper.unlink()
            else:
                helper.write_bytes(helper_before)
            raise
        finally:
            for _, temporary in staged:
                if temporary.exists():
                    temporary.unlink()
    return {'applied': bool(apply and changed), 'would_change': changed,
            'wrapper_sha256': sha(candidate), 'helper_sha256': sha(helper_after),
            'default_mode': 'multi', 'candidate_mode': 'single',
            'starts_processes': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    print(json.dumps(install(args.runtime, apply=args.apply), indent=2))
