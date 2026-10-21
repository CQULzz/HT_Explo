# 阶段24：同规则室内诊断复跑：发现几何根状态拒绝

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261018-latency-diagnosis`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-latency-diagnosis)。
- 归档标签提交：[`bada7bad52fca98a3eb0942c1bc3d9c0a7d84185`](https://github.com/CQULzz/HT_Explo/commit/bada7bad52fca98a3eb0942c1bc3d9c0a7d84185)。
- 记录的实验候选：[`bada7ba`](https://github.com/CQULzz/HT_Explo/tree/bada7bad52fca98a3eb0942c1bc3d9c0a7d84185)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-latency-diagnosis)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

只增加CuPy锁/回调和已有规划分项录制

区分计算、排队、粗视点碰撞与实际车位查询

## 验证与剩余问题

完整600秒23.86m、993.125m³，最终BLOCKED；13项采集检查通过，21次晚拒绝全部发零

约80秒后几何层禁止根状态；时效和表示更新耗时仍存在，阶段23单轮改善未稳定复现

## 报告及版本证据

- [docs/results/ht_latency_diagnosis_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_latency_diagnosis_10min_2026-10-18/REPORT.md)
- 原版本总表记录的控制提交：`149566de09c48a528140b6ec950c08c5fa29539c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261018-latency-diagnosis-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-latency-diagnosis/ht-stage-20261018-latency-diagnosis-indoor.mp4) — 3747236 bytes；`sha256:62db02bee8ca99593169537163d3f92ba295f38ff4f8f7bd79499d075369ff72`。

## 完整数据及上传回执

- [docs/experiments/publications/stage24.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage24.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
