# 阶段11：统一运动段检查与执行拒绝反馈

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261016-swept-check`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261016-swept-check)。
- 归档标签提交：[`919d826f340c11e34421a738e80d2a2e85066eb9`](https://github.com/CQULzz/HT_Explo/commit/919d826f340c11e34421a738e80d2a2e85066eb9)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-swept-check)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

3912e37使规划、发布前和执行共用motionSupport及经过栅格检查；拒绝边反馈、6秒冷却重规划；后续提交补两轮视频/统计。

消除已复现的规划通过/执行拒绝循环；检查车头变化、倒车方向和前约1米路径；不放宽HT门槛或未知策略。

## 验证与剩余问题

冻结原停车地图：旧路一致拒绝、重规划41姿态；155项核心、15项HT ROS、5项跟踪器检查通过。两轮180秒57.87/63.45米，最长完全零速1.65/1.50秒。

只解决特定持续拒绝循环；仍有转向、回访与短暂停顿，短测不保证全局探索完成；最新长测进一步证实长期推进不足。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/results/ht_swept_gate_2026-10-16/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_swept_gate_2026-10-16/REPORT.md)
- 原版本总表记录的控制提交：`3912e37df7541799c354bf568ff8f3d5b0383aab`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_swept_gate_2026-10-16.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_swept_gate_2026-10-16.json)
- [docs/experiments/legacy_archive/receipts/ht_swept_gate_repeat_2026-10-16.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_swept_gate_repeat_2026-10-16.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_swept_gate_2026-10-16

- 数据分片前缀：`legacy-ht_swept_gate_2026-10-16-c9e424786497`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_swept_gate_2026-10-16.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_swept_gate_2026-10-16.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "697ae2e82859f0381ee6455d39617159eb97295a", "tested_code_commit": "3912e37df7541799c354bf568ff8f3d5b0383aab"}, "planned_duration_s": 180, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[]`。
- 包内视频：`publish/garage_ht_fixed_180s.mp4`；49522478 bytes；SHA256 `da1836e698a4af1b705e0b7b50770ab2803802d91992107798fa69ddc3ba638c`。
- 包内视频：`visuals/current_ht_exploration.mp4`；89115257 bytes；SHA256 `ff5ca07de5229a82d585f6d10e1c7f6e702700d108bac01258e72949fb67e7cd`。

### ht_swept_gate_repeat_2026-10-16

- 数据分片前缀：`legacy-ht_swept_gate_repeat_2026-10-16-9ccee559b2f5`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_swept_gate_repeat_2026-10-16.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_swept_gate_repeat_2026-10-16.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "3912e37df7541799c354bf568ff8f3d5b0383aab"}, "planned_duration_s": 180, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[]`。
- 包内视频：`visuals/current_ht_exploration.mp4`；81861967 bytes；SHA256 `ee27177f2de71ac345d3f2c9f3fff4ecca2129b80b7e9a82c71f04998c718d23`。
