#!/usr/bin/env python3
"""Add visualization assets without replacing any stage47 evidence assets."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
REPO = 'CQULzz/HT_Explo'
TAG = 'ht-stage-20261021-tare-matched'
OUT = ROOT/'docs/results/ht_tare_matched_rviz_replay_2026-10-21'
TEMP = ROOT/'.git/rviz-replay-runtime/upload'


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def gh(*args):
    r = subprocess.run(['gh', *args], check=True, capture_output=True, text=True)
    return r.stdout


def release():
    return json.loads(gh('api', f'repos/{REPO}/releases/tags/{TAG}'))


def main():
    original = json.loads((ROOT/'docs/experiments/publications/stage47.json').read_text())
    def check_old(remote):
        for old in original['assets']:
            a = next(a for a in remote['assets'] if a['name'] == old['name'])
            assert a['state'] == 'uploaded' and a['size'] == old['bytes']
            assert a['digest'] == 'sha256:'+old['sha256']
    check_old(release())
    validation = json.loads((OUT/'validation.json').read_text())
    for item in validation.values():
        assert item['frames'] == 1501 and item['full_decode_exit_code'] == 0
        assert sha(OUT/item['file']) == item['sha256']
    TEMP.mkdir(parents=True, exist_ok=True)
    source_files = [(OUT/'rviz_comparison_4x.mp4', 'stage47-rviz-comparison-4x.mp4'),
                    (OUT/'detail/rviz_detail_4x.mp4', 'stage47-rviz-xytheta-4x.mp4')]
    assets = []
    for src,name in source_files:
        dest = TEMP/name
        if not dest.exists() or sha(dest) != sha(src):
            shutil.copyfile(src, dest)
        assets.append(dest)
    # Videos are separate named assets. Bundle contains all other reproducible
    # configs, script snapshots, logs, keyframes and the all-file inventory.
    inventory = {str(p.relative_to(OUT)): sha(p) for p in sorted(OUT.rglob('*'))
                 if p.is_file() and p.name != 'files_sha256.json'}
    (OUT/'files_sha256.json').write_text(json.dumps(inventory, indent=2)+'\n')
    bundle = TEMP/'stage47-rviz-replay-bundle.tar.gz'
    with tarfile.open(bundle, 'w:gz') as tar:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and p.suffix != '.mp4':
                tar.add(p, arcname='rviz_replay/'+str(p.relative_to(OUT)))
    assets.append(bundle)
    receipt = {'tag': TAG, 'release': original['release'], 'type': 'VISUALIZATION_ONLY_ADDENDUM',
               'navigation_control_commit_unchanged': '07c1abd334f83cb8d602e2234134b4286862c916',
               'original_suite_status_unchanged': 'COMPLETED_WITH_ISSUES',
               'existing_assets_verified_unchanged': len(original['assets']),
               'source_publication_receipt_sha256': sha(ROOT/'docs/experiments/publications/stage47.json'),
               'source_review_sha256': sha(OUT/'source_review.json'), 'assets': []}
    def upload_verified(p):
        found = next((a for a in release()['assets'] if a['name'] == p.name), None)
        if found is None:
            gh('release', 'upload', TAG, str(p), '--repo', REPO)
            found = next(a for a in release()['assets'] if a['name'] == p.name)
        assert found['state'] == 'uploaded' and found['size'] == p.stat().st_size
        assert found['digest'] == 'sha256:'+sha(p), p.name
        print('Verified', p.name, found['size'], flush=True)
        return {'name': p.name, 'id': found['id'], 'bytes': found['size'],
                'sha256': sha(p), 'url': found['browser_download_url']}
    for p in assets:
        receipt['assets'].append(upload_verified(p))
    receipt['verified_at'] = datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    proof = TEMP/'stage47-rviz-replay-SHA256.json'
    proof.write_text(json.dumps(receipt, indent=2)+'\n')
    receipt['assets'].append(upload_verified(proof))
    check_old(release())
    target = ROOT/'docs/experiments/publication_addenda/stage47_rviz.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, indent=2)+'\n')
    body = release()['body']
    if 'stage47-rviz-comparison-4x.mp4' not in body:
        body += '\n\n### RViz补录（同一600秒实验数据，非新试验）\n\n'
        body += ('[全局TARE/HT对比](https://github.com/'+REPO+'/releases/download/'+TAG+'/stage47-rviz-comparison-4x.mp4) · '
                 '[HT局部XY与八层XYθ](https://github.com/'+REPO+'/releases/download/'+TAG+'/stage47-rviz-xytheta-4x.mp4)\n\n')
        body += '1080p、10fps、4倍速，各覆盖0～600秒；真实RViz窗口回放。原始采集状态COMPLETED_WITH_ISSUES保持，已有22个证据附件不变。配置/图例/验证见新增replay-bundle附件。\n'
        note = TEMP/'release_notes_with_rviz.md'
        note.write_text(body)
        gh('release', 'edit', TAG, '--repo', REPO, '--notes-file', str(note))


if __name__ == '__main__':
    main()
