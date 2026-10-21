# 阶段19：室内视点细化：恢复推进，仍有停顿回访

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261017-indoor-viewpoints`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-indoor-viewpoints)。
- 归档标签提交：[`f3d1eeedae814f99d0db94673c7abadc8eaf7439`](https://github.com/CQULzz/HT_Explo/commit/f3d1eeedae814f99d0db94673c7abadc8eaf7439)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-indoor-viewpoints)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

室内视点从50×50、0.6m改为100×100、0.3m，保持30×30m范围；原HT分辨率、概率阈值、足迹半径、运动学搜索和控制速度不变。

为窄HT支撑带提供候选端点，保留原参数失败视频；新增实际栅格、足迹硬门槛、时间戳与配置归档。

## 验证与剩余问题

独立600秒补测、9000帧完整解码及13项采集/进程核验通过。里程3.11→145.28m，近似观测347.875→1900.25m³，全零指令98.2%→23.0%；运行中实际参数读取与源哈希证明仅室内视点配置不同。

仍有最长39.80秒停车和2.3%倒车；第6至7.5分钟行驶22.94m仅增8.375m³，低收益回访未消失。活跃搜索耗时P95为1.576秒、HT年龄最大4.67秒。隧道返航未知足迹问题未解决；每配置一次，不能视为所有场景通过。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/results/ht_indoor_sampling_comparison_2026-10-17/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_indoor_sampling_comparison_2026-10-17/REPORT.md)
- [docs/results/ht_indoor_viewpoint_10min_2026-10-17/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_indoor_viewpoint_10min_2026-10-17/REPORT.md)
- [docs/results/ht_multiscene_10min_2026-10-17/indoor/diagnostics/README.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_multiscene_10min_2026-10-17/indoor/diagnostics/README.md)
- 原版本总表记录的控制提交：`f1c84854ccc147d40d7f9120c9713ba5e11c736c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_indoor_dense_10min_2026-10-17_12-38-24.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_indoor_dense_10min_2026-10-17_12-38-24.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_indoor_dense_10min_2026-10-17_12-38-24

- 数据分片前缀：`legacy-ht_indoor_dense_10min_2026-10-17_12-38-24-bc5da6325e75`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_indoor_dense_10min_2026-10-17_12-38-24.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_indoor_dense_10min_2026-10-17_12-38-24.json)。
- 原测量源码记录：`[{"path": "indoor/manifest.json", "recorded_commits": {"git_head": "f3d1eeedae814f99d0db94673c7abadc8eaf7439"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "suite.json", "state": "COMPLETED", "runs": [{"scenario": "indoor", "state": "RECORDED", "elapsed_measurement_s": 599.2}], "reason": null}]`。
- 包内视频：`indoor/camera_15fps.mp4`；47154472 bytes；SHA256 `421bbe2cf3d382b67565523e82aa0dfa1ccf9554e6d0bd421143dd397265af84`。
- 包内视频：`indoor/camera_h264.mp4`；12780689 bytes；SHA256 `09d5a364e32bf653cdb15a85a43f15bdddadd62381eb7dca15136f8e2f8216d0`。
