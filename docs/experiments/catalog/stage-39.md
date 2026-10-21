# 阶段39：XYθ支配边提前剪枝，减少注定丢弃的硬检查

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261020-successor-pruning`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261020-successor-pruning)。
- 归档标签提交：[`6fc754903f0e7c9aafe4b2a2b13c3fa24266551a`](https://github.com/CQULzz/HT_Explo/commit/6fc754903f0e7c9aafe4b2a2b13c3fa24266551a)。
- 记录的实验候选：[`6fc7549`](https://github.com/CQULzz/HT_Explo/tree/6fc754903f0e7c9aafe4b2a2b13c3fa24266551a)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261020-successor-pruning)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

相同终点键/代价支配检查放到HT/几何检查前，接受边仍逐段硬验证；预算/候选/覆盖评分不变

冻结公开输入固定256展开查询减少约67%；18组合成实际成功路线代价/逐姿态相同。预算内4目标新旧仍均超时，保留反例

## 验证与剩余问题

完整车库600秒199.69m/6483.000m³，13项采集及4项CTest通过；剪枝1048111条

体积较38+11.6%，仍低于36；搜索超时81→65，但末分钟新增553.75→274.515m³、完全停车3.73%→4.84%。单目标覆盖/欧氏引导结构未改，没有同控制约束新原版配对，不证明追平TARE

## 报告及版本证据

- [docs/results/ht_successor_pruning_10min_2026-10-20/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_successor_pruning_10min_2026-10-20/REPORT.md)
- 原版本总表记录的控制提交：`6fc754903f0e7c9aafe4b2a2b13c3fa24266551a`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261020-successor-pruning-garage.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261020-successor-pruning/ht-stage-20261020-successor-pruning-garage.mp4) — 9404367 bytes；`sha256:55e93ed2907291e7dee2ca4b1e30f08a850ed875e0ab97fe04b19f9fc28a9793`。

## 完整数据及上传回执

- [docs/experiments/publications/stage39.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage39.json)
- [docs/experiments/legacy_archive/receipts/ht_revision_metric_reanalysis_2026-10-19.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_revision_metric_reanalysis_2026-10-19.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_revision_metric_reanalysis_2026-10-19

- 数据分片前缀：`legacy-ht_revision_metric_reanalysis_2026-10-19-2ffd2e20d69f`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_revision_metric_reanalysis_2026-10-19.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_revision_metric_reanalysis_2026-10-19.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。
