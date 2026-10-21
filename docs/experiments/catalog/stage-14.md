# 阶段14：全局停滞恢复与返航容差修正

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261016-progress-memory`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261016-progress-memory)。
- 归档标签提交：[`9393e7da7d1eeabf04a4325593834304f236e405`](https://github.com/CQULzz/HT_Explo/commit/9393e7da7d1eeabf04a4325593834304f236e405)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-progress-memory)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

全局引导独立进展计时、180秒失败冷却、世界坐标重复访问记忆；修正恢复评分、返航检查点到达容差及无用探索搜索。

局部目标完成不再掩盖全局停滞；零收益主目标不能压住所有恢复候选；保留HT硬门槛、严格未知和速度上限。

## 验证与剩余问题

242项核心、15项ROS和5项跟踪测试通过。两轮20/25分钟；最新同期20分钟估计观测6498m³，对照3293.875m³；第10–20分钟增益1654.125m³，对照26.375m³。25分钟447.50米、294格，最终EXPLORING。

第一轮返航BLOCKED；补容差回归后，25分钟轮未触发返航。后续阶段15的60分钟记录验证了一次返回完成，但活动期仍有低增益回访、短时地图过期和关停清理报错；无实车或真值全覆盖验收。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/results/ht_progress_fix_2026-10-16/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_progress_fix_2026-10-16/REPORT.md)
- [docs/results/ht_progress_fix_2026-10-16/same_duration_metrics.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_progress_fix_2026-10-16/same_duration_metrics.json)
- [docs/results/ht_progress_fix_2026-10-16/return_fix_trial/validation_checks.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_progress_fix_2026-10-16/return_fix_trial/validation_checks.json)
- 原版本总表记录的控制提交：`c85ad1f004bbaceae14cd65351be38c3a9e61273`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_guide_fix_2026-10-16_22-53-33.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_guide_fix_2026-10-16_22-53-33.json)
- [docs/experiments/legacy_archive/receipts/ht_progress_return_fix_2026-10-16_23-20-58.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_progress_return_fix_2026-10-16_23-20-58.json)
- [docs/experiments/legacy_archive/receipts/ht_progress_return_fix_2026-10-16_23-23-20.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_progress_return_fix_2026-10-16_23-23-20.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_guide_fix_2026-10-16_22-53-33

- 数据分片前缀：`legacy-ht_guide_fix_2026-10-16_22-53-33-630c6e89580a`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_guide_fix_2026-10-16_22-53-33.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_guide_fix_2026-10-16_22-53-33.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "7f1c253feccb1b7ec4b4912f70312d7b308e3a20"}, "planned_duration_s": 1200, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "COMPLETED.json", "state": "see_original_file", "runs": [], "reason": null}]`。
- 包内视频：`camera_2fps.mp4`；11388956 bytes；SHA256 `2e46740c86ed73f216418c83d8308d2b0e0ebd0315180c314c8ef515810c3ee5`。
- 包内视频：`camera_h264.mp4`；6788047 bytes；SHA256 `8bfba2db4b359ec5f150f9baa805201051b541b48f90c097fb26e5c4f97190c6`。

### ht_progress_return_fix_2026-10-16_23-20-58

- 数据分片前缀：`legacy-ht_progress_return_fix_2026-10-16_23-20-58-1ac23c13d31a`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_progress_return_fix_2026-10-16_23-20-58.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_progress_return_fix_2026-10-16_23-20-58.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "c85ad1f004bbaceae14cd65351be38c3a9e61273"}, "planned_duration_s": 1500, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "FAILURE.json", "state": "see_original_file", "runs": [], "reason": null}]`。

### ht_progress_return_fix_2026-10-16_23-23-20

- 数据分片前缀：`legacy-ht_progress_return_fix_2026-10-16_23-23-20-4a6357c73099`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_progress_return_fix_2026-10-16_23-23-20.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_progress_return_fix_2026-10-16_23-23-20.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "c85ad1f004bbaceae14cd65351be38c3a9e61273"}, "planned_duration_s": 1500, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "COMPLETED.json", "state": "see_original_file", "runs": [], "reason": null}]`。
- 包内视频：`camera_2fps.mp4`；14443645 bytes；SHA256 `46a1e34568d1e4f3f837f70fbcc512f0f68918461d0eadc92cc890e6fe71e50c`。
- 包内视频：`camera_h264.mp4`；8443083 bytes；SHA256 `7abf020e02724ff04b26c948dfa4b1fad7aad40975aad23d7679f6bdf4bc59e5`。
