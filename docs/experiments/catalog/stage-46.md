# 阶段46：连续XYθ空间范围与原TARE覆盖标签解耦

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261021-continuous-domain`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261021-continuous-domain)。
- 归档标签提交：[`07c1abd334f83cb8d602e2234134b4286862c916`](https://github.com/CQULzz/HT_Explo/commit/07c1abd334f83cb8d602e2234134b4286862c916)。
- 记录的实验候选：[`07c1abd`](https://github.com/CQULzz/HT_Explo/tree/07c1abd334f83cb8d602e2234134b4286862c916)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261021-continuous-domain)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

原连续规划范围混入覆盖格候选标签；分离空间范围与原TARE语义

保持原TARE TSP与HT严格执行约束；同室内600s独立对比

## 验证与剩余问题

RECORDED {'distance_m': 187.22, 'visited_1m_xy_cells': 127, 'observed_free_volume_m3': 3934.25, 'mission': 'EXPLORING', 'map_age_p95_s': 0.9583802700042722, 'map_age_max_s': 1.5767745971679688}; fourCTest/sixSHA

森林8000次展开上限与隧道53s结束线索本轮未复测，不能宣称已解决；单次600s不证明所有环境、长时运行或真实车辆稳定；无新增同限制原版TARE配对

## 报告及版本证据

- [docs/results/ht_continuous_domain_10min_2026-10-21/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_continuous_domain_10min_2026-10-21/REPORT.md)
- [冻结清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_continuous_domain_10min_2026-10-21/frozen_job.json)：candidate_commit=`07c1abd334f83cb8d602e2234134b4286862c916`；navigation_control_commit=`07c1abd334f83cb8d602e2234134b4286862c916`；duration_per_scene_s=`600`

## 可直接下载的视频

- [ht-stage-20261021-continuous-domain-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261021-continuous-domain/ht-stage-20261021-continuous-domain-indoor.mp4) — 13949047 bytes；`sha256:2bbcec79050ecb96ee2ab9012233089683d539a0b3eb4045c26d6703ee29f5db`。

## 完整数据及上传回执

- [docs/experiments/publications/stage46.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage46.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
