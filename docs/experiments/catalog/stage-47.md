# 阶段47：原TARE与最新HT同运动上限室内600秒对照

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261021-tare-matched`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261021-tare-matched)。
- 归档标签提交：[`1ded85a7b66ad9506bb26b7abe4e1c1def946648`](https://github.com/CQULzz/HT_Explo/commit/1ded85a7b66ad9506bb26b7abe4e1c1def946648)。
- 记录的实验候选：[`1ded85a`](https://github.com/CQULzz/HT_Explo/tree/1ded85a7b66ad9506bb26b7abe4e1c1def946648)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261021-tare-matched)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

新增比较设施；HT导航不改；原TARE使用原探索/TSP与显式对齐的控制包络

独立双600秒/共同观测指标/限幅前后指令/参数与视频

## 验证与剩余问题

- 原TARE同运动上限：600秒、188.19m、4116.125m³，末任务EXPLORING，最长完全停车1.600s。；- 最新HT：600秒、190.53m、5027.125m³，末任务EXPLORING，最长完全停车6.400s。

原CMU采后SIGINT退出异常；单次端到端对照，网格密度不同；非HT单模块消融

## 报告及版本证据

- [docs/results/ht_tare_matched_10min_2026-10-21/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_tare_matched_10min_2026-10-21/REPORT.md)
- [docs/results/ht_tare_matched_10min_2026-10-21_review/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_tare_matched_10min_2026-10-21_review/REPORT.md)
- [冻结清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_tare_matched_10min_2026-10-21/frozen_job.json)：candidate_commit=`1ded85a7b66ad9506bb26b7abe4e1c1def946648`；navigation_control_commit=`07c1abd334f83cb8d602e2234134b4286862c916`；upstream_commit=`b6760adb4280b379567c76f4e684ce628e28ef71`；duration_per_scene_s=`600`

## 可直接下载的视频

- [ht-stage-20261021-tare-matched-original.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-tare-matched/ht-stage-20261021-tare-matched-original.mp4) — 11075399 bytes；`sha256:9c91ad7259e094ab90c8650e8f2bb8577186b6d8e5c9df1368cb707c9e96ba67`。
- [ht-stage-20261021-tare-matched-ht.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-tare-matched/ht-stage-20261021-tare-matched-ht.mp4) — 14184308 bytes；`sha256:8eb3823ba487b5cb2684967678f1ff2621f232adda9f5fcbf3416e5cf89ff9b5`。
- [stage47-rviz-comparison-4x.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-tare-matched/stage47-rviz-comparison-4x.mp4) — 2241117 bytes；`sha256:639c1504b2a07dc2d3ff648f67195c828b15efb32c5f89ccaf6245d33021bd4c`。
- [stage47-rviz-xytheta-4x.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-tare-matched/stage47-rviz-xytheta-4x.mp4) — 38895981 bytes；`sha256:732d76b67985a5ce2cfcaf1e371819c63cbb5d3c37cfd5bee2ca67c91aaf499a`。

## 完整数据及上传回执

- [docs/experiments/publications/stage47.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage47.json)
- [docs/experiments/publication_addenda/stage47_rviz.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publication_addenda/stage47_rviz.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
