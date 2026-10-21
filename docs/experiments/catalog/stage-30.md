# 阶段30：正收益全局任务保留：600秒169.57m/3321.25m³仍探索

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261018-pending-gain`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-pending-gain)。
- 归档标签提交：[`ce7202bb14fa493d6ee2e4cb68dd8d56b32aef0b`](https://github.com/CQULzz/HT_Explo/commit/ce7202bb14fa493d6ee2e4cb68dd8d56b32aef0b)。
- 记录的实验候选：[`ce7202b`](https://github.com/CQULzz/HT_Explo/tree/ce7202bb14fa493d6ee2e4cb68dd8d56b32aef0b)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-pending-gain)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

按收益登记UNSEEN，全局保留仍有收益的任务，防止移出邻域核销

HT/物理硬门槛不变；原零收益覆盖/已覆盖滞回/非HT保持

## 验证与剩余问题

4个CTest目标与10项新状态回归通过；600秒169.57m/3321.25m³；最后60秒17.829m；有收益UNSEEN33→0、almost移出核销5→0

102次TIME_LIMIT；五次无候选覆盖分支仍需修正，3次此前刚有收益；1次地图超时和4次路径超时，重复/多环境/真值覆盖仍未验收

## 报告及版本证据

- [docs/results/ht_pending_gain_tasks_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_pending_gain_tasks_10min_2026-10-18/REPORT.md)
- 原版本总表记录的控制提交：`ce7202bb14fa493d6ee2e4cb68dd8d56b32aef0b`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261018-pending-gain-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-pending-gain/ht-stage-20261018-pending-gain-indoor.mp4) — 13758724 bytes；`sha256:eaf902cb667619d47d44f15d7961093270c3f86f64fbee3d5510dad846949202`。

## 完整数据及上传回执

- [docs/experiments/publications/stage30.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage30.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
