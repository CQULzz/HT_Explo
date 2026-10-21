# 阶段44：稀疏高程纹理修正与四场景600秒实测

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261021-sparse-height`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261021-sparse-height)。
- 归档标签提交：[`454efa230fae337cfa8f87b2aa87ee9917040621`](https://github.com/CQULzz/HT_Explo/commit/454efa230fae337cfa8f87b2aa87ee9917040621)。
- 记录的实验候选：[`454efa2`](https://github.com/CQULzz/HT_Explo/tree/454efa230fae337cfa8f87b2aa87ee9917040621)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261021-sparse-height)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

对称已观测邻域有限滤波与小特征保护；扩充准确输入诊断，不改模型或原TSP

多帧高程供HT；原TARE访问顺序、XYθ路由和硬门禁保持

## 验证与剩余问题

indoor=RECORDED:{'distance_m': 62.88, 'visited_1m_xy_cells': 59, 'observed_free_volume_m3': 1849.25, 'mission': 'BLOCKED', 'map_age_p95_s': 1.2692938446998594, 'map_age_max_s': 1.3944075107574463}; garage=RECORDED:{'distance_m': 224.11, 'visited_1m_xy_cells': 236, 'observed_free_volume_m3': 9809.375, 'mission': 'EXPLORING', 'map_age_p95_s': 0.9291829347610472, 'map_age_max_s': 1.4759821891784668}; forest=RECORDED:{'distance_m': 46.32, 'visited_1m_xy_cells': 55, 'observed_free_volume_m3': 8377.875, 'mission': 'BLOCKED', 'map_age_p95_s': 1.2872920632362366, 'map_age_max_s': 1.7394349575042725}; tunnel=RECORDED:{'distance_m': 25.62, 'visited_1m_xy_cells': 13, 'observed_free_volume_m3': 448.875, 'mission': 'COMPLETED', 'map_age_p95_s': 0.7127429604530333, 'map_age_max_s': 1.1787598133087158}

indoor末状态BLOCKED，不能称探索成功；indoor记录中5次XYθ搜索达到展开上限，不能据此断言无路；indoor最长完全停车412.53s，需结合任务/门禁解释；forest末状态BLOCKED，不能称探索成功；forest记录中754次XYθ搜索达到展开上限，不能据此断言无路；forest最长完全停车436.05s，需结合任务/门禁解释；tunnel最长完全停车529.38s，需结合任务/门禁解释；tunnel在53.0s采样报告exploration_finished，是否真实全覆盖尚未验证；COMPLETED只表示任务返航条件满足；无新原版同限制配对/训练分布未知/粗图不保证完整SE2/无实车

## 报告及版本证据

- [docs/results/ht_sparse_height_4scene_10min_2026-10-21/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_sparse_height_4scene_10min_2026-10-21/REPORT.md)
- [冻结清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_sparse_height_4scene_10min_2026-10-21/frozen_job.json)：candidate_commit=`454efa230fae337cfa8f87b2aa87ee9917040621`；navigation_control_commit=`d7e0741c1aeeb65f4c0ff404521a4c54f992a330`；duration_per_scene_s=`600`

## 可直接下载的视频

- [ht-stage-20261021-sparse-height-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-sparse-height/ht-stage-20261021-sparse-height-indoor.mp4) — 5868841 bytes；`sha256:f8444199fc1c4e22b0ef35babe991a321a8333534df7628fd995da30116f1669`。
- [ht-stage-20261021-sparse-height-garage.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-sparse-height/ht-stage-20261021-sparse-height-garage.mp4) — 10029801 bytes；`sha256:c982cb047b900acd2461478ccdd6765c419d0bec32d0217ae2103a9dae7e4c1d`。
- [ht-stage-20261021-sparse-height-forest.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-sparse-height/ht-stage-20261021-sparse-height-forest.mp4) — 32490149 bytes；`sha256:f9db212a5dbd85d176dd0737414b2c6e59863ae5b78df080e802fb665aa55e53`。
- [ht-stage-20261021-sparse-height-tunnel.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-sparse-height/ht-stage-20261021-sparse-height-tunnel.mp4) — 2564983 bytes；`sha256:13ae557753acd28122c6a0cfd5e94a5aa60feacc72c8c4c736b72df71b1b6e6d`。

## 完整数据及上传回执

- [docs/experiments/publications/stage44.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage44.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
