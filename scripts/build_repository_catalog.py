#!/usr/bin/env python3
"""Build code/experiment/video links from existing provenance and upload receipts.

Read-only with respect to GitHub: --refresh-remote verifies asset metadata, not
payload downloads. Missing experiment provenance remains missing. No tag or
release is created or moved by this program.
"""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/experiments/catalog'
REPO = 'CQULzz/HT_Explo'
WEB = 'https://github.com/' + REPO


def read(path):
    return json.loads(path.read_text())


def dump(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def gh(path, paginate=False):
    args = ['gh', 'api']
    if paginate:
        args += ['--paginate', '--slurp']
    data = json.loads(subprocess.check_output(args + [path], text=True))
    return [item for page in data for item in page] if paginate else data


def remote_snapshot():
    releases = gh(f'repos/{REPO}/releases?per_page=100', True)
    for release in releases:
        # Always paginate the asset endpoint, independent of embedded list limits.
        if len(release['assets']) >= 30:
            release['assets'] = gh(
                f'repos/{REPO}/releases/{release["id"]}/assets?per_page=100', True)
    return {
        'verified_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'method': 'GitHub API uploaded state, size and server SHA256 versus local publication receipts; no full payload redownload.',
        'releases': [{
            'tag': r['tag_name'], 'id': r['id'], 'url': r['html_url'],
            'assets': [{k: a.get(k) for k in
                        ['id', 'name', 'state', 'size', 'digest', 'browser_download_url']}
                       for a in r['assets']],
        } for r in releases],
    }


def relpath(path):
    text = str(path)
    marker = 'HT_Explo-fixposition/'
    return text.split(marker, 1)[1] if marker in text else text


def code(path, ref='main'):
    return WEB + '/blob/' + ref + '/' + quote(str(path), safe='/')


def verify_receipts(receipts, remote):
    by_tag = {r['tag']: r for r in remote['releases']}
    checked = {}
    for path, receipt in receipts:
        if receipt['tag'] not in by_tag:
            raise ValueError(f'Missing remote release: {receipt["tag"]}')
        assets = {a['name']: a for a in by_tag[receipt['tag']]['assets']}
        for expected in receipt.get('assets', []):
            actual = assets.get(expected['name'])
            if not actual or actual['state'] != 'uploaded' or \
               actual['size'] != expected['bytes'] or \
               actual['digest'] != 'sha256:' + expected['sha256']:
                raise ValueError(f'Remote asset mismatch: {path}: {expected["name"]}')
            key = (receipt['tag'], expected['name'])
            if key in checked and checked[key]['sha256'] != expected['sha256']:
                raise ValueError(f'Conflicting receipts: {key}')
            checked[key] = {'tag': key[0], 'name': key[1], 'sha256': expected['sha256']}
    return checked


def generate(remote):
    version = read(ROOT / 'docs/version_history.json')
    mapping = read(ROOT / 'docs/experiments/legacy_archive/mapping.json')
    receipts = [(p, read(p)) for directory in
                ['publications', 'publication_addenda', 'legacy_archive/receipts']
                for p in sorted((ROOT / 'docs/experiments' / directory).glob('*.json'))]
    checked = verify_receipts(receipts, remote)
    by_tag = {r['tag']: r for r in remote['releases']}
    legacy = {d['dataset']: d for d in mapping['datasets']}
    rows = []
    for stage in version['stages']:
        tag = stage['tag']
        # Confirm each archive tag in the local Git object database. Remote refs
        # are independently checked during publication; fetching is explicit.
        actual = subprocess.check_output(
            ['git', 'rev-parse', tag + '^{commit}'], cwd=ROOT, text=True).strip()
        if actual != stage['sha']:
            raise ValueError('Tag/catalogue disagreement: ' + tag)
        assigned = [(p, d) for p, d in receipts if d['tag'] == tag]
        modern = [(p, d) for p, d in assigned if p.parent.name == 'publications']
        historical = []
        for path, receipt in assigned:
            if path.parent.name != 'receipts':
                continue
            original = legacy[receipt['dataset']]
            inventory = ROOT / 'docs/experiments/legacy_archive/inventories' / path.name
            if not inventory.exists():
                raise ValueError('Missing historical inventory: ' + str(inventory))
            historical.append({
                'dataset': receipt['dataset'], 'association': original['association'],
                'recorded_provenance': original.get('provenance', []),
                'original_status_evidence': original.get('original_status_evidence', []),
                'receipt': str(path.relative_to(ROOT)),
                'inventory': str(inventory.relative_to(ROOT)),
                'content_key': receipt['content_key'],
                'archived_videos': [e for e in read(inventory)['entries']
                                    if e.get('kind') == 'file' and
                                    Path(e['path']).suffix.lower() in ('.mp4', '.mkv', '.avi', '.webm')],
            })
        frozen = []
        roots = {Path(relpath(d['result_archive'])) for _, d in modern}
        roots.update(Path(p).parent for p in stage['evidence'] if p.endswith('/REPORT.md'))
        for root in sorted(roots):
            path = ROOT / root / 'frozen_job.json'
            if path.exists():
                job = read(path)
                frozen.append({'path': str(path.relative_to(ROOT)), **{
                    k: job[k] for k in ['candidate_commit', 'navigation_control_commit',
                                        'upstream_commit', 'scene', 'duration_per_scene_s']
                    if k in job}})
        uploaded = [a for a in by_tag[tag]['assets'] if a['state'] == 'uploaded']
        videos = [a for a in uploaded
                  if Path(a['name']).suffix.lower() in ('.mp4', '.mkv', '.avi', '.webm')]
        row = {
            'number': stage['number'], 'title': stage['title'], 'tag': tag,
            'archive_tag_commit': stage['sha'],
            'recorded_candidates': sorted({d['tested_commit'] for _, d in modern}),
            'historical_control_commit': stage.get('control_commit'),
            'frozen_jobs': frozen, 'change': stage['change'], 'features': stage['features'],
            'validation': stage['validation'], 'known_issues': stage['known_issues'],
            'reports': stage['evidence'], 'release': by_tag[tag]['url'],
            'publication_receipts': [str(p.relative_to(ROOT)) for p, _ in assigned],
            'collection_validation': [d['collection_validation'] for _, d in modern
                                      if 'collection_validation' in d],
            'direct_videos': videos, 'release_assets': uploaded,
            'incomplete_remote_assets': [a for a in by_tag[tag]['assets'] if a['state'] != 'uploaded'],
            'legacy_datasets': historical,
        }
        rows.append(row)
    result = {
        'schema_version': 1, 'generated_from': 'Existing checked-in stage catalogue, upload receipts, frozen jobs, historical inventories and current GitHub metadata.',
        'remote_verified_at': remote['verified_at'],
        'verification_scope': remote['method'],
        'counts': {'stages': len(rows), 'legacy_datasets': len(legacy),
                   'publication_receipts': len(receipts), 'verified_receipt_assets': len(checked),
                   'release_assets': sum(len(r['release_assets']) for r in rows),
                   'direct_videos': sum(len(r['direct_videos']) for r in rows),
                   'legacy_archived_videos': sum(len(d['archived_videos']) for r in rows for d in r['legacy_datasets'])},
        'stages': rows,
    }
    outputs = {OUT / 'index.json': json.dumps(result, ensure_ascii=False, indent=2) + '\n'}
    overview = [
        '# 实验与历史资料索引', '',
        '按阶段查代码、报告、可直接下载的视频和完整录包。GitHub阶段标签是归档锚点，实际测量候选与导航提交分栏保存。', '',
        '早期62个目录只关联到研究阶段；未记录的测量提交保持待确认。归档完整不等于600秒验收通过，失败、中止与未运行状态均保留。', '',
        f'远端核验时间：{remote["verified_at"]}。逐项比较发布回执中的大小、SHA256与上传状态；没有重新下载全部数据。', '',
        '[分支与标签说明](../../REPOSITORY_GUIDE.md) · [机器可读清单](index.json) · [远端核验清单](remote_assets_verified.json)', '',
        '| 阶段 | 改动/功能 | 归档提交 | 直接视频 | 历史目录 | 详情 |',
        '|---|---|---|---:|---:|---|',
    ]
    versions = ['# 版本总览', '',
                '导航版本、实验归档、可视化版本分别标识；[分支与标签](docs/REPOSITORY_GUIDE.md)，[全部实验资料](docs/experiments/catalog/INDEX.md)。', '',
                '已完整归档的最新导航为`07c1abd`，室内/校园对照沿用它。`develop`包含`3f589d8`输入校验候选，没有完整600秒验收。已知问题逐轮列出，不能称为无缺陷版本。', '',
                '| 阶段 | 改动及实现 | 验证与问题 | 代码/数据/视频 |',
                '|---|---|---|---|']
    def cell(value):
        return str(value).replace('|', '\\|').replace('\n', ' ')
    for row in reversed(rows):
        n = row['number']
        overview.append(f'| {n:02d} | {cell(row["title"])} | `{row["archive_tag_commit"][:7]}` | {len(row["direct_videos"])} | {len(row["legacy_datasets"])} | [查看](stage-{n:02d}.md) |')
        versions.append(f'| {n:02d} | {cell(row["change"])}<br>{cell(row["features"])} | {cell(row["validation"])}<br>**限制：**{cell(row["known_issues"])} | [阶段{n:02d}](docs/experiments/catalog/stage-{n:02d}.md) |')
        lines = [f'# 阶段{n:02d}：{row["title"]}', '', '[返回总索引](INDEX.md)', '',
                 f'- 阶段标签：[`{row["tag"]}`]({WEB}/tree/{row["tag"]})。',
                 f'- 归档标签提交：[`{row["archive_tag_commit"]}`]({WEB}/commit/{row["archive_tag_commit"]})。',
                 '- 记录的实验候选：' + (', '.join(f'[`{sha[:7]}`]({WEB}/tree/{sha})' for sha in row['recorded_candidates']) or '现代发布回执无记录；查下方原始清单，待确认。'),
                 f'- [GitHub Release：完整数据及附件]({row["release"]})。', '',
                 '归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。', '',
                 '## 改动及实现', '', row['change'], '', row['features'], '',
                 '## 验证与剩余问题', '', row['validation'], '', row['known_issues'], '',
                 '## 报告及版本证据', '']
        lines += [f'- [{p}]({code(p)})' for p in row['reports']]
        for job in row['frozen_jobs']:
            lines += [f'- [冻结清单]({code(job["path"])})：' + '；'.join(f'{k}=`{v}`' for k, v in job.items() if k != 'path')]
        if row['historical_control_commit']:
            lines += [f'- 原版本总表记录的控制提交：`{row["historical_control_commit"]}`。这是历史字段，不能替代运行时快照/补丁核对。']
        lines += ['','## 可直接下载的视频','']
        lines += [f'- [{v["name"]}]({v["browser_download_url"]}) — {v["size"]} bytes；`{v["digest"]}`。' for v in row['direct_videos']] or ['本Release没有独立视频附件；请查历史目录内的视频及原报告。']
        lines += ['', '## 完整数据及上传回执', '']
        lines += [f'- [{p}]({code(p)})' for p in row['publication_receipts']] or ['没有对应上传回执；不能据此宣称存在完整录包。']
        lines += ['', '完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。', '',
                  '## 早期历史目录与包内视频', '',
                  '以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。', '']
        for d in row['legacy_datasets']:
            lines += [f'### {d["dataset"]}', '', f'- 数据分片前缀：`{d["content_key"]}`。',
                      f'- [上传回执]({code(d["receipt"])}) · [包内逐文件SHA256清单]({code(d["inventory"])})。',
                      '- 原测量源码记录：`' + json.dumps(d['recorded_provenance'], ensure_ascii=False) + '`。',
                      '- 原状态证据：`' + json.dumps(d['original_status_evidence'], ensure_ascii=False) + '`。']
            lines += [f'- 包内视频：`{e["path"]}`；{e["bytes"]} bytes；SHA256 `{e["sha256"]}`。' for e in d['archived_videos']]
            lines += ['']
        if not row['legacy_datasets']:
            lines += ['无早期历史目录关联。', '']
        outputs[OUT / f'stage-{n:02d}.md'] = '\n'.join(lines).rstrip() + '\n'
    outputs[OUT / 'INDEX.md'] = '\n'.join(overview) + '\n'
    outputs[ROOT / 'VERSIONS.md'] = '\n'.join(versions) + '\n'
    return outputs, result['counts']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-remote', action='store_true')
    parser.add_argument('--check', action='store_true', help='Compare generated output without modifying it.')
    args = parser.parse_args()
    if args.check and args.refresh_remote:
        parser.error('--check uses the saved snapshot; refresh it separately.')
    snapshot = OUT / 'remote_assets_verified.json'
    remote = remote_snapshot() if args.refresh_remote else read(snapshot)
    outputs, counts = generate(remote)
    if args.check:
        stale = [str(p.relative_to(ROOT)) for p, text in outputs.items()
                 if not p.exists() or p.read_text() != text]
        if stale:
            raise SystemExit('Stale generated files: ' + ', '.join(stale))
    else:
        if args.refresh_remote:
            dump(snapshot, remote)
        for path, text in outputs.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    print(json.dumps({'check': args.check, **counts}, ensure_ascii=False))


if __name__ == '__main__':
    main()
