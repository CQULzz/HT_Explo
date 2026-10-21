# 阶段36：冻结版本车库600秒与历史统一口径对比

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261019-frozen-garage`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261019-frozen-garage)。
- 归档标签提交：[`7b4c3589366c6a0bb4f8f1984c14951aa446d1ad`](https://github.com/CQULzz/HT_Explo/commit/7b4c3589366c6a0bb4f8f1984c14951aa446d1ad)。
- 记录的实验候选：[`7b4c358`](https://github.com/CQULzz/HT_Explo/tree/7b4c3589366c6a0bb4f8f1984c14951aa446d1ad)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-frozen-garage)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

导航/桥接保持阶段35版本，独立车库600秒；历史体积按相同源秒口径重新评估，导出说明纠错

记录完整600秒，冻结62个共同文件相同；实际几何分析读取车库0.7m余量

## 验证与剩余问题

187.25m/7900.375m³，13项采集通过；60份上下文CRC、58份同源核对、3份模型重算、视频通过

仍71次搜索超时，最长全零4.95s，地图最大4.117s；单次历史对比不能归因或证明普遍优越，校园/森林/隧道待测

## 报告及版本证据

- [docs/results/ht_frozen_garage_10min_2026-10-19/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_frozen_garage_10min_2026-10-19/REPORT.md)
- 原版本总表记录的控制提交：`391fa0f98fc2a0adab2c018b4c5a1c7c29efff91`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261019-frozen-garage-garage.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261019-frozen-garage/ht-stage-20261019-frozen-garage-garage.mp4) — 9286152 bytes；`sha256:9f81bed58eeda5bb66f618cd659a31e0cc20cf762997b0da1e5fce22d452969b`。

## 完整数据及上传回执

- [docs/experiments/publications/stage36.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage36.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
