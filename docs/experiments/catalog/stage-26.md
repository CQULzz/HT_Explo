# 阶段26：有限质量拒绝高度保留为硬障碍：里程增加但体积退步

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261018-postfilter-obstacles`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-postfilter-obstacles)。
- 归档标签提交：[`22c2749f395af8bb5dc6705b1e92548acf69494e`](https://github.com/CQULzz/HT_Explo/commit/22c2749f395af8bb5dc6705b1e92548acf69494e)。
- 记录的实验候选：[`22c2749`](https://github.com/CQULzz/HT_Explo/tree/22c2749f395af8bb5dc6705b1e92548acf69494e)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-postfilter-obstacles)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

统一源/融合后有限质量拒绝高度的硬障碍上下文；新增完整网络输入输出记录

不再由有限拒绝高度制造全窗口未知，拒绝格仍八方向强制零

## 验证与剩余问题

7项支撑+实际模型ROS集成通过；600秒116.15m、1258m³；58份上下文同源逐值一致、3份模型重放差0；128次晚拒绝均发零

最终95秒无路停车；比上轮体积下降35.8%，不能以里程增加宣称探索提升；图龄长尾和几何记录缺失仍待解决

## 报告及版本证据

- [docs/results/ht_postfilter_obstacles_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_postfilter_obstacles_10min_2026-10-18/REPORT.md)
- 原版本总表记录的控制提交：`43069a7b11b8028b53f6eae0d6bdc53c13e8affd`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261018-postfilter-obstacles-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-postfilter-obstacles/ht-stage-20261018-postfilter-obstacles-indoor.mp4) — 10608728 bytes；`sha256:04d8b15cce2519137b6fa66f9ba42beff7c9d25eb326a11c76c3b7a68a6e2c70`。

## 完整数据及上传回执

- [docs/experiments/publications/stage26.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage26.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
