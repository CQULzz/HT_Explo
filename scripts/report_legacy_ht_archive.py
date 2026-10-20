#!/usr/bin/env python3
"""Render the historical data/version catalogue strictly from verified receipts."""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/experiments/legacy_archive'


def main():
    mapping=json.loads((OUT/'mapping.json').read_text())['datasets']
    receipts={p.stem:json.loads(p.read_text()) for p in (OUT/'receipts').glob('*.json')}
    byte_total=sum(r['bytes'] for r in mapping)
    done=[r for r in mapping if r['dataset'] in receipts]
    lines=['# 历史实验完整数据与版本对应表','',
           f'本次范围：原审计列出的 **62 个历史目录**，常规文件共 **{byte_total/1024**3:.3f} GiB**。',
           f'已完成远端大小与 SHA256 核验：**{len(done)}/62 个目录**，原始文件 **{sum(receipts[r["dataset"]]["file_bytes"] for r in done)/1024**3:.3f} GiB**。其余状态以表格为准，不把待上传当作已备份。','',
           '## 版本对应的含义','',
           'Release 用于归入对应研究阶段；旧标签保持不动。归入某阶段不表示该阶段标签就是实际测试提交。逐目录 inventory 中保留原 manifest 的 git_head/tested_code_commit/current_commit、源文件哈希、working_tree.patch、原始时长及失败说明。没有提交号的旧记录标为未知，不用当前 HEAD 补写。','',
           '多环境目录可能包含不同实际提交；原版 TARE 录包与事后 CuPy/HT 重放属于共享对照资料，不等于 HT 驱车试验。完整录制、中止、短测、离线分析和导航成功是不同概念，本次归档不新增任何“通过”结论。','',
           '## 数据清单','',
           '| 阶段 | 原始目录 | 清单记录提交（另见补丁） | GiB | 备份状态 / Release |','|---|---|---|---:|---|']
    for r in sorted(mapping,key=lambda x:(x['stage'],x['dataset'])):
        n=r['dataset'];rec=receipts.get(n)
        url=f'https://github.com/CQULzz/HT_Explo/releases/tag/{r["tag"]}'
        status=f'[已核验]({url}) · [逐文件清单](inventories/{n}.json) · [回执](receipts/{n}.json)' if rec else f'[待完成]({url})'
        commits=sorted({k+':'+str(v)[:10] for p in r['provenance'] for k,v in p['recorded_commits'].items()})
        code='<br>'.join('`'+c+'`' for c in commits) if commits else '未知 / 见原记录'
        lines.append(f'| {r["stage"]} | `{n}` | {code} | {r["bytes"]/1024**3:.4f} | {status} |')
    lines += ['', '## 下载与恢复','',
              '在对应 Release 下载同一 `legacy-目录名-内容键` 前缀下的所有 `.tar.zst.partNNN`、`-files.json` 和 `-verified.json`。不要混用不同内容键。仓库 receipts 文件额外记录远端 proof 自身的校验值。','',
              '```bash',
              '# 把前缀替换为该数据回执中的 content_key；先依照回执逐个验证大小和 SHA256。',
              "cat legacy-目录名-内容键.tar.zst.part[0-9][0-9][0-9] | zstd -d -c | tar -xf - -C 恢复目录",
              '```','',
              '所有数据集解压到同一个恢复目录，跨目录的相对符号链接才能找到目标。打包不跟随链接复制外部数据；原绝对链接文本保存在清单中，归档内改用等价相对链接。空目录也会保留。所有普通文件内容按逐文件 SHA256 核验。','',
              '上传采用流式 tar + zstd、每卷最多512 MiB，所有上传任务共享最多3个暂存分卷，合计不超过1.5 GiB；中断后重新执行 `python3 scripts/archive_legacy_ht_data.py` 会核对并复用相同远端分卷，不覆盖同名不同内容。完整数据仅放 Release 附件，不写入 Git 历史。','',
              '本次备份工具不会删除历史源目录。原保存政策为 GitHub 全部保留、本机最近两轮完整录包；清理必须另做逐文件本机差异核对，报告、视频和必要回归样本继续保留。第40/41轮完整数据由标准发布流程保留，未重复加入这62个历史目录。','',
              '## 原审计之外的文件','',
              '下载目录的重复视频、HT.zip 项目压缩包，以及其他工作区数据不属于这62个目录；未据此删除或宣称已完整备份。']
    (OUT/'README.md').write_text('\n'.join(lines)+'\n')
    print(f'{len(done)}/62 verified, {sum(receipts[r["dataset"]]["file_bytes"] for r in done)/1024**3:.3f} GiB')


if __name__=='__main__':main()
