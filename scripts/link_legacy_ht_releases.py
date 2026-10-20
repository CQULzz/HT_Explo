#!/usr/bin/env python3
"""Append the completed historical data index without changing existing release notes."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/experiments/legacy_archive'
REPO='CQULzz/HT_Explo'
START='<!-- legacy-full-data-start -->'
END='<!-- legacy-full-data-end -->'


def append(body,section):
    if START in body or END in body:
        if body.count(START)!=1 or body.count(END)!=1:
            raise ValueError('Malformed archive section markers; do not rewrite notes')
        a,b=body.index(START),body.index(END)+len(END)
        return body[:a]+section+body[b:]
    return body.rstrip()+'\n\n'+section+'\n'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--apply',action='store_true');args=ap.parse_args()
    records=json.loads((OUT/'mapping.json').read_text())['datasets']
    receipts={p.stem:json.loads(p.read_text()) for p in (OUT/'receipts').glob('*.json')}
    if set(receipts)!={r['dataset'] for r in records}:
        raise ValueError('Only append final completed index after all 62 datasets are verified')
    groups={}
    for r in records:groups.setdefault(r['tag'],[]).append(r)
    updated=[]
    for tag,rows in groups.items():
        remote=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{tag}'],text=True))
        body=remote['body'] or ''
        lines=[START,'## 历史完整实验数据补归档（2026-10-20）','',
               f'本阶段关联的 **{len(rows)} 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。',
               '','**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。','',
               '[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)','',
               '| 历史目录 | 原始文件GiB | 完整数据前缀 |','|---|---:|---|']
        for r in sorted(rows,key=lambda x:x['dataset']):
            receipt=receipts[r['dataset']]
            lines.append(f'| `{r["dataset"]}` | {receipt["file_bytes"]/1024**3:.4f} | `{receipt["content_key"]}` |')
        lines += ['', '下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。',END]
        section='\n'.join(lines);new=append(body,section)
        notes=ROOT/'docs/release_notes'/(tag+'.md')
        if not notes.exists():raise FileNotFoundError(notes)
        if args.apply:
            with tempfile.TemporaryDirectory(prefix='ht-release-index-') as temporary:
                path=Path(temporary)/'notes.md';path.write_text(new)
                subprocess.run(['gh','release','edit',tag,'--repo',REPO,'--notes-file',str(path)],check=True)
            after=json.loads(subprocess.check_output(['gh','api',f'repos/{REPO}/releases/tags/{tag}'],text=True))
            if after['body']!=new or after['tag_name']!=tag:
                raise ValueError('Release notes verification mismatch')
            notes.write_text(append(notes.read_text(),section))
        updated.append(dict(tag=tag,datasets=len(rows),body_sha256=__import__('hashlib').sha256(new.encode()).hexdigest()))
        print(('UPDATED' if args.apply else 'READY'),tag,len(rows),flush=True)
    if args.apply:
        (OUT/'release_links_verified.json').write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n')


if __name__=='__main__':main()
