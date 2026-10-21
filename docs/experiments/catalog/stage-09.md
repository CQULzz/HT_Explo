# 阶段09：目标保持与执行器独立校验

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261015-goal-continuity`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261015-goal-continuity)。
- 归档标签提交：[`dbce623161087fcaac865b1d4db5305d1cfe2c9c`](https://github.com/CQULzz/HT_Explo/commit/dbce623161087fcaac865b1d4db5305d1cfe2c9c)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-goal-continuity)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

按世界位置保持目标、停滞冷却、稳定全局引导、候选预筛和侧向恢复；跟踪器独立读取新鲜HT图校验路径。

减少目标尚未完成时反向切换；HT启用时旧Bool许可年龄不再单独触发停车，地图/扫描/定位/路径时效和显式禁止仍有效。

## 验证与剩余问题

一轮180秒56.54米，目标方向反转9→0；149项核心、13项HT ROS和4项跟踪器检查通过。

同代码后续复跑29.76米、102秒后长期停车，故不能把这次56.54米视为稳定通过。仍有规划/执行采样不一致。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/xytheta_execution_continuity.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/xytheta_execution_continuity.md)
- [docs/results/ht_continuity_2026-10-15/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_continuity_2026-10-15/REPORT.md)
- [docs/results/ht_repeat_2026-10-15/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_repeat_2026-10-15/REPORT.md)
- 原版本总表记录的控制提交：`dbce623161087fcaac865b1d4db5305d1cfe2c9c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_continuity_candidates_2026-10-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_continuity_candidates_2026-10-15.json)
- [docs/experiments/legacy_archive/receipts/ht_continuity_escape_2026-10-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_continuity_escape_2026-10-15.json)
- [docs/experiments/legacy_archive/receipts/ht_continuity_final_2026-10-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_continuity_final_2026-10-15.json)
- [docs/experiments/legacy_archive/receipts/ht_target_continuity_2026-10-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_target_continuity_2026-10-15.json)
- [docs/experiments/legacy_archive/receipts/ht_target_continuity_verified_2026-10-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_target_continuity_verified_2026-10-15.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_continuity_candidates_2026-10-15

- 数据分片前缀：`legacy-ht_continuity_candidates_2026-10-15-9146d7827481`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_continuity_candidates_2026-10-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_continuity_candidates_2026-10-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "8398f538450a21c4ee9d65d17193ee084eacee03"}, "planned_duration_s": 180, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "ABORTED.md", "state": "ABORTED", "text": "本轮主动中止，记录末样本为122.001秒：候选终点HT预检查生效，但直线推进约束使侧向绕行候选被排除，车辆约8.51m后停止。增加受同样硬约束的侧向恢复搜索后另开输出目录。\n"}]`。

### ht_continuity_escape_2026-10-15

- 数据分片前缀：`legacy-ht_continuity_escape_2026-10-15-4f556a31eb5e`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_continuity_escape_2026-10-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_continuity_escape_2026-10-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "8398f538450a21c4ee9d65d17193ee084eacee03"}, "planned_duration_s": 180, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[]`。
- 包内视频：`visuals/current_ht_exploration.mp4`；81190371 bytes；SHA256 `4a68a1a8771554e72f49f966a92d349266af9f4d5be8d47d6188bea8b7a0ab19`。

### ht_continuity_final_2026-10-15

- 数据分片前缀：`legacy-ht_continuity_final_2026-10-15-3ed39cf33caa`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_continuity_final_2026-10-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_continuity_final_2026-10-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "8398f538450a21c4ee9d65d17193ee084eacee03"}, "planned_duration_s": 180, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[]`。
- 包内视频：`visuals/current_ht_exploration.mp4`；67564773 bytes；SHA256 `20c23d662f5ea395447ea7fdec0ace2fbbea7fc50275cf826df3a7f3d70ba8ed`。

### ht_target_continuity_2026-10-15

- 数据分片前缀：`legacy-ht_target_continuity_2026-10-15-9937c4a8a0d5`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_target_continuity_2026-10-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_target_continuity_2026-10-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 180, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[{"path": "ABORTED.md", "state": "ABORTED", "text": "本轮在启动阶段主动中止：TARE尚未生成全局路线，第一版目标保持逻辑未提供局部边界引导，导致候选为空、未起步。已修正启动边界情况，后续验证使用独立输出目录，未覆盖本轮日志。\n"}]`。

### ht_target_continuity_verified_2026-10-15

- 数据分片前缀：`legacy-ht_target_continuity_verified_2026-10-15-d67600d6c799`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_target_continuity_verified_2026-10-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_target_continuity_verified_2026-10-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "8398f538450a21c4ee9d65d17193ee084eacee03"}, "planned_duration_s": 180, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "ABORTED.md", "state": "ABORTED", "text": "本轮启动回归主动中止：不仅全局路线为空，导航边界也尚未建立；原版引导来源实际是覆盖选择集合中的远视点。补充从这些视点初始化世界坐标引导。完整仿真另建目录，未覆盖本轮日志。\n"}]`。
