# 阶段16：跨目标记忆与正常关停修复（短测验证）

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261017-crossguide-lifecycle`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-crossguide-lifecycle)。
- 归档标签提交：[`bd0c2c24f7eac383a3d8120b312fa4eb499c3199`](https://github.com/CQULzz/HT_Explo/commit/bd0c2c24f7eac383a3d8120b312fa4eb499c3199)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-crossguide-lifecycle)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

全局引导进展跨目标切换保留；零收益到达目标暂缓回访；拆分CuPy发布调度，修复CMU/CuPy/Gazebo关停及完成状态显示。

A→B→A不再重置A的停滞预算；新收益可绕过恢复目标冷却；工作区独立，HT硬门槛、严格未知、3秒时效和0.5m/s上限保留。

## 验证与剩余问题

260核心、15 ROS、6跟踪器、8 CuPy/调度及2关停集成测试通过；第四轮仿真关停回归所有子节点正常退出，无残留。首轮复测中发现额外BLAS线程争用，主动中止并保留证据；后续见阶段17。

短测不证明7.4分钟低收益回访已消除；新长测早期仍采样到超过3秒的地图年龄峰值。远端引导仍是距离启发，无完整全局可执行图；未做实车验证。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/fixes/2026-10-17_endurance_followup.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/fixes/2026-10-17_endurance_followup.md)
- [docs/results/ht_followup_smoke_2026-10-17/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_followup_smoke_2026-10-17/REPORT.md)
- 原版本总表记录的控制提交：`bd0c2c24f7eac383a3d8120b312fa4eb499c3199`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_clean_shutdown_smoke2_2026-10-17.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_clean_shutdown_smoke2_2026-10-17.json)
- [docs/experiments/legacy_archive/receipts/ht_clean_shutdown_smoke3_2026-10-17.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_clean_shutdown_smoke3_2026-10-17.json)
- [docs/experiments/legacy_archive/receipts/ht_cycle_shutdown_smoke_2026-10-17.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_cycle_shutdown_smoke_2026-10-17.json)
- [docs/experiments/legacy_archive/receipts/ht_direct_gazebo_shutdown_smoke4_2026-10-17.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_direct_gazebo_shutdown_smoke4_2026-10-17.json)
- [docs/experiments/legacy_archive/receipts/ht_endurance_crossguide_2026-10-17_02-14-09.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_endurance_crossguide_2026-10-17_02-14-09.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_clean_shutdown_smoke2_2026-10-17

- 数据分片前缀：`legacy-ht_clean_shutdown_smoke2_2026-10-17-371d7d55bff2`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_clean_shutdown_smoke2_2026-10-17.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_clean_shutdown_smoke2_2026-10-17.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "a8fdc8c7f6848ae78d4d3c6eeab9de94e54f1e61"}, "planned_duration_s": 60, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "COMPLETED.json", "state": "see_original_file", "runs": [], "reason": null}]`。
- 包内视频：`camera_2fps.mp4`；865752 bytes；SHA256 `cd13dc5bfcd265804f3814722244ff2ec96794ccef9eedb03f9adcdf604ed3e6`。

### ht_clean_shutdown_smoke3_2026-10-17

- 数据分片前缀：`legacy-ht_clean_shutdown_smoke3_2026-10-17-87ed2633ff21`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_clean_shutdown_smoke3_2026-10-17.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_clean_shutdown_smoke3_2026-10-17.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "a8fdc8c7f6848ae78d4d3c6eeab9de94e54f1e61"}, "planned_duration_s": 30, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "COMPLETED.json", "state": "see_original_file", "runs": [], "reason": null}]`。
- 包内视频：`camera_2fps.mp4`；579172 bytes；SHA256 `7677a3fac17937d1d482594553d63ca1cdc9dfe6b2256214d79db02080b0e0cd`。

### ht_cycle_shutdown_smoke_2026-10-17

- 数据分片前缀：`legacy-ht_cycle_shutdown_smoke_2026-10-17-1e23e5775a1d`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_cycle_shutdown_smoke_2026-10-17.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_cycle_shutdown_smoke_2026-10-17.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "a8fdc8c7f6848ae78d4d3c6eeab9de94e54f1e61"}, "planned_duration_s": 120, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "COMPLETED.json", "state": "see_original_file", "runs": [], "reason": null}]`。
- 包内视频：`camera_2fps.mp4`；1403733 bytes；SHA256 `dd4a8daffc4bd923ea5073a618dba96ac73c59c573ccda4fbfcc7b93721911ff`。

### ht_direct_gazebo_shutdown_smoke4_2026-10-17

- 数据分片前缀：`legacy-ht_direct_gazebo_shutdown_smoke4_2026-10-17-c6c31266fb7a`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_direct_gazebo_shutdown_smoke4_2026-10-17.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_direct_gazebo_shutdown_smoke4_2026-10-17.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### ht_endurance_crossguide_2026-10-17_02-14-09

- 数据分片前缀：`legacy-ht_endurance_crossguide_2026-10-17_02-14-09-9fc29aa09fd9`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_endurance_crossguide_2026-10-17_02-14-09.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_endurance_crossguide_2026-10-17_02-14-09.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "bd0c2c24f7eac383a3d8120b312fa4eb499c3199"}, "planned_duration_s": 3600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "FAILURE.json", "state": "see_original_file", "runs": [], "reason": null}]`。
- 包内视频：`camera_2fps.mp4`；9783634 bytes；SHA256 `faa623da733ef2bebb82e43f459554ce1e7108b15b27883569808ae86f5cbc91`。
