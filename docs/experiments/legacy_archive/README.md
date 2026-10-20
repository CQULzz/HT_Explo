# 历史实验完整数据与版本对应表

本次范围：原审计列出的 **62 个历史目录**，常规文件共 **63.405 GiB**。
已完成远端大小与 SHA256 核验：**40/62 个目录**，原始文件 **3.095 GiB**。其余状态以表格为准，不把待上传当作已备份。

## 版本对应的含义

Release 用于归入对应研究阶段；旧标签保持不动。归入某阶段不表示该阶段标签就是实际测试提交。逐目录 inventory 中保留原 manifest 的 git_head/tested_code_commit/current_commit、源文件哈希、working_tree.patch、原始时长及失败说明。没有提交号的旧记录标为未知，不用当前 HEAD 补写。

多环境目录可能包含不同实际提交；原版 TARE 录包与事后 CuPy/HT 重放属于共享对照资料，不等于 HT 驱车试验。完整录制、中止、短测、离线分析和导航成功是不同概念，本次归档不新增任何“通过”结论。

## 数据清单

| 阶段 | 原始目录 | GiB | 备份状态 / Release |
|---|---|---:|---|
| 8 | `2026-10-12_10-01-43` | 0.0000 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/2026-10-12_10-01-43.json) · [回执](receipts/2026-10-12_10-01-43.json) |
| 8 | `2026-10-12_10-02-28` | 0.0000 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/2026-10-12_10-02-28.json) · [回执](receipts/2026-10-12_10-02-28.json) |
| 8 | `2026-10-12_10-04-20` | 0.0000 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/2026-10-12_10-04-20.json) · [回执](receipts/2026-10-12_10-04-20.json) |
| 8 | `2026-10-12_10-05-50` | 0.0001 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/2026-10-12_10-05-50.json) · [回执](receipts/2026-10-12_10-05-50.json) |
| 8 | `2026-10-12_10-08-15` | 0.0001 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/2026-10-12_10-08-15.json) · [回执](receipts/2026-10-12_10-08-15.json) |
| 8 | `2026-10-12_10-10-47` | 0.0002 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/2026-10-12_10-10-47.json) · [回执](receipts/2026-10-12_10-10-47.json) |
| 8 | `2026-10-12_13-36-02` | 0.0000 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/2026-10-12_13-36-02.json) · [回执](receipts/2026-10-12_13-36-02.json) |
| 8 | `2026-10-12_13-36-45` | 0.0001 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/2026-10-12_13-36-45.json) · [回执](receipts/2026-10-12_13-36-45.json) |
| 8 | `2026-10-13_13-33-11` | 0.0016 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/2026-10-13_13-33-11.json) · [回执](receipts/2026-10-13_13-33-11.json) |
| 8 | `history_executor_2026-10-12_13-43-58` | 0.0001 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/history_executor_2026-10-12_13-43-58.json) · [回执](receipts/history_executor_2026-10-12_13-43-58.json) |
| 8 | `history_export_2026-10-12_13-52-39` | 0.0011 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/history_export_2026-10-12_13-52-39.json) · [回执](receipts/history_export_2026-10-12_13-52-39.json) |
| 8 | `history_lookahead_2026-10-12_13-47-51` | 0.0001 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/history_lookahead_2026-10-12_13-47-51.json) · [回执](receipts/history_lookahead_2026-10-12_13-47-51.json) |
| 8 | `ht_validation_final_2026-10-15` | 1.9329 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) |
| 8 | `noise_chain_2026-10-13_15-26-34` | 0.0313 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/noise_chain_2026-10-13_15-26-34.json) · [回执](receipts/noise_chain_2026-10-13_15-26-34.json) |
| 8 | `noise_source_analysis_2026-10-13` | 0.0005 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/noise_source_analysis_2026-10-13.json) · [回执](receipts/noise_source_analysis_2026-10-13.json) |
| 8 | `noise_static_2026-10-13` | 0.0043 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/noise_static_2026-10-13.json) · [回执](receipts/noise_static_2026-10-13.json) |
| 8 | `noise_static_dense_2026-10-13` | 0.0120 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/noise_static_dense_2026-10-13.json) · [回执](receipts/noise_static_dense_2026-10-13.json) |
| 8 | `noise_static_unit_resolution_2026-10-13` | 0.0035 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/noise_static_unit_resolution_2026-10-13.json) · [回执](receipts/noise_static_unit_resolution_2026-10-13.json) |
| 8 | `original_10min_replay_2026-10-13_16-58-15` | 28.9696 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) |
| 8 | `pose_permission_fix_2026-10-13_16-21-50` | 0.0010 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/pose_permission_fix_2026-10-13_16-21-50.json) · [回执](receipts/pose_permission_fix_2026-10-13_16-21-50.json) |
| 8 | `pose_permission_latest_map_2026-10-13_16-25-58` | 0.0027 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/pose_permission_latest_map_2026-10-13_16-25-58.json) · [回执](receipts/pose_permission_latest_map_2026-10-13_16-25-58.json) |
| 8 | `realtime_fix_smoke_2026-10-15` | 0.5352 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/realtime_fix_smoke_2026-10-15.json) · [回执](receipts/realtime_fix_smoke_2026-10-15.json) |
| 8 | `stop_ht_2026-10-12_14-00-05` | 0.0041 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/stop_ht_2026-10-12_14-00-05.json) · [回执](receipts/stop_ht_2026-10-12_14-00-05.json) |
| 8 | `surface_fix_live_2026-10-15` | 0.8977 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) |
| 8 | `surface_fix_live_reliable_isolated_2026-10-15` | 0.8403 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) |
| 8 | `upstream_replay_scan_tf_smoke_2026-10-13` | 0.0001 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/upstream_replay_scan_tf_smoke_2026-10-13.json) · [回执](receipts/upstream_replay_scan_tf_smoke_2026-10-13.json) |
| 8 | `upstream_replay_scan_tf_verified_2026-10-13` | 0.0377 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) · [逐文件清单](inventories/upstream_replay_scan_tf_verified_2026-10-13.json) · [回执](receipts/upstream_replay_scan_tf_verified_2026-10-13.json) |
| 8 | `upstream_replay_smoke_2026-10-13` | 0.6439 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-elevation-xytheta) |
| 9 | `ht_continuity_candidates_2026-10-15` | 1.2712 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-goal-continuity) |
| 9 | `ht_continuity_escape_2026-10-15` | 1.8119 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-goal-continuity) |
| 9 | `ht_continuity_final_2026-10-15` | 1.8976 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-goal-continuity) |
| 9 | `ht_target_continuity_2026-10-15` | 0.4081 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-goal-continuity) · [逐文件清单](inventories/ht_target_continuity_2026-10-15.json) · [回执](receipts/ht_target_continuity_2026-10-15.json) |
| 9 | `ht_target_continuity_verified_2026-10-15` | 0.2403 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261015-goal-continuity) · [逐文件清单](inventories/ht_target_continuity_verified_2026-10-15.json) · [回执](receipts/ht_target_continuity_verified_2026-10-15.json) |
| 10 | `ht_repeat_publish_2026-10-15` | 2.4815 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-garage-repeat-20261015-1225) |
| 11 | `ht_swept_gate_2026-10-16` | 1.9364 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-swept-check) |
| 11 | `ht_swept_gate_repeat_2026-10-16` | 1.8527 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-swept-check) |
| 12 | `tare_ht_pair_2026-10-16` | 2.0478 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-tare-compare) |
| 12 | `version_publication_2026-10-16` | 0.0000 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-tare-compare) · [逐文件清单](inventories/version_publication_2026-10-16.json) · [回执](receipts/version_publication_2026-10-16.json) |
| 13 | `ht_endurance_2026-10-16_19-23-16` | 1.6717 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-endurance) |
| 14 | `ht_guide_fix_2026-10-16_22-53-33` | 0.5761 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-progress-memory) |
| 14 | `ht_progress_return_fix_2026-10-16_23-20-58` | 0.0000 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-progress-memory) · [逐文件清单](inventories/ht_progress_return_fix_2026-10-16_23-20-58.json) · [回执](receipts/ht_progress_return_fix_2026-10-16_23-20-58.json) |
| 14 | `ht_progress_return_fix_2026-10-16_23-23-20` | 0.7262 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-progress-memory) |
| 15 | `ht_endurance_progress_2026-10-17_00-39-55` | 2.3770 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-endurance-return) |
| 16 | `ht_clean_shutdown_smoke2_2026-10-17` | 0.0479 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-crossguide-lifecycle) · [逐文件清单](inventories/ht_clean_shutdown_smoke2_2026-10-17.json) · [回执](receipts/ht_clean_shutdown_smoke2_2026-10-17.json) |
| 16 | `ht_clean_shutdown_smoke3_2026-10-17` | 0.0320 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-crossguide-lifecycle) · [逐文件清单](inventories/ht_clean_shutdown_smoke3_2026-10-17.json) · [回执](receipts/ht_clean_shutdown_smoke3_2026-10-17.json) |
| 16 | `ht_cycle_shutdown_smoke_2026-10-17` | 0.0799 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-crossguide-lifecycle) · [逐文件清单](inventories/ht_cycle_shutdown_smoke_2026-10-17.json) · [回执](receipts/ht_cycle_shutdown_smoke_2026-10-17.json) |
| 16 | `ht_direct_gazebo_shutdown_smoke4_2026-10-17` | 0.0000 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-crossguide-lifecycle) · [逐文件清单](inventories/ht_direct_gazebo_shutdown_smoke4_2026-10-17.json) · [回执](receipts/ht_direct_gazebo_shutdown_smoke4_2026-10-17.json) |
| 16 | `ht_endurance_crossguide_2026-10-17_02-14-09` | 0.5103 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-crossguide-lifecycle) · [逐文件清单](inventories/ht_endurance_crossguide_2026-10-17_02-14-09.json) · [回执](receipts/ht_endurance_crossguide_2026-10-17_02-14-09.json) |
| 17 | `ht_endurance_cpu_limited_2026-10-17_02-35-26` | 0.1556 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-blas-threads) · [逐文件清单](inventories/ht_endurance_cpu_limited_2026-10-17_02-35-26.json) · [回执](receipts/ht_endurance_cpu_limited_2026-10-17_02-35-26.json) |
| 18 | `ht_multiscene_10min_2026-10-17_11-37-52` | 2.2031 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-multiscene-10min) |
| 19 | `ht_indoor_dense_10min_2026-10-17_12-38-24` | 0.2891 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-indoor-viewpoints) · [逐文件清单](inventories/ht_indoor_dense_10min_2026-10-17_12-38-24.json) · [回执](receipts/ht_indoor_dense_10min_2026-10-17_12-38-24.json) |
| 20 | `ht_combined_admission_10min_2026-10-18_01-52-52` | 1.7468 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-context-recovery) |
| 20 | `ht_completion_diagnostic_2026-10-18_01-06-52` | 0.2692 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-context-recovery) · [逐文件清单](inventories/ht_completion_diagnostic_2026-10-18_01-06-52.json) · [回执](receipts/ht_completion_diagnostic_2026-10-18_01-06-52.json) |
| 20 | `ht_context_recovery_10min_2026-10-17_14-42-07` | 0.0971 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-context-recovery) · [逐文件清单](inventories/ht_context_recovery_10min_2026-10-17_14-42-07.json) · [回执](receipts/ht_context_recovery_10min_2026-10-17_14-42-07.json) |
| 20 | `ht_heading_reserve_10min_2026-10-18_01-47-41` | 0.3299 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-context-recovery) · [逐文件清单](inventories/ht_heading_reserve_10min_2026-10-18_01-47-41.json) · [回执](receipts/ht_heading_reserve_10min_2026-10-18_01-47-41.json) |
| 20 | `ht_recovery_verified_10min_2026-10-17_14-55-03` | 0.0000 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-context-recovery) · [逐文件清单](inventories/ht_recovery_verified_10min_2026-10-17_14-55-03.json) · [回执](receipts/ht_recovery_verified_10min_2026-10-17_14-55-03.json) |
| 20 | `ht_recovery_verified_10min_2026-10-17_14-55-26` | 0.5603 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-context-recovery) |
| 20 | `ht_reversible_motion_10min_2026-10-18_01-26-31` | 1.1109 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-context-recovery) |
| 21 | `ht_zero_twist_fine_heading_10min_2026-10-18_02-28-07` | 1.9352 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-zero-hold) |
| 21 | `ht_zero_twist_verified_10min_2026-10-18_02-13-23` | 0.0000 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-zero-hold) · [逐文件清单](inventories/ht_zero_twist_verified_10min_2026-10-18_02-13-23.json) · [回执](receipts/ht_zero_twist_verified_10min_2026-10-18_02-13-23.json) |
| 21 | `ht_zero_twist_verified_10min_2026-10-18_02-15-15` | 0.8191 | [待完成](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-zero-hold) |
| 39 | `ht_revision_metric_reanalysis_2026-10-19` | 0.0003 | [已核验](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261020-successor-pruning) · [逐文件清单](inventories/ht_revision_metric_reanalysis_2026-10-19.json) · [回执](receipts/ht_revision_metric_reanalysis_2026-10-19.json) |

## 下载与恢复

在对应 Release 下载同一 `legacy-目录名-内容键` 前缀下的所有 `.tar.zst.partNNN`、`-files.json` 和 `-verified.json`。不要混用不同内容键。仓库 receipts 文件额外记录远端 proof 自身的校验值。

```bash
# 把前缀替换为该数据回执中的 content_key；先依照回执逐个验证大小和 SHA256。
cat legacy-目录名-内容键.tar.zst.part[0-9][0-9][0-9] | zstd -d -c | tar -xf - -C 恢复目录
```

所有数据集解压到同一个恢复目录，跨目录的相对符号链接才能找到目标。打包不跟随链接复制外部数据；原绝对链接文本保存在清单中，归档内改用等价相对链接。空目录也会保留。所有普通文件内容按逐文件 SHA256 核验。

上传采用流式 tar + zstd、每卷最多512 MiB，每个上传任务只暂存一卷，默认3个并发任务合计最多1.5 GiB；中断后重新执行 `python3 scripts/archive_legacy_ht_data.py` 会核对并复用相同远端分卷，不覆盖同名不同内容。完整数据仅放 Release 附件，不写入 Git 历史。

本次备份工具不会删除历史源目录。原保存政策为 GitHub 全部保留、本机最近两轮完整录包；清理必须另做逐文件本机差异核对，报告、视频和必要回归样本继续保留。第40/41轮完整数据由标准发布流程保留，未重复加入这62个历史目录。

## 原审计之外的文件

下载目录的重复视频、HT.zip 项目压缩包，以及其他工作区数据不属于这62个目录；未据此删除或宣称已完整备份。
