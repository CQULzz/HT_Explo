#!/usr/bin/env python3
"""Upload an immutable completed HT suite as GitHub Release assets (never Git blobs)."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

REPO = 'CQULzz/HT_Explo'


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def gh(*args):
    return subprocess.check_output(['gh', *args, *(['--repo', REPO] if args[0] != 'api' else [])], text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--notes', type=Path, required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--recording-issues-note',type=Path,
                        help='Publish a full600s capture with cleanup exceptions, retaining failed status; requires archived issue JSON')
    args = parser.parse_args()
    suite, archive = args.suite.resolve(), args.archive.resolve()
    state = json.loads((suite / 'suite.json').read_text())
    allowed_states=['COMPLETED']+(['COMPLETED_WITH_ISSUES'] if args.recording_issues_note else [])
    if state['state'] not in allowed_states or state['duration_s'] < 600:
        raise ValueError('Only a completed >=600s suite is eligible; retain partial runs separately.')
    if args.receipt.exists():
        raise FileExistsError('Do not overwrite a publication receipt.')
    tracked = json.loads((archive / 'files_sha256.json').read_text())
    for name, expected in tracked.items():
        if sha256(archive / name) != expected:
            raise ValueError('Archive checksum mismatch: ' + name)
    validation_issues={}
    if args.recording_issues_note:
        issue_path=args.recording_issues_note.resolve()
        if not issue_path.is_relative_to(archive) or str(issue_path.relative_to(archive)) not in tracked:
            raise ValueError('Recording issue note must be inside the checksum-verified archive.')
        issue_note=json.loads(issue_path.read_text())
    for run in state['runs']:
        trial = suite / run['scenario']
        validation = json.loads((trial / 'suite_validation.json').read_text())
        failed=[k for k,v in validation['checks'].items() if not v]
        permitted_issue=args.recording_issues_note and run['state']=='RECORDED_WITH_ISSUES' and set(failed)=={'no_child_or_cleanup_exception'}
        if not permitted_issue and (run['state'] != 'RECORDED' or failed):
            raise ValueError('Collection validation failed: ' + run['scenario'])
        if failed:validation_issues[run['scenario']]=dict(failed_checks=failed,lifecycle_errors=validation['lifecycle_errors'])
        if json.loads((trial / 'manifest.json').read_text())['git_head'] != state['git_head']:
            raise ValueError('Suite contains inconsistent candidate commits.')
    candidate = state['git_head']
    local_tag = subprocess.check_output(['git', 'rev-parse', args.tag + '^{commit}'], text=True).strip()
    if local_tag != candidate:
        raise ValueError('Tag must identify the exact measured candidate.')
    print(json.dumps({'candidate': candidate, 'scenarios': [r['scenario'] for r in state['runs']],
                      'raw_bytes': sum(p.stat().st_size for p in suite.rglob('*') if p.is_file()),
                      'source': str(suite), 'archive': str(archive)}, indent=2), flush=True)
    if args.dry_run:
        return
    # A remote immutable tag is required. Never create/move tags implicitly.
    remote = gh('api', 'repos/' + REPO + '/git/ref/tags/' + args.tag)
    obj = json.loads(remote)['object']
    while obj['type'] == 'tag':
        obj = json.loads(gh('api', 'repos/' + REPO + '/git/tags/' + obj['sha']))['object']
    if obj['sha'] != candidate or obj['type'] != 'commit':
        raise ValueError('Remote tag mismatch.')
    releases = json.loads(gh('release', 'list', '--limit', '100', '--json', 'tagName'))
    if not any(r['tagName'] == args.tag for r in releases):
        gh('release', 'create', args.tag, '--verify-tag', '--prerelease',
           '--title', args.title, '--notes-file', str(args.notes))
    else:
        gh('release', 'edit', args.tag, '--title', args.title, '--notes-file', str(args.notes))
    # Temporary files are removed only after all verified uploads succeed. Raw sources remain.
    temp = Path(tempfile.mkdtemp(prefix='ht-release-'))
    print('Packaging in ' + str(temp), flush=True)
    assets = []
    for label, directory in [('raw', suite), ('results', archive)]:
        path = temp / (args.tag + '-' + label + '.tar')
        files = sorted(p for p in directory.rglob('*') if p.is_file())
        entries = []
        with tarfile.open(path, 'w') as output:
            for item in files:
                if item.is_symlink():
                    raise ValueError('Refuse symlink in evidence: ' + str(item))
                entries.append({'path': str(item.relative_to(directory)),
                                'bytes': item.stat().st_size, 'sha256': sha256(item)})
                output.add(item, arcname=str(Path(directory.name)/item.relative_to(directory)), recursive=False)
        # Verify archive content bytes rather than trusting packaging alone.
        with tarfile.open(path, 'r') as packed:
            for entry, member in zip(entries, packed.getmembers(), strict=True):
                digest = hashlib.sha256()
                with packed.extractfile(member) as stream:
                    for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b''):
                        digest.update(chunk)
                if digest.hexdigest() != entry['sha256']:
                    raise ValueError('Packaged file mismatch: ' + entry['path'])
        inventory = temp / (args.tag + '-' + label + '-files.json')
        inventory.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + '\n')
        assets += [path, inventory]
    for run in state['runs']:
        video = temp / (args.tag + '-' + run['scenario'] + '.mp4')
        # Hardlink keeps the upload independent of source names without duplicating video bytes.
        video.hardlink_to(archive / run['scenario'] / 'camera_h264.mp4')
        assets.append(video)
    # Split only the temporary transport archive when the GitHub per-asset limit is approached.
    transport = []
    for path in assets:
        if path.stat().st_size <= 1_900_000_000:
            transport.append(path)
        else:
            with path.open('rb') as stream:
                i = 0
                while chunk := stream.read(512 * 1024 * 1024):
                    part = path.with_name(path.name + f'.part{i:03}')
                    part.write_bytes(chunk)
                    transport.append(part)
                    i += 1
            path.unlink()
    receipt = {'tag': args.tag, 'tested_commit': candidate, 'raw_suite': str(suite),
               'result_archive': str(archive), 'release': f'https://github.com/{REPO}/releases/tag/{args.tag}',
               'recording_scope': 'Full published HT/control/odom/status; source-second laser samples; periodic map snapshots, not all raw laser/CuPy frames.',
               'assets': [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha256(p)} for p in transport]}
    if validation_issues:
        receipt.update(publication_status='RECORDED_WITH_ISSUES',validation_issues=validation_issues,
                       recording_issues_note=issue_note)
    proof = temp / (args.tag + '-SHA256.json')
    proof.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    transport.append(proof)
    existing = {a['name']: a for a in json.loads(gh('api', 'repos/' + REPO + '/releases/tags/' + args.tag))['assets']}
    for path in transport:
        if path.name in existing:
            asset = existing[path.name]
            # Never clobber existing assets, and never equate matching size with integrity.
            remote_digest = gh('api', 'repos/' + REPO + '/releases/assets/' + str(asset['id']))
            remote_digest = json.loads(remote_digest).get('digest')
            if asset['size'] != path.stat().st_size or remote_digest != 'sha256:' + sha256(path):
                raise ValueError('Existing asset differs or has no verified digest: ' + path.name)
        else:
            print('Uploading ' + path.name, flush=True)
            gh('release', 'upload', args.tag, str(path))
    remote_assets = json.loads(gh('api', 'repos/' + REPO + '/releases/tags/' + args.tag))['assets']
    for path in transport:
        matched = next(a for a in remote_assets if a['name'] == path.name)
        detail = json.loads(gh('api', 'repos/' + REPO + '/releases/assets/' + str(matched['id'])))
        if matched['size'] != path.stat().st_size or detail.get('digest') != 'sha256:' + sha256(path):
            raise ValueError('Remote size/digest verification failed: ' + path.name)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    for path in temp.iterdir():
        path.unlink()
    temp.rmdir()
    print('Verified: ' + receipt['release'], flush=True)


if __name__ == '__main__':
    main()
