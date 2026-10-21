# 阶段21：拦截命令归零与32航向：修正缺陷，仍有停滞

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261018-zero-hold`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-zero-hold)。
- 归档标签提交：[`67ade71c10caa8a8923b9fe9c663d10a9ec75568`](https://github.com/CQULzz/HT_Explo/commit/67ade71c10caa8a8923b9fe9c663d10a9ec75568)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-zero-hold)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

停车函数清空实际待发Twist全部六个分量；搜索16改32航向；按绝对源秒评估采样包，防止重复分秒丢帧；增加完成队列和全频HT证据记录。

HT晚拒绝真正发零速度，保留原硬门槛；同一真实快照上32航向找到16漏掉的HT路线；区分完成、无路、地图时效与评估误差。

## 验证与剩余问题

旧晚拒绝回归失败、新实现通过；384核心、21ROS、8跟踪回归通过，4个真实快照均参与。最终室内/隧道各600秒、各13项采集核验及完整解码通过，19次晚拒绝均发零。室内6.64m/432.875m³仍BLOCKED；隧道79.00m/621.375m³约230.53秒返航完成。

室内29.967秒同一世界位姿，中心HT概率仍约0.999846，8个此前神经预测无效但物理已观测的邻格变成有效低概率，进入足迹硬门槛后拒绝起点。该接口仍未修改，不能直接判定噪声、模型错误或重复膨胀；32航向不是闭环稳定性通过。原215秒收尾未复现、完成条件未改；无实车或更长验收。

## 报告及版本证据

- [docs/fixes/2026-10-18_late_hold_zero_twist.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/fixes/2026-10-18_late_hold_zero_twist.md)
- [docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)
- [docs/results/ht_zero_twist_only_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_zero_twist_only_10min_2026-10-18/REPORT.md)
- [docs/results/ht_zero_twist_fine_heading_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_zero_twist_fine_heading_10min_2026-10-18/REPORT.md)
- 原版本总表记录的控制提交：`8e8d2b768a2e8e347ba4de315df1c68c9079c8ad`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_zero_twist_fine_heading_10min_2026-10-18_02-28-07.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_zero_twist_fine_heading_10min_2026-10-18_02-28-07.json)
- [docs/experiments/legacy_archive/receipts/ht_zero_twist_verified_10min_2026-10-18_02-13-23.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_zero_twist_verified_10min_2026-10-18_02-13-23.json)
- [docs/experiments/legacy_archive/receipts/ht_zero_twist_verified_10min_2026-10-18_02-15-15.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_zero_twist_verified_10min_2026-10-18_02-15-15.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_zero_twist_fine_heading_10min_2026-10-18_02-28-07

- 数据分片前缀：`legacy-ht_zero_twist_fine_heading_10min_2026-10-18_02-28-07-8bf856929ce9`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_zero_twist_fine_heading_10min_2026-10-18_02-28-07.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_zero_twist_fine_heading_10min_2026-10-18_02-28-07.json)。
- 原测量源码记录：`[{"path": "indoor/manifest.json", "recorded_commits": {"git_head": "67ade71c10caa8a8923b9fe9c663d10a9ec75568"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}, {"path": "tunnel/manifest.json", "recorded_commits": {"git_head": "67ade71c10caa8a8923b9fe9c663d10a9ec75568"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "suite.json", "state": "COMPLETED", "runs": [{"scenario": "indoor", "state": "RECORDED", "elapsed_measurement_s": 600}, {"scenario": "tunnel", "state": "RECORDED", "elapsed_measurement_s": 599.0}], "reason": null}]`。
- 包内视频：`indoor/camera_15fps.mp4`；30884698 bytes；SHA256 `94b32a4a2ed1c2816b71b954125d33471c921d953ba09f54f2d3cacc1dadabc1`。
- 包内视频：`indoor/camera_h264.mp4`；2890689 bytes；SHA256 `e2f5818ef0a1ff9b682b5fe0ba39e27b551fa389048c08f1baa27204d9d2043e`。
- 包内视频：`tunnel/camera_15fps.mp4`；37935042 bytes；SHA256 `aba554130438d13fc233d9149f6f6ebf734b63c801bf957eebf34216560f8e64`。
- 包内视频：`tunnel/camera_h264.mp4`；4200418 bytes；SHA256 `dddf4177ca0f3f5915c0dbbd728b03ad333758c6b674fc02295637fb41e88a2c`。

### ht_zero_twist_verified_10min_2026-10-18_02-13-23

- 数据分片前缀：`legacy-ht_zero_twist_verified_10min_2026-10-18_02-13-23-945969142b1f`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_zero_twist_verified_10min_2026-10-18_02-13-23.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_zero_twist_verified_10min_2026-10-18_02-13-23.json)。
- 原测量源码记录：`[]`。
- 原状态证据：`[]`。

### ht_zero_twist_verified_10min_2026-10-18_02-15-15

- 数据分片前缀：`legacy-ht_zero_twist_verified_10min_2026-10-18_02-15-15-d396d8641816`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_zero_twist_verified_10min_2026-10-18_02-15-15.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_zero_twist_verified_10min_2026-10-18_02-15-15.json)。
- 原测量源码记录：`[{"path": "indoor/manifest.json", "recorded_commits": {"git_head": "37f0d42f75220a7098baf2167da61bf38e47fa59"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}, {"path": "tunnel/manifest.json", "recorded_commits": {"git_head": "37f0d42f75220a7098baf2167da61bf38e47fa59"}, "planned_duration_s": 600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "suite.json", "state": "DIAGNOSTIC_STOPPED", "runs": [{"scenario": "indoor", "state": "RECORDED", "elapsed_measurement_s": 600}, {"scenario": "tunnel", "state": "FAILED"}], "reason": "Completed600s zero-command-only indoor still blocks without command leakage. Same-input C++ audit finds HT-feasible2m escapes at32 headings but not16; stop remaining batch to isolate finer heading search, not retrace admission. Any incomplete tunnel is not counted as600s."}, {"path": "DIAGNOSTIC_STOP_REASON.json", "state": "see_original_file", "runs": [], "reason": "Completed600s zero-command-only indoor still blocks without command leakage. Same-input C++ audit finds HT-feasible2m escapes at32 headings but not16; stop remaining batch to isolate finer heading search, not retrace admission. Any incomplete tunnel is not counted as600s."}]`。
- 包内视频：`indoor/camera_15fps.mp4`；36512148 bytes；SHA256 `18b0ae2e59804447345102b45aa4dfa210a897ae068f370e57a54ca02555d9fa`。
- 包内视频：`indoor/camera_h264.mp4`；5975939 bytes；SHA256 `383d32b5cefc4383e29e80c0eee0c8c8d8d6e8f9599b1f0d89b915be722cb876`。
