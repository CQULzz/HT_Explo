# 阶段41：原TARE图与HT禁行掩码同步，恢复近家HOME优先级

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261020-tare-boundaries`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261020-tare-boundaries)。
- 归档标签提交：[`68701319b333165dd9cd5acf8e226ba52c174434`](https://github.com/CQULzz/HT_Explo/commit/68701319b333165dd9cd5acf8e226ba52c174434)。
- 记录的实验候选：[`6870131`](https://github.com/CQULzz/HT_Explo/tree/68701319b333165dd9cd5acf8e226ba52c174434)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261020-tare-boundaries)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

BFS/候选图共用本周期地形掩码；近家rush-home目标优先，再做HT路由；不改六核心TARE函数与TSP

真实ROS禁行带、异步更新、解除禁行及HOME无前视回归通过；原40失败证据保留

## 验证与剩余问题

完整车库600秒181.31m/8660.125m³，13项采集、4项CTest与六函数SHA通过

搜索时间上限34次、展开上限57次，最长完全停车0.25s，末60秒新增671.645m³/移动16.56m；末尾EXPLORING。 单次闭环不证明因果收益；没有同限制新原版配对、全局SE2可达/实车保证；返航单元回归不等于该600秒触发返航

## 报告及版本证据

- [docs/results/ht_tare_boundaries_10min_2026-10-20/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_tare_boundaries_10min_2026-10-20/REPORT.md)
- 原版本总表记录的控制提交：`68701319b333165dd9cd5acf8e226ba52c174434`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261020-tare-boundaries-garage.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261020-tare-boundaries/ht-stage-20261020-tare-boundaries-garage.mp4) — 10118346 bytes；`sha256:f211e0b0dc3744bab35d790e79cb8fee733a778d8c1dd58223a7276d050d61dd`。

## 完整数据及上传回执

- [docs/experiments/publications/stage41.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage41.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
