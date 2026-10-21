# 阶段08：实际XYθ硬约束规划与分层历史高程

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261015-elevation-xytheta`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261015-elevation-xytheta)。
- 归档标签提交：[`8398f538450a21c4ee9d65d17193ee084eacee03`](https://github.com/CQULzz/HT_Explo/commit/8398f538450a21c4ee9d65d17193ee084eacee03)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

322ec85一次归档此前本地XYθ、历史高程工作及当日修复：引入Hybrid A*和独立执行器，修正坐标翻转、固定世界索引、分层高程和真实观测时间。

从odom位姿到目标视点规划前进/倒车/原地旋转路径；P≥0.5硬门槛、默认严格未知；全局历史高程裁局部窗口供HT推理。

## 验证与剩余问题

180秒实际HT控车仅行驶14.35米；对应窗口接收984帧、成功融合窗口983帧；225组地图时间戳一致。

运动连续性差、旧许可1.5秒超时导致大量停车，目标反复切换；仍有噪声/未知区，未完成探索或实车验证。10月12日只是本地实验日期，不是独立Git发布。

## 报告及版本证据

- [docs/XYTHETA_EXPERIMENT_2026-10-12.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/XYTHETA_EXPERIMENT_2026-10-12.md)
- [docs/HISTORICAL_ELEVATION_EXPERIMENT_2026-10-12.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/HISTORICAL_ELEVATION_EXPERIMENT_2026-10-12.md)
- [docs/ELEVATION_MAPPING_FIXES_2026-10-15.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/ELEVATION_MAPPING_FIXES_2026-10-15.md)
- [docs/results/ht_validation_2026-10-15/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_validation_2026-10-15/REPORT.md)
- 原版本总表记录的控制提交：`322ec85c728c5900d3e47f22b4c3c5a4e6bccc99`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/2026-10-12_10-01-43.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-01-43.json)
- [docs/experiments/legacy_archive/receipts/2026-10-12_10-02-28.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-02-28.json)
- [docs/experiments/legacy_archive/receipts/2026-10-12_10-04-20.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-04-20.json)
- [docs/experiments/legacy_archive/receipts/2026-10-12_10-05-50.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-05-50.json)
- [docs/experiments/legacy_archive/receipts/2026-10-12_10-08-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-08-15.json)
- [docs/experiments/legacy_archive/receipts/2026-10-12_10-10-47.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-10-47.json)
- [docs/experiments/legacy_archive/receipts/2026-10-12_13-36-02.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_13-36-02.json)
- [docs/experiments/legacy_archive/receipts/2026-10-12_13-36-45.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_13-36-45.json)
- [docs/experiments/legacy_archive/receipts/2026-10-13_13-33-11.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-13_13-33-11.json)
- [docs/experiments/legacy_archive/receipts/history_executor_2026-10-12_13-43-58.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/history_executor_2026-10-12_13-43-58.json)
- [docs/experiments/legacy_archive/receipts/history_export_2026-10-12_13-52-39.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/history_export_2026-10-12_13-52-39.json)
- [docs/experiments/legacy_archive/receipts/history_lookahead_2026-10-12_13-47-51.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/history_lookahead_2026-10-12_13-47-51.json)
- [docs/experiments/legacy_archive/receipts/ht_validation_final_2026-10-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_validation_final_2026-10-15.json)
- [docs/experiments/legacy_archive/receipts/noise_chain_2026-10-13_15-26-34.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/noise_chain_2026-10-13_15-26-34.json)
- [docs/experiments/legacy_archive/receipts/noise_source_analysis_2026-10-13.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/noise_source_analysis_2026-10-13.json)
- [docs/experiments/legacy_archive/receipts/noise_static_2026-10-13.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/noise_static_2026-10-13.json)
- [docs/experiments/legacy_archive/receipts/noise_static_dense_2026-10-13.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/noise_static_dense_2026-10-13.json)
- [docs/experiments/legacy_archive/receipts/noise_static_unit_resolution_2026-10-13.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/noise_static_unit_resolution_2026-10-13.json)
- [docs/experiments/legacy_archive/receipts/original_10min_replay_2026-10-13_16-58-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/original_10min_replay_2026-10-13_16-58-15.json)
- [docs/experiments/legacy_archive/receipts/pose_permission_fix_2026-10-13_16-21-50.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/pose_permission_fix_2026-10-13_16-21-50.json)
- [docs/experiments/legacy_archive/receipts/pose_permission_latest_map_2026-10-13_16-25-58.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/pose_permission_latest_map_2026-10-13_16-25-58.json)
- [docs/experiments/legacy_archive/receipts/realtime_fix_smoke_2026-10-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/realtime_fix_smoke_2026-10-15.json)
- [docs/experiments/legacy_archive/receipts/stop_ht_2026-10-12_14-00-05.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/stop_ht_2026-10-12_14-00-05.json)
- [docs/experiments/legacy_archive/receipts/surface_fix_live_2026-10-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/surface_fix_live_2026-10-15.json)
- [docs/experiments/legacy_archive/receipts/surface_fix_live_reliable_isolated_2026-10-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/surface_fix_live_reliable_isolated_2026-10-15.json)
- [docs/experiments/legacy_archive/receipts/upstream_replay_scan_tf_smoke_2026-10-13.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/upstream_replay_scan_tf_smoke_2026-10-13.json)
- [docs/experiments/legacy_archive/receipts/upstream_replay_scan_tf_verified_2026-10-13.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/upstream_replay_scan_tf_verified_2026-10-13.json)
- [docs/experiments/legacy_archive/receipts/upstream_replay_smoke_2026-10-13.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/upstream_replay_smoke_2026-10-13.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### 2026-10-12_10-01-43

- 数据分片前缀：`legacy-2026-10-12_10-01-43-60862731f5ae`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-01-43.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/2026-10-12_10-01-43.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 10, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[{"path": "FAILURE.json", "state": "see_original_file", "runs": [], "reason": null}]`。

### 2026-10-12_10-02-28

- 数据分片前缀：`legacy-2026-10-12_10-02-28-b9d1ef653ada`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-02-28.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/2026-10-12_10-02-28.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 10, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[{"path": "FAILURE.json", "state": "see_original_file", "runs": [], "reason": null}]`。

### 2026-10-12_10-04-20

- 数据分片前缀：`legacy-2026-10-12_10-04-20-a6333e6f95e9`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-04-20.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/2026-10-12_10-04-20.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 10, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。

### 2026-10-12_10-05-50

- 数据分片前缀：`legacy-2026-10-12_10-05-50-754f2de48a15`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-05-50.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/2026-10-12_10-05-50.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 10, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[{"path": "FAILURE.json", "state": "see_original_file", "runs": [], "reason": null}]`。

### 2026-10-12_10-08-15

- 数据分片前缀：`legacy-2026-10-12_10-08-15-872d638e316f`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-08-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/2026-10-12_10-08-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 10, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。

### 2026-10-12_10-10-47

- 数据分片前缀：`legacy-2026-10-12_10-10-47-d073087872d9`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_10-10-47.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/2026-10-12_10-10-47.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 180, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。

### 2026-10-12_13-36-02

- 数据分片前缀：`legacy-2026-10-12_13-36-02-55a6f0ac762a`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_13-36-02.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/2026-10-12_13-36-02.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 90, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[{"path": "FAILURE.json", "state": "see_original_file", "runs": [], "reason": null}]`。

### 2026-10-12_13-36-45

- 数据分片前缀：`legacy-2026-10-12_13-36-45-03cbca571f89`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-12_13-36-45.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/2026-10-12_13-36-45.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 90, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。

### 2026-10-13_13-33-11

- 数据分片前缀：`legacy-2026-10-13_13-33-11-7ccccb15f40a`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/2026-10-13_13-33-11.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/2026-10-13_13-33-11.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 180, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。

### history_executor_2026-10-12_13-43-58

- 数据分片前缀：`legacy-history_executor_2026-10-12_13-43-58-192f2cc4b44e`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/history_executor_2026-10-12_13-43-58.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/history_executor_2026-10-12_13-43-58.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### history_export_2026-10-12_13-52-39

- 数据分片前缀：`legacy-history_export_2026-10-12_13-52-39-94bdb4696142`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/history_export_2026-10-12_13-52-39.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/history_export_2026-10-12_13-52-39.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### history_lookahead_2026-10-12_13-47-51

- 数据分片前缀：`legacy-history_lookahead_2026-10-12_13-47-51-dc9d066cc3de`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/history_lookahead_2026-10-12_13-47-51.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/history_lookahead_2026-10-12_13-47-51.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### ht_validation_final_2026-10-15

- 数据分片前缀：`legacy-ht_validation_final_2026-10-15-5d215d5eab98`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_validation_final_2026-10-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_validation_final_2026-10-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 180, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。
- 包内视频：`visuals/current_ht_exploration.mp4`；74353316 bytes；SHA256 `1f75ecee22f421ab7c1e388f0fd90aa6f5b2a33390d87a71301511bae169408b`。

### noise_chain_2026-10-13_15-26-34

- 数据分片前缀：`legacy-noise_chain_2026-10-13_15-26-34-9bbc69c9cb74`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/noise_chain_2026-10-13_15-26-34.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/noise_chain_2026-10-13_15-26-34.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### noise_source_analysis_2026-10-13

- 数据分片前缀：`legacy-noise_source_analysis_2026-10-13-34eb54618923`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/noise_source_analysis_2026-10-13.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/noise_source_analysis_2026-10-13.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### noise_static_2026-10-13

- 数据分片前缀：`legacy-noise_static_2026-10-13-c72eccf282b2`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/noise_static_2026-10-13.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/noise_static_2026-10-13.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### noise_static_dense_2026-10-13

- 数据分片前缀：`legacy-noise_static_dense_2026-10-13-6c690c932c4d`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/noise_static_dense_2026-10-13.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/noise_static_dense_2026-10-13.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### noise_static_unit_resolution_2026-10-13

- 数据分片前缀：`legacy-noise_static_unit_resolution_2026-10-13-6aa837a9a79d`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/noise_static_unit_resolution_2026-10-13.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/noise_static_unit_resolution_2026-10-13.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### original_10min_replay_2026-10-13_16-58-15

- 数据分片前缀：`legacy-original_10min_replay_2026-10-13_16-58-15-6481d2b90b22`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/original_10min_replay_2026-10-13_16-58-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/original_10min_replay_2026-10-13_16-58-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"baseline_revision": "b6760adb4280b379567c76f4e684ce628e28ef71"}, "planned_duration_s": 600, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。
- 包内视频：`replay_complete/visuals/original_tare_cupy_ht_sync.mp4`；136016860 bytes；SHA256 `350acd5658f919b0f91a0615e70ec7ca80c3cc7e20e0ee394176172c4e92953e`。
- 包内视频：`replay_corrected/visuals/original_tare_cupy_ht_sync.mp4`；146468297 bytes；SHA256 `3bd796d4a430f3fb832b7dbee9d88b2b19d879f23f5a917aeadefe78c1c086e1`。
- 包内视频：`replay_surface_fix_verified_2026-10-15/visuals/original_tare_cupy_ht_sync.mp4`；260819824 bytes；SHA256 `3b25a7f182651af3c0a9741f064138f7b258be74f86d57b389e6f372eeb8be5d`。

### pose_permission_fix_2026-10-13_16-21-50

- 数据分片前缀：`legacy-pose_permission_fix_2026-10-13_16-21-50-ff7a2ea7290c`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/pose_permission_fix_2026-10-13_16-21-50.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/pose_permission_fix_2026-10-13_16-21-50.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### pose_permission_latest_map_2026-10-13_16-25-58

- 数据分片前缀：`legacy-pose_permission_latest_map_2026-10-13_16-25-58-2561f0fa6c24`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/pose_permission_latest_map_2026-10-13_16-25-58.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/pose_permission_latest_map_2026-10-13_16-25-58.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### realtime_fix_smoke_2026-10-15

- 数据分片前缀：`legacy-realtime_fix_smoke_2026-10-15-701af2a9db13`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/realtime_fix_smoke_2026-10-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/realtime_fix_smoke_2026-10-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 45, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。

### stop_ht_2026-10-12_14-00-05

- 数据分片前缀：`legacy-stop_ht_2026-10-12_14-00-05-3691b7f5c95e`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/stop_ht_2026-10-12_14-00-05.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/stop_ht_2026-10-12_14-00-05.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### surface_fix_live_2026-10-15

- 数据分片前缀：`legacy-surface_fix_live_2026-10-15-2ba802339659`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/surface_fix_live_2026-10-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/surface_fix_live_2026-10-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 90, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。

### surface_fix_live_reliable_isolated_2026-10-15

- 数据分片前缀：`legacy-surface_fix_live_reliable_isolated_2026-10-15-ddc185f2a07c`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/surface_fix_live_reliable_isolated_2026-10-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/surface_fix_live_reliable_isolated_2026-10-15.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 90, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。

### upstream_replay_scan_tf_smoke_2026-10-13

- 数据分片前缀：`legacy-upstream_replay_scan_tf_smoke_2026-10-13-0ce41d04283e`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/upstream_replay_scan_tf_smoke_2026-10-13.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/upstream_replay_scan_tf_smoke_2026-10-13.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### upstream_replay_scan_tf_verified_2026-10-13

- 数据分片前缀：`legacy-upstream_replay_scan_tf_verified_2026-10-13-9d9e6545dbf2`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/upstream_replay_scan_tf_verified_2026-10-13.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/upstream_replay_scan_tf_verified_2026-10-13.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。
- 包内视频：`visuals/original_tare_cupy_ht_sync.mp4`；1176049 bytes；SHA256 `fe096f9f13d529ec65b0f355d481af712d045e268766ebb5ad14c7477817ed6d`。

### upstream_replay_smoke_2026-10-13

- 数据分片前缀：`legacy-upstream_replay_smoke_2026-10-13-1995dace135b`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/upstream_replay_smoke_2026-10-13.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/upstream_replay_smoke_2026-10-13.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {}, "planned_duration_s": 8, "working_tree_patch_preserved": false}]`。
- 原状态证据：`[]`。
- 包内视频：`visuals/original_tare_cupy_ht_sync.mp4`；1466861 bytes；SHA256 `e082f064218b2d0f370c3ce88a683ab5720a3d26a774da867c52709689766d4b`。
