# 阶段45：已知障碍足迹与原TARE地形提示统一

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261021-terrain-footprint`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261021-terrain-footprint)。
- 归档标签提交：[`15e197eca16bee3dea1fcd3870a05ee84f2ecd12`](https://github.com/CQULzz/HT_Explo/commit/15e197eca16bee3dea1fcd3870a05ee84f2ecd12)。
- 记录的实验候选：[`15e197e`](https://github.com/CQULzz/HT_Explo/tree/15e197eca16bee3dea1fcd3870a05ee84f2ecd12)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261021-terrain-footprint)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

原地形提示遗漏已知车体障碍；增加精确查询、历史缓存更新，保留未知引导

保持原TARE TSP与HT严格执行约束；同室内600s独立对比

## 验证与剩余问题

RECORDED {'distance_m': 169.14, 'visited_1m_xy_cells': 140, 'observed_free_volume_m3': 3625.625, 'mission': 'BLOCKED', 'map_age_p95_s': 0.8616966724395752, 'map_age_max_s': 1.3770060539245605}; fourCTest50.65s/sixSHA

室内末状态BLOCKED，仍有路线问题；最长完全停车65.060s，结合任务状态判断；森林8000次展开上限与隧道53s结束线索本轮未复测，不能宣称已解决；单次600s不证明所有环境、长时运行或真实车辆稳定；无新增同限制原版TARE配对

## 报告及版本证据

- [docs/results/ht_known_body_terrain_10min_2026-10-21/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_known_body_terrain_10min_2026-10-21/REPORT.md)
- [冻结清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_known_body_terrain_10min_2026-10-21/frozen_job.json)：candidate_commit=`15e197eca16bee3dea1fcd3870a05ee84f2ecd12`；navigation_control_commit=`15e197eca16bee3dea1fcd3870a05ee84f2ecd12`；duration_per_scene_s=`600`

## 可直接下载的视频

- [ht-stage-20261021-terrain-footprint-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-terrain-footprint/ht-stage-20261021-terrain-footprint-indoor.mp4) — 13254382 bytes；`sha256:06f79b2306f88de6522165ef8c6d1aa2e0d93afef849607c8ebf844bb2cf5922`。

## 完整数据及上传回执

- [docs/experiments/publications/stage45.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage45.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
