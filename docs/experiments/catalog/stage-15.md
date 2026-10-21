# 阶段15：60分钟复测：返回完成但仍有回访

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261017-endurance-return`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-endurance-return)。
- 归档标签提交：[`3fe5b9b5ee23c7a3cc8ec7a0243cdd2d09891a38`](https://github.com/CQULzz/HT_Explo/commit/3fe5b9b5ee23c7a3cc8ec7a0243cdd2d09891a38)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-endurance-return)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

对阶段14核心代码进行同Garage连续60分钟记录，补活动/等待分段控制、返航、低收益回访、地图时效及主动关停审计；不新增导航算法。

首次在本次最新规划代码的长测中观察到TARE触发返航并通过到家、低速和停稳条件，任务完成后保持停车；明确区分末尾正常等待与中途低收益回访。

## 验证与剩余问题

44分28秒左右COMPLETED，距记录起点0.291米；共768.57米、371个轨迹格、6513.750m³近似观测，对照旧60分钟为3296.375m³。7201个轨迹采样、72000条录包控制指令；14项哈希不变，视频完整解码通过。

活动约44.5分钟，余下15.5分钟为完成后等待，不是主动探索60分钟。中途7.38分钟行驶106.17米仅增2.125m³；地图年龄最高3.37秒，1Hz检查3次超过3秒。主动SIGINT后CMU部分节点关停异常；无运行期意外退出记录。单场景一轮、非真值全覆盖或实车证明。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/results/ht_endurance_progress_2026-10-17/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_endurance_progress_2026-10-17/REPORT.md)
- [docs/results/ht_endurance_progress_2026-10-17/validation_checks.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_endurance_progress_2026-10-17/validation_checks.json)
- [docs/results/ht_endurance_progress_2026-10-17/return_search_audit.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_endurance_progress_2026-10-17/return_search_audit.json)
- [docs/results/ht_endurance_progress_2026-10-17/shutdown_event_audit.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_endurance_progress_2026-10-17/shutdown_event_audit.json)
- 原版本总表记录的控制提交：`c85ad1f004bbaceae14cd65351be38c3a9e61273`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_endurance_progress_2026-10-17_00-39-55.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_endurance_progress_2026-10-17_00-39-55.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_endurance_progress_2026-10-17_00-39-55

- 数据分片前缀：`legacy-ht_endurance_progress_2026-10-17_00-39-55-4ae0e7291382`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_endurance_progress_2026-10-17_00-39-55.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_endurance_progress_2026-10-17_00-39-55.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "0a2d5440021117da39ee21abe9b89fba02250c4e"}, "planned_duration_s": 3600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "COMPLETED.json", "state": "see_original_file", "runs": [], "reason": null}]`。
- 包内视频：`camera_2fps.mp4`；30921390 bytes；SHA256 `f83cdfc81482afeadf2dbe6828e5df11ecf1c5efe06e2de5621140a90db95eed`。
- 包内视频：`camera_h264.mp4`；16172041 bytes；SHA256 `19c64184c8f9c54020918c32256327633452259960172447ee1cb4aeabc73b16`。
