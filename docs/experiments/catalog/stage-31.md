# 阶段31：候选缺失保留有效收益：核销正确但体积退步

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261019-deferred-gain`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261019-deferred-gain)。
- 归档标签提交：[`b05ed9e717a3e430cc6243ed61666b5120f76e5b`](https://github.com/CQULzz/HT_Explo/commit/b05ed9e717a3e430cc6243ed61666b5120f76e5b)。
- 记录的实验候选：[`b05ed9e`](https://github.com/CQULzz/HT_Explo/tree/b05ed9e717a3e430cc6243ed61666b5120f76e5b)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-deferred-gain)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

记录最后有效收益、候选缺失延期，有效评估核销及完成守卫

不凭候选暂缺报覆盖；零收益导航/既有滞回/非HT保持

## 验证与剩余问题

18项几何/状态回归及4个CTest目标通过；600秒162.71m/2703.875m³；19单元延期、4次重新评估解除登记、无候选误核销0；实际拦截全零

体积比阶段30下降18.6%；81次TIME_LIMIT及地图/路径时效；末刻EMPTY_PATH零速度，未验证后续恢复；真值/重复/多环境未验收

## 报告及版本证据

- [docs/results/ht_deferred_gain_tasks_10min_2026-10-19/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_deferred_gain_tasks_10min_2026-10-19/REPORT.md)
- 原版本总表记录的控制提交：`b05ed9e717a3e430cc6243ed61666b5120f76e5b`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261019-deferred-gain-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261019-deferred-gain/ht-stage-20261019-deferred-gain-indoor.mp4) — 13575394 bytes；`sha256:f28898a4702a4e368d136b5955b01c3337e3891faf318dcc6218fbbdc5d86657`。

## 完整数据及上传回执

- [docs/experiments/publications/stage31.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage31.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
