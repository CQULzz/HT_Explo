# 阶段35：诊断写入与完整退出，同导航二进制复测

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261019-atomic-context`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261019-atomic-context)。
- 归档标签提交：[`445b5c1490d6bb198c35bee23e95fc0f7781407e`](https://github.com/CQULzz/HT_Explo/commit/445b5c1490d6bb198c35bee23e95fc0f7781407e)。
- 记录的实验候选：[`445b5c1`](https://github.com/CQULzz/HT_Explo/tree/445b5c1490d6bb198c35bee23e95fc0f7781407e)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-atomic-context)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

SIGINT等待回调完成，诊断NPZ原子发布并严格审计半文件

旧中断ZIP错误复现后修复，保留既有导航/模型/门槛

## 验证与剩余问题

5项针对性回归通过；600秒169.10m/2674.750m³；13项采集检查通过，坏文件/partial为0，视频完整

仍51次超时，最长全零4.200s；整体收益、地图时效/重复多环境未全部验收

## 报告及版本证据

- [docs/results/ht_atomic_context_10min_2026-10-19/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_atomic_context_10min_2026-10-19/REPORT.md)
- 原版本总表记录的控制提交：`391fa0f98fc2a0adab2c018b4c5a1c7c29efff91`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261019-atomic-context-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261019-atomic-context/ht-stage-20261019-atomic-context-indoor.mp4) — 13336808 bytes；`sha256:ac9061deeb11001ba0cbeb5f4f5d1c5c853246a0bda64f5b2e9577d740648bb1`。

## 完整数据及上传回执

- [docs/experiments/publications/stage35.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage35.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
