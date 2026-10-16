#!/usr/bin/env python3
"""Synchronize the checked-in HT milestone catalogue to GitHub Releases.

No tags, commits, branches or existing assets are moved or removed. Authentication
comes from the repository-scoped Actions token, never a checked-in credential.
"""
import argparse
import json
import os
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    data = json.loads((ROOT/'docs/version_history.json').read_text())
    repository = os.environ.get('GITHUB_REPOSITORY', 'CQULzz/HT_Explo')
    if repository != 'CQULzz/HT_Explo':
        raise RuntimeError('This catalogue describes CQULzz/HT_Explo only')
    planned = []
    tags = set()
    for stage in data['stages']:
        tag = stage['tag']
        if tag in tags or '/' in tag or '..' in tag:
            raise ValueError('Invalid or repeated milestone tag')
        tags.add(tag)
        body = (ROOT/'docs/release_notes'/(tag+'.md')).read_text()
        for heading in ['## 改了什么', '## 实现了什么功能', '## 实验与验证', '## 存在什么问题']:
            if heading not in body:
                raise ValueError(f'{tag}: missing {heading}')
        planned.append((stage, body))
    if args.dry_run:
        print(f'Validated {len(planned)} release notes; no remote writes.')
        return
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        raise RuntimeError('GITHUB_TOKEN is required; use the version-notes Actions workflow')

    def api(method, path, payload=None):
        body = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        request = urllib.request.Request(
            'https://api.github.com/repos/'+repository+'/'+path,
            data=body, method=method,
            headers={'Authorization': 'Bearer '+token, 'Accept': 'application/vnd.github+json',
                     'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28',
                     'User-Agent': 'HT-Explo-version-catalogue'})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            message = error.read().decode(errors='replace')[:600]
            raise RuntimeError(f'GitHub API {method} {path}: HTTP {error.code}: {message}') from None

    current = []
    page = 1
    while True:
        batch = api('GET', f'releases?per_page=100&page={page}')
        current.extend(batch)
        if len(batch)<100:
            break
        page += 1
    by_tag = {release['tag_name']: release for release in current}
    results = []
    for stage, body in planned:
        tag = stage['tag']
        # All milestone tags must have been pushed by the maintainer already.
        # Refuse to silently create a lightweight tag on the default branch.
        reference = api('GET', 'git/ref/tags/'+tag)
        obj = reference['object']
        while obj['type']=='tag':
            obj = api('GET', 'git/tags/'+obj['sha'])['object']
        if obj['type']!='commit' or obj['sha']!=stage['sha']:
            raise ValueError(f'{tag}: remote tag does not match catalogue commit')
        fields = dict(name=f'阶段{stage["number"]:02}｜{stage["title"]}', body=body,
                      draft=False, prerelease=True, make_latest='false')
        previous = by_tag.get(tag)
        if previous:
            release = api('PATCH', 'releases/'+str(previous['id']), fields)
            action = 'updated'
            before = {(asset['id'], asset['name'], asset['size'], asset.get('digest'))
                      for asset in previous.get('assets', [])}
            after = {(asset['id'], asset['name'], asset['size'], asset.get('digest'))
                     for asset in release.get('assets', [])}
            if before!=after:
                raise RuntimeError(f'{tag}: existing assets changed unexpectedly')
        else:
            fields.update(tag_name=tag, target_commitish=stage['sha'])
            release = api('POST', 'releases', fields)
            action = 'created'
        if release['body']!=body or not release['prerelease'] or release['draft']:
            raise RuntimeError(f'{tag}: release verification failed')
        results.append((stage['number'], action, release['html_url']))
        print(f'{action}: {tag}: {release["html_url"]}', flush=True)
    summary_path = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary_path:
        with open(summary_path, 'a') as output:
            output.write('# HT版本说明同步完成\n\n所有阶段均为实验预发布，保留原始标签和已有附件。\n\n')
            for number, action, url in results:
                output.write(f'- [阶段{number:02}]({url})：{action}\n')
    print(f'Verified {len(results)} milestone releases; tags and existing assets preserved.')


if __name__=='__main__':
    main()
