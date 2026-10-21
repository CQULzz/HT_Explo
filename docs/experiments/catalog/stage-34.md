# 阶段34：先验算简单SE2连接，再做图搜索

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261019-checked-connections`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261019-checked-connections)。
- 归档标签提交：[`391fa0f98fc2a0adab2c018b4c5a1c7c29efff91`](https://github.com/CQULzz/HT_Explo/commit/391fa0f98fc2a0adab2c018b4c5a1c7c29efff91)。
- 记录的实验候选：[`391fa0f`](https://github.com/CQULzz/HT_Explo/tree/391fa0f98fc2a0adab2c018b4c5a1c7c29efff91)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-checked-connections)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

共用预算、逐段通过原谓词的转向+前进/倒车连接，受阻回原搜索

避免简单局部恢复也展开数千状态点；记录direct标记

## 验证与剩余问题

4个CTest通过；室内600秒168.77m/2169.875m³，直接连接513/754；末分钟14.826m，视频完整、12/13项采集核验（退出快照损坏）

退出时一份NPZ损坏，12/13采集检查通过；体积较阶段33下降12.5%；仍42次超时、地图/路径时效及重复/多环境未验收

## 报告及版本证据

- [docs/results/ht_checked_connections_10min_2026-10-19/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_checked_connections_10min_2026-10-19/REPORT.md)
- 原版本总表记录的控制提交：`391fa0f98fc2a0adab2c018b4c5a1c7c29efff91`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261019-checked-connections-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261019-checked-connections/ht-stage-20261019-checked-connections-indoor.mp4) — 13068029 bytes；`sha256:5c581227826bf03716daf50b5779ee9a08582f66c3283397f9e6d832e34d81a1`。

## 完整数据及上传回执

- [docs/experiments/publications/stage34.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage34.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
