# 阶段33：普通恢复目标提前搜索

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261019-recovery-slot`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261019-recovery-slot)。
- 归档标签提交：[`ba7942ce176378d68b0eeab99a4f4bb9a5e68913`](https://github.com/CQULzz/HT_Explo/commit/ba7942ce176378d68b0eeab99a4f4bb9a5e68913)。
- 记录的实验候选：[`ba7942c`](https://github.com/CQULzz/HT_Explo/tree/ba7942ce176378d68b0eeab99a4f4bb9a5e68913)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-recovery-slot)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

首个主要目标后插入普通恢复搜索，保留硬约束和原预算

避免主要目标反复超时挤占普通恢复，记录实际恢复/回退尝试

## 验证与剩余问题

4个CTest通过；室内600秒151.57m/2480.000m³；末分钟15.525m，13项采集核验/完整视频通过

仍有232次搜索超时，最长全零35.800s；地图/路径时效、真值覆盖/重复多环境未全部验收

## 报告及版本证据

- [docs/results/ht_recovery_search_slot_10min_2026-10-19/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_recovery_search_slot_10min_2026-10-19/REPORT.md)
- 原版本总表记录的控制提交：`ba7942ce176378d68b0eeab99a4f4bb9a5e68913`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261019-recovery-slot-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261019-recovery-slot/ht-stage-20261019-recovery-slot-indoor.mp4) — 12014571 bytes；`sha256:0860639e53c10bdb559b48c579a6463ad2e517c1a1087211f759a5615459885a`。

## 完整数据及上传回执

- [docs/experiments/publications/stage33.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage33.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
