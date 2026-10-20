#!/usr/bin/env python3
"""Resumable, bounded-spool archival of legacy data; never changes experiments/tags."""
import argparse
import concurrent.futures
import datetime
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'presentations/scheduled_results'
OUT = ROOT / 'docs/experiments/legacy_archive'
REPO = 'CQULzz/HT_Explo'
PART = 512 * 1024 * 1024


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    os.replace(tmp, path)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4 * 1024 * 1024), b''):
            h.update(b)
    return h.hexdigest()


def gh(*args):
    error = None
    for attempt in range(4):
        try:
            return subprocess.check_output(['gh', *args], text=True, stderr=subprocess.PIPE)
        except subprocess.CalledProcessError as exc:
            error = exc
            print('GitHub retry:', exc.stderr.strip()[:500], flush=True)
            time.sleep(min(2 ** attempt, 8))
    raise error


def release(tag):
    result = json.loads(gh('api', f'repos/{REPO}/releases/tags/{tag}'))
    if len(result['assets']) >= 30:
        pages = json.loads(gh('api', '--paginate', '--slurp',
                              f'repos/{REPO}/releases/{result["id"]}/assets?per_page=100'))
        result['assets'] = [a for page in pages for a in page]
    return result


def inventory(source):
    entries = []
    for directory, dirs, files in os.walk(source, followlinks=False):
        for name in sorted(dirs + files):
            p = Path(directory) / name
            rel = str(p.relative_to(source))
            s = p.lstat()
            if p.is_symlink():
                # Portable links can only address the archived datasets, never external files.
                target = Path(os.path.normpath(p.parent / os.readlink(p)))
                if not target.is_relative_to(BASE):
                    raise ValueError('Link escapes experiment collection: ' + str(p))
                entries.append(dict(path=rel, kind='symlink', original_target=os.readlink(p),
                                    portable_target=os.path.relpath(target, p.parent)))
            elif p.is_file():
                expected = sha(p)
                after = p.stat()
                if (s.st_size, s.st_mtime_ns, s.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                    raise ValueError('Source changed during inventory: ' + str(p))
                entries.append(dict(path=rel, kind='file', bytes=s.st_size,
                                    sha256=expected, mode=s.st_mode & 0o777))
            elif p.is_dir():
                entries.append(dict(path=rel, kind='directory', mode=s.st_mode & 0o777))
            else:
                raise ValueError('Unsupported special file: ' + str(p))
    return sorted(entries, key=lambda e: e['path'])


class CheckedReader:
    def __init__(self, stream):
        self.stream, self.hash = stream, hashlib.sha256()
    def read(self, size):
        b = self.stream.read(size)
        self.hash.update(b)
        return b


def stream_parts(source, entries, temp, prefix, callback, part_bytes=PART):
    """Tar producer verifies source bytes while compressor/consumer apply backpressure.

    Only one transport part exists at a time. Compression and tar headers are
    deterministic, so already uploaded identical parts can be reused after restart.
    """
    errors = []
    proc = subprocess.Popen(['zstd', '-q', '-3', '-T1', '-c'], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    def produce():
        try:
            with tarfile.open(fileobj=proc.stdin, mode='w|', format=tarfile.PAX_FORMAT) as tar:
                for entry in entries:
                    p = source / entry['path']
                    info = tarfile.TarInfo(source.name + '/' + entry['path'])
                    info.uid = info.gid = info.mtime = 0
                    info.mode = entry.get('mode', 0o777)
                    if entry['kind'] == 'symlink':
                        if not p.is_symlink() or os.readlink(p) != entry['original_target']:
                            raise ValueError('Source symlink changed: ' + str(p))
                        info.type, info.linkname = tarfile.SYMTYPE, entry['portable_target']
                        tar.addfile(info)
                    elif entry['kind'] == 'directory':
                        info.type = tarfile.DIRTYPE
                        tar.addfile(info)
                    else:
                        before = p.stat()
                        if p.is_symlink() or before.st_size != entry['bytes']:
                            raise ValueError('Source type/size changed: ' + str(p))
                        info.size = entry['bytes']
                        with p.open('rb') as f:
                            checked = CheckedReader(f)
                            tar.addfile(info, checked)
                        after = p.stat()
                        if checked.hash.hexdigest() != entry['sha256'] or (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino):
                            raise ValueError('Source bytes changed: ' + str(p))
        except BaseException as exc:
            errors.append(exc)
        finally:
            proc.stdin.close()
    thread = threading.Thread(target=produce, daemon=True)
    thread.start()
    assets = []
    try:
        number = 0
        while True:
            part = temp / f'{prefix}.tar.zst.part{number:03d}'
            with part.open('wb') as output:
                remaining = part_bytes
                while remaining:
                    b = proc.stdout.read(min(4 * 1024 * 1024, remaining))
                    if not b:
                        break
                    output.write(b)
                    remaining -= len(b)
            if not part.stat().st_size:
                part.unlink()
                break
            assets.append(callback(part))
            part.unlink()  # Source remains; only the verified temporary transport part is removed.
            number += 1
        thread.join()
        code = proc.wait()
        if errors:
            raise errors[0]
        if code:
            raise RuntimeError('zstd failed: ' + proc.stderr.read().decode())
    finally:
        if proc.poll() is None:
            proc.kill()
        proc.stdout.close()
        proc.stderr.close()
    return assets


def matches(asset, expected):
    return (asset.get('state') == 'uploaded' and asset['size'] == expected['bytes']
            and asset.get('digest') == 'sha256:' + expected['sha256'])


def archive(record):
    source = (ROOT / record['source']).absolute()
    if source.parent != BASE or source.is_symlink() or not source.is_dir():
        raise ValueError('Unsafe/missing owned dataset: ' + str(source))
    tag = record['tag']
    # Phase association is explicitly separate from recorded tested commits.
    remote_ref = json.loads(gh('api', f'repos/{REPO}/git/ref/tags/{tag}'))['object']
    while remote_ref['type'] == 'tag':
        remote_ref = json.loads(gh('api', f'repos/{REPO}/git/tags/' + remote_ref['sha']))['object']
    if remote_ref['sha'] != record['stage_tag_commit']:
        raise ValueError('Phase tag differs from catalogue; do not move tags.')
    print('Inventory', source.name, flush=True)
    entries = inventory(source)
    contents = dict(dataset=source.name, entries=entries, provenance=record,
                    format='Concatenate parts in numeric order, zstd-decompress then tar-extract into a common root. Symlinks are relative; original link strings are in this inventory.')
    canonical = json.dumps(contents, sort_keys=True, ensure_ascii=False).encode()
    prefix = 'legacy-' + source.name + '-' + hashlib.sha256(canonical).hexdigest()[:12]
    local_inventory = OUT / 'inventories' / (source.name + '.json')
    receipt_path = OUT / 'receipts' / (source.name + '.json')
    remote = release(tag)
    existing = {a['name']: a for a in remote['assets']}
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if receipt['content_key'] != prefix:
            raise ValueError('Previously published dataset changed; preserve both versions explicitly.')
        if not all(a['name'] in existing and matches(existing[a['name']], a) for a in receipt['assets']):
            raise ValueError('Published receipt no longer matches remote assets')
        if sha(local_inventory) != receipt['inventory_sha256']:
            raise ValueError('Local inventory changed')
        print('Reverified', source.name, flush=True)
        return receipt
    write(local_inventory, contents)
    def upload(path):
        expected = dict(name=path.name, bytes=path.stat().st_size, sha256=sha(path))
        if path.name in existing:
            if not matches(existing[path.name], expected):
                raise ValueError('Refuse to overwrite differing asset: ' + path.name)
            print('Reusing', path.name, flush=True)
        else:
            print('Uploading', path.name, expected['bytes'], flush=True)
            # Retry must first inspect remote: a lost HTTP response may follow a successful upload.
            for attempt in range(4):
                current = {a['name']: a for a in release(tag)['assets']}
                if path.name in current:
                    if not matches(current[path.name], expected):
                        raise ValueError('Remote asset conflicts: ' + path.name)
                    break
                try:
                    subprocess.run(['gh', 'release', 'upload', tag, str(path), '--repo', REPO], check=True)
                except subprocess.CalledProcessError:
                    if attempt == 3:
                        raise
                    time.sleep(2 ** attempt)
            current = {a['name']: a for a in release(tag)['assets']}
            if path.name not in current or not matches(current[path.name], expected):
                raise ValueError('Upload not verified: ' + path.name)
            existing[path.name] = current[path.name]
        expected['url'] = existing[path.name]['browser_download_url']
        return expected
    with tempfile.TemporaryDirectory(prefix='ht-legacy-') as tmp:
        temp = Path(tmp)
        assets = stream_parts(source, entries, temp, prefix, upload)
        inv_asset = temp / (prefix + '-files.json')
        inv_asset.write_bytes(local_inventory.read_bytes())
        assets.append(upload(inv_asset))
        receipt = dict(schema=1, dataset=source.name, source=str(source), tag=tag,
                       stage=record['stage'], content_key=prefix,
                       association=record['association'], provenance=record['provenance'],
                       status='REMOTE_VERIFIED_ARCHIVE_NOT_NEW_EXPERIMENT',
                       release=f'https://github.com/{REPO}/releases/tag/{tag}',
                       inventory_sha256=sha(local_inventory), files=sum(e['kind']=='file' for e in entries),
                       file_bytes=sum(e.get('bytes', 0) for e in entries),
                       assets=assets)
        proof = temp / (prefix + '-verified.json')
        if proof.name in existing:
            # Resume even after a complete proof upload followed by a lost response.
            gh('release', 'download', tag, '--repo', REPO, '--pattern', proof.name,
               '--output', str(proof))
            prior=json.loads(proof.read_text())
            comparable=dict(prior)
            comparable.pop('verified_at',None)  # Compatibility with the first archive receipts.
            if comparable != receipt:
                raise ValueError('Existing proof describes different complete content')
        else:
            write(proof, receipt)
        proof_asset = upload(proof)
        receipt['assets'].append(proof_asset)
        # Verify the complete set together, after all streaming checks succeeded.
        final = {a['name']: a for a in release(tag)['assets']}
        if not all(a['name'] in final and matches(final[a['name']], a) for a in receipt['assets']):
            raise ValueError('Final complete remote verification failed')
        receipt['verified_at']=datetime.datetime.now().astimezone().isoformat()
        write(receipt_path, receipt)
    print('VERIFIED', source.name, receipt['file_bytes'], flush=True)
    return receipt


def self_test():
    with tempfile.TemporaryDirectory() as tmp:
        temp = Path(tmp)
        source = temp / 'example'
        source.mkdir()
        (source/'empty').mkdir()
        (source/'data.bin').write_bytes(os.urandom(20000))
        (source/'alias').symlink_to('data.bin')
        entries = [dict(path='alias',kind='symlink',original_target='data.bin',portable_target='data.bin'),
                   dict(path='data.bin',kind='file',bytes=20000,sha256=sha(source/'data.bin'),mode=0o644),
                   dict(path='empty',kind='directory',mode=0o755)]
        def once(label):
            transport=[]
            def save(p):
                transport.append(p.read_bytes())
                return dict(bytes=p.stat().st_size,sha256=sha(p))
            assets=stream_parts(source,entries,temp,label,save,4096)
            return assets,b''.join(transport)
        a,raw=once('one');b,repeated=once('two')
        assert a==b and raw==repeated and len(a)>1
        unpacked=subprocess.check_output(['zstd','-q','-d','-c'],input=raw)
        with tarfile.open(fileobj=io.BytesIO(unpacked)) as tar:
            assert tar.extractfile('example/data.bin').read()==(source/'data.bin').read_bytes()
            assert tar.getmember('example/alias').linkname=='data.bin'
            assert tar.getmember('example/empty').isdir()
        entries[1]['sha256']='0'*64
        try:
            stream_parts(source,entries,temp,'corrupt',lambda p:None,4096)
        except ValueError:
            pass
        else:
            raise AssertionError('Changed source was not rejected')
        assert matches(dict(state='uploaded',size=1,digest='sha256:abc'),dict(bytes=1,sha256='abc'))
        assert not matches(dict(state='uploaded',size=1,digest='sha256:xyz'),dict(bytes=1,sha256='abc'))
    print('PASS: deterministic multipart round-trip, empty directories, portable symlink, source mismatch and remote digest rejection')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--self-test',action='store_true')
    ap.add_argument('--dataset',action='append')
    ap.add_argument('--workers',type=int,default=3)
    args=ap.parse_args()
    if args.self_test:
        self_test()
        return
    records=json.loads((OUT/'mapping.json').read_text())['datasets']
    if args.dataset:
        unknown=set(args.dataset)-{r['dataset'] for r in records}
        if unknown:
            raise ValueError('Unknown datasets: '+str(unknown))
        records=[r for r in records if r['dataset'] in args.dataset]
    if not 1 <= args.workers <= 4:
        raise ValueError('Use between one and four bounded-spool upload workers')
    # Three independent datasets can upload concurrently; each retains just one part.
    receipts=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        jobs={pool.submit(archive,r):r for r in sorted(records,key=lambda r:r['bytes'])}
        for future in concurrent.futures.as_completed(jobs):
            record=jobs[future]
            receipts.append(future.result())
            write(OUT/'progress.json',dict(selected=len(records),verified=len(receipts),
                                          verified_file_bytes=sum(r['file_bytes'] for r in receipts),
                                          latest=record['dataset'],updated_at=datetime.datetime.now().astimezone().isoformat()))
    print('ALL SELECTED DATASETS VERIFIED',len(receipts),flush=True)


if __name__=='__main__':
    main()
