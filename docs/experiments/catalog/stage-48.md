# 阶段48：Campus原TARE与当前HT同运动上限各600秒

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261021-campus-matched`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261021-campus-matched)。
- 归档标签提交：[`f7fd77b66fc442752599ead359e8aa60e7773ae4`](https://github.com/CQULzz/HT_Explo/commit/f7fd77b66fc442752599ead359e8aa60e7773ae4)。
- 记录的实验候选：[`f7fd77b`](https://github.com/CQULzz/HT_Explo/tree/f7fd77b66fc442752599ead359e8aa60e7773ae4)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261021-campus-matched)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

仅实验入口增加campus；HT导航仍07c1abd，原TARE/TSP及控制配置保持

各600秒、共同体积指标、运行参数、路线、真实相机与RViz回放

## 验证与剩余问题

- 原TARE同运动上限：600秒、223.53m、17048.250m³，末任务EXPLORING，最长零运动指令区间0.500s。；- 当前HT＋原TARE决策：600秒、218.28m、17722.250m³，末任务EXPLORING，最长零运动指令区间0.950s。

单次对照；失败检查{'original': ['no_child_lifecycle_exception'], 'ht': ['normal_acceleration']}；详见报告

## 报告及版本证据

- [docs/results/ht_tare_campus_matched_10min_2026-10-21/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_tare_campus_matched_10min_2026-10-21/REPORT.md)
- [冻结清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_tare_campus_matched_10min_2026-10-21/frozen_job.json)：candidate_commit=`f7fd77b66fc442752599ead359e8aa60e7773ae4`；navigation_control_commit=`07c1abd334f83cb8d602e2234134b4286862c916`；upstream_commit=`b6760adb4280b379567c76f4e684ce628e28ef71`；scene=`campus`；duration_per_scene_s=`600`

## 可直接下载的视频

- [ht-stage-20261021-campus-matched-ht.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-campus-matched/ht-stage-20261021-campus-matched-ht.mp4) — 52737209 bytes；`sha256:baab01cf78d1d12aba47572fcaf90a444de744e8c4dba32cfdbee0ba2e5f86cb`。
- [ht-stage-20261021-campus-matched-original.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-campus-matched/ht-stage-20261021-campus-matched-original.mp4) — 42342275 bytes；`sha256:3e67bbeb00b87ac10db1ad49456e973da8ec6fffa639381ac60f898205e30d97`。
- [stage48-campus-camera-comparison.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-campus-matched/stage48-campus-camera-comparison.mp4) — 73537230 bytes；`sha256:d98d256a3d8d478760fd2e5c9426a38be6a0a5c4ad4fa0a3e113f8df44cf9310`。
- [stage48-campus-rviz-comparison-4x.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-campus-matched/stage48-campus-rviz-comparison-4x.mp4) — 6350367 bytes；`sha256:c24bc3b8e8c10eb33f53a5c337bc0d4c4d2a5a366493cbc50d1a2141b9523889`。
- [stage48-campus-rviz-xytheta-4x.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-campus-matched/stage48-campus-rviz-xytheta-4x.mp4) — 60104206 bytes；`sha256:02b2501987e0a27a97c37c850f5061feaee96dba1380a6b3bac9585a4cb5efe3`。
- [stage48-xytheta-transparent-voxels-4x.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-campus-matched/stage48-xytheta-transparent-voxels-4x.mp4) — 9899094 bytes；`sha256:2e12318ee50f23e9532e35fadb75bf6124a58ffa5fedd8acdb74e1f166f19574`。

## 完整数据及上传回执

- [docs/experiments/publications/stage48.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage48.json)
- [docs/experiments/publication_addenda/stage48_transparent_voxels.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publication_addenda/stage48_transparent_voxels.json)
- [docs/experiments/publication_addenda/stage48_videos.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publication_addenda/stage48_videos.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
