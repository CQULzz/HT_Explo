# 阶段20：观测支撑与停滞恢复：返航通过，探索仍有退步

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261017-context-recovery`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-context-recovery)。
- 归档标签提交：[`dee873db9a25778eb67060100025bea2f619c0ee`](https://github.com/CQULzz/HT_Explo/commit/dee873db9a25778eb67060100025bea2f619c0ee)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-context-recovery)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

区分网络上下文与车体观测支撑；按实际观测时间保留拒绝，有限坏高度仅作八方向禁行上下文；增加12秒原地停滞释放、有限回退和0.35秒共享搜索预算，CPU改4线程channels-last。

避免网络缺测重复膨胀及旧方差反复否定历史；保留HT硬阈值、真实未知和碰撞检查，支持安全回退及实际返航。

## 验证与剩余问题

311核心、17ROS、6跟踪及53Python回归通过；隧道/室内各600秒、两段15fps视频完整解码及各13项采集核验通过。均COMPLETED；等长前缀最长全零指令145.95→4.30秒、39.80→4.65秒；室内规划P95 1.576→1.004秒。

室内约215秒触发返航，总近似观测1900.250→1106.750m³（下降41.8%）；任务收尾不是全覆盖证明。室内HT年龄最大5.01秒，两场景各8个1Hz样本超过3秒。森林约4Hz本轮未重测，其他三场景未重跑。保留约195秒失败诊断；每配置仅一次、无实车或长期稳定性验收。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/fixes/2026-10-17_context_recovery.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/fixes/2026-10-17_context_recovery.md)
- [docs/results/ht_recovery_comparison_2026-10-17/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_recovery_comparison_2026-10-17/REPORT.md)
- [docs/results/ht_recovery_10min_2026-10-17/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_recovery_10min_2026-10-17/REPORT.md)
- [docs/results/ht_context_diagnostics_2026-10-17/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_context_diagnostics_2026-10-17/REPORT.md)
- 原版本总表记录的控制提交：`73cae0b24e72575b8592e772fd818f85ab91a9a6`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_combined_admission_10min_2026-10-18_01-52-52.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_combined_admission_10min_2026-10-18_01-52-52.json)
- [docs/experiments/legacy_archive/receipts/ht_completion_diagnostic_2026-10-18_01-06-52.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_completion_diagnostic_2026-10-18_01-06-52.json)
- [docs/experiments/legacy_archive/receipts/ht_context_recovery_10min_2026-10-17_14-42-07.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_context_recovery_10min_2026-10-17_14-42-07.json)
- [docs/experiments/legacy_archive/receipts/ht_heading_reserve_10min_2026-10-18_01-47-41.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_heading_reserve_10min_2026-10-18_01-47-41.json)
- [docs/experiments/legacy_archive/receipts/ht_recovery_verified_10min_2026-10-17_14-55-03.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_recovery_verified_10min_2026-10-17_14-55-03.json)
- [docs/experiments/legacy_archive/receipts/ht_recovery_verified_10min_2026-10-17_14-55-26.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_recovery_verified_10min_2026-10-17_14-55-26.json)
- [docs/experiments/legacy_archive/receipts/ht_reversible_motion_10min_2026-10-18_01-26-31.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_reversible_motion_10min_2026-10-18_01-26-31.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_combined_admission_10min_2026-10-18_01-52-52

- 数据分片前缀：`legacy-ht_combined_admission_10min_2026-10-18_01-52-52-00014a2f02d8`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_combined_admission_10min_2026-10-18_01-52-52.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_combined_admission_10min_2026-10-18_01-52-52.json)。
- 原测量源码记录：`[{"path": "indoor/manifest.json", "recorded_commits": {"git_head": "77cd87cef62bccc35949deef40dd2c156ef3d112"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}, {"path": "tunnel/manifest.json", "recorded_commits": {"git_head": "77cd87cef62bccc35949deef40dd2c156ef3d112"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "suite.json", "state": "DIAGNOSTIC_STOPPED", "runs": [{"scenario": "indoor", "state": "RECORDED", "elapsed_measurement_s": 600}, {"scenario": "tunnel", "state": "FAILED", "elapsed_measurement_s": 314.5}], "reason": "Confirmed late HT rejection publishes nonzero candidate Twist. Preserve completed600s indoor; tunnel interrupted after314.5s, not a600s trial. Stop before correcting controller and re-testing."}, {"path": "DIAGNOSTIC_STOP_REASON.json", "state": "see_original_file", "runs": [], "reason": "Confirmed late HT rejection publishes nonzero candidate Twist. Preserve completed600s indoor; tunnel interrupted after314.5s, not a600s trial. Stop before correcting controller and re-testing."}]`。
- 包内视频：`indoor/camera_15fps.mp4`；44158232 bytes；SHA256 `38f6a35b2022f7084318b3e04ca6810d7cf07ef866a4fa01ca77bcc7aa61ed79`。
- 包内视频：`indoor/camera_h264.mp4`；10371501 bytes；SHA256 `2627eef0b2d6dc989d05126a2d7aa08dedd15a6d2af757f8f5af1c3dff544823`。
- 包内视频：`tunnel/camera_15fps.mp4`；24760820 bytes；SHA256 `adb5744f51370009351150c04a2f11b791388400e84a5e2a5aaada9ee5015ac6`。

### ht_completion_diagnostic_2026-10-18_01-06-52

- 数据分片前缀：`legacy-ht_completion_diagnostic_2026-10-18_01-06-52-01fe8da2d70f`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_completion_diagnostic_2026-10-18_01-06-52.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_completion_diagnostic_2026-10-18_01-06-52.json)。
- 原测量源码记录：`[{"path": "indoor/manifest.json", "recorded_commits": {"git_head": "9fec0375f8caec2b07a7c0c268f197e1800f5fab"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "suite.json", "state": "COMPLETED", "runs": [{"scenario": "indoor", "state": "RECORDED", "elapsed_measurement_s": 599.5}], "reason": null}]`。
- 包内视频：`indoor/camera_15fps.mp4`；36547407 bytes；SHA256 `a454808113aeac18771aef61c00c2e7d0bc8f55c1f8a83167222001e82e5bf0e`。
- 包内视频：`indoor/camera_h264.mp4`；6572431 bytes；SHA256 `08c39ffdc9942b608e57191adae4ee2be203cb7886ac9f9dad1d9a0b34695338`。

### ht_context_recovery_10min_2026-10-17_14-42-07

- 数据分片前缀：`legacy-ht_context_recovery_10min_2026-10-17_14-42-07-507d7a8ee98a`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_context_recovery_10min_2026-10-17_14-42-07.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_context_recovery_10min_2026-10-17_14-42-07.json)。
- 原测量源码记录：`[{"path": "tunnel/manifest.json", "recorded_commits": {"git_head": "73cae0b24e72575b8592e772fd818f85ab91a9a6"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "suite.json", "state": "DIAGNOSTIC_STOPPED", "runs": [{"scenario": "tunnel", "state": "FAILED", "elapsed_measurement_s": 194.9}, {"scenario": "indoor", "state": "PENDING"}], "reason": "Retained-source variance invalidation reproduced; partial diagnostic, not a 600s pass"}, {"path": "DIAGNOSTIC_STOP_REASON.json", "state": "see_original_file", "runs": [], "reason": "Reproduced retained-source variance invalidation without a new measurement; stop diagnostic attempt before correction, not a completed 600-second test"}]`。
- 包内视频：`tunnel/camera_15fps.mp4`；13891360 bytes；SHA256 `e42dd3c27fdc987d419fe7d4c3b32bf66e0132813d4cc1a77ff1f8cd20a58c3a`。

### ht_heading_reserve_10min_2026-10-18_01-47-41

- 数据分片前缀：`legacy-ht_heading_reserve_10min_2026-10-18_01-47-41-f2fe98d2f285`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_heading_reserve_10min_2026-10-18_01-47-41.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_heading_reserve_10min_2026-10-18_01-47-41.json)。
- 原测量源码记录：`[{"path": "indoor/manifest.json", "recorded_commits": {"git_head": "966f3ff1921be2eaeee3a4d7b40bf152abbecebc"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "suite.json", "state": "DIAGNOSTIC_STOPPED", "runs": [{"scenario": "indoor", "state": "FAILED", "elapsed_measurement_s": 192.3}, {"scenario": "tunnel", "state": "PENDING"}], "reason": "Heading reserve only still blocks without a retrace certificate; partial diagnosis, not600s test."}, {"path": "DIAGNOSTIC_STOP_REASON.json", "state": "see_original_file", "runs": [], "reason": "Heading reserve alone remains blocked with nominally valid current pose and forbidden reverse directions; preserve this partial diagnostic and test combined constraints. This is not a completed600s run."}]`。
- 包内视频：`indoor/camera_15fps.mp4`；11719551 bytes；SHA256 `0e57782baf4991824a6c5853a041c6ade55dd6b2572eb499b87409a63e2ea033`。

### ht_recovery_verified_10min_2026-10-17_14-55-03

- 数据分片前缀：`legacy-ht_recovery_verified_10min_2026-10-17_14-55-03-3227ad8844b7`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_recovery_verified_10min_2026-10-17_14-55-03.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_recovery_verified_10min_2026-10-17_14-55-03.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### ht_recovery_verified_10min_2026-10-17_14-55-26

- 数据分片前缀：`legacy-ht_recovery_verified_10min_2026-10-17_14-55-26-71125d7a908e`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_recovery_verified_10min_2026-10-17_14-55-26.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_recovery_verified_10min_2026-10-17_14-55-26.json)。
- 原测量源码记录：`[{"path": "indoor/manifest.json", "recorded_commits": {"git_head": "dee873db9a25778eb67060100025bea2f619c0ee"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}, {"path": "tunnel/manifest.json", "recorded_commits": {"git_head": "dee873db9a25778eb67060100025bea2f619c0ee"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "suite.json", "state": "COMPLETED", "runs": [{"scenario": "tunnel", "state": "RECORDED", "elapsed_measurement_s": 599.3}, {"scenario": "indoor", "state": "RECORDED", "elapsed_measurement_s": 599.7}], "reason": null}]`。
- 包内视频：`indoor/camera_15fps.mp4`；41641036 bytes；SHA256 `e286c9f5b4d86f476ceb564c74f39f86c3ddf212cdbcb2e61846e3e8d14d71e2`。
- 包内视频：`indoor/camera_h264.mp4`；8722146 bytes；SHA256 `83fef13a8cc56fa5f33a2484de8d4e5d6966d79dd5373e4961bd9409af7e5e2e`。
- 包内视频：`tunnel/camera_15fps.mp4`；40095187 bytes；SHA256 `f683c0b55eeadb6da5f7d43c550202b5c852a7a5a2e150e7c92e0c34d5212fe7`。
- 包内视频：`tunnel/camera_h264.mp4`；4757621 bytes；SHA256 `ee7c4ec921bb0550bec21615183ea2a3eb9b54fbb2c23830bc4095be079768b7`。

### ht_reversible_motion_10min_2026-10-18_01-26-31

- 数据分片前缀：`legacy-ht_reversible_motion_10min_2026-10-18_01-26-31-08cff2aceafa`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_reversible_motion_10min_2026-10-18_01-26-31.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_reversible_motion_10min_2026-10-18_01-26-31.json)。
- 原测量源码记录：`[{"path": "indoor/manifest.json", "recorded_commits": {"git_head": "fde37365232f8af219488cafd7d1d6e9f6bf73d8"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}, {"path": "tunnel/manifest.json", "recorded_commits": {"git_head": "fde37365232f8af219488cafd7d1d6e9f6bf73d8"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "suite.json", "state": "DIAGNOSTIC_STOPPED", "runs": [{"scenario": "indoor", "state": "RECORDED", "elapsed_measurement_s": 600}, {"scenario": "tunnel", "state": "FAILED", "elapsed_measurement_s": 121.1}], "reason": "Indoor completed600s but candidate failed; partial tunnel interrupted for evidence-based revision"}, {"path": "DIAGNOSTIC_STOP_REASON.json", "state": "see_original_file", "runs": [], "reason": "Completed600s indoor candidate failed with captured heading-boundary admissibility crossing; stop remaining trial to refine the failed candidate. Indoor is complete; tunnel partial is not a600s result."}]`。
- 包内视频：`indoor/camera_15fps.mp4`；33130273 bytes；SHA256 `f6899eef9e77adcaa65303b1b79430556c35e9bcc26c14b1df6fdf79595a7c59`。
- 包内视频：`indoor/camera_h264.mp4`；4106201 bytes；SHA256 `e17177716dbc96b3145b3b25ff60cdc09f2eb66d9f7e64fe9b9dfc5ea1401ca3`。
- 包内视频：`tunnel/camera_15fps.mp4`；11797599 bytes；SHA256 `e7f0a082d3bdcf338304fd5d325a96505138e58f16bf447c3ff6477933ef28f1`。
