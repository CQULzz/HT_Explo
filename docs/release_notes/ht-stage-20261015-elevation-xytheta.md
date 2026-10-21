# 阶段08：实际XYθ硬约束规划与分层历史高程

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[8398f53](https://github.com/CQULzz/HT_Explo/commit/8398f538450a21c4ee9d65d17193ee084eacee03)。类型：功能。
实际控制/功能来源：[322ec85](https://github.com/CQULzz/HT_Explo/commit/322ec85c728c5900d3e47f22b4c3c5a4e6bccc99)。

## 改了什么

322ec85一次归档此前本地XYθ、历史高程工作及当日修复：引入Hybrid A*和独立执行器，修正坐标翻转、固定世界索引、分层高程和真实观测时间。

## 实现了什么功能

从odom位姿到目标视点规划前进/倒车/原地旋转路径；P≥0.5硬门槛、默认严格未知；全局历史高程裁局部窗口供HT推理。

## 实验与验证

180秒实际HT控车仅行驶14.35米；对应窗口接收984帧、成功融合窗口983帧；225组地图时间戳一致。

## 存在什么问题

运动连续性差、旧许可1.5秒超时导致大量停车，目标反复切换；仍有噪声/未知区，未完成探索或实车验证。10月12日只是本地实验日期，不是独立Git发布。

## 报告与代码

- [docs/XYTHETA_EXPERIMENT_2026-10-12.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/XYTHETA_EXPERIMENT_2026-10-12.md)
- [docs/HISTORICAL_ELEVATION_EXPERIMENT_2026-10-12.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/HISTORICAL_ELEVATION_EXPERIMENT_2026-10-12.md)
- [docs/ELEVATION_MAPPING_FIXES_2026-10-15.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/ELEVATION_MAPPING_FIXES_2026-10-15.md)
- [docs/results/ht_validation_2026-10-15/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_validation_2026-10-15/REPORT.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-08)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/8398f538450a21c4ee9d65d17193ee084eacee03)

<!-- legacy-full-data-start -->
## 历史完整实验数据补归档（2026-10-20）

本阶段关联的 **28 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。

**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。

[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)

| 历史目录 | 原始文件GiB | 完整数据前缀 |
|---|---:|---|
| `2026-10-12_10-01-43` | 0.0000 | `legacy-2026-10-12_10-01-43-60862731f5ae` |
| `2026-10-12_10-02-28` | 0.0000 | `legacy-2026-10-12_10-02-28-b9d1ef653ada` |
| `2026-10-12_10-04-20` | 0.0000 | `legacy-2026-10-12_10-04-20-a6333e6f95e9` |
| `2026-10-12_10-05-50` | 0.0001 | `legacy-2026-10-12_10-05-50-754f2de48a15` |
| `2026-10-12_10-08-15` | 0.0001 | `legacy-2026-10-12_10-08-15-872d638e316f` |
| `2026-10-12_10-10-47` | 0.0002 | `legacy-2026-10-12_10-10-47-d073087872d9` |
| `2026-10-12_13-36-02` | 0.0000 | `legacy-2026-10-12_13-36-02-55a6f0ac762a` |
| `2026-10-12_13-36-45` | 0.0001 | `legacy-2026-10-12_13-36-45-03cbca571f89` |
| `2026-10-13_13-33-11` | 0.0016 | `legacy-2026-10-13_13-33-11-7ccccb15f40a` |
| `history_executor_2026-10-12_13-43-58` | 0.0001 | `legacy-history_executor_2026-10-12_13-43-58-192f2cc4b44e` |
| `history_export_2026-10-12_13-52-39` | 0.0011 | `legacy-history_export_2026-10-12_13-52-39-94bdb4696142` |
| `history_lookahead_2026-10-12_13-47-51` | 0.0001 | `legacy-history_lookahead_2026-10-12_13-47-51-dc9d066cc3de` |
| `ht_validation_final_2026-10-15` | 1.9329 | `legacy-ht_validation_final_2026-10-15-5d215d5eab98` |
| `noise_chain_2026-10-13_15-26-34` | 0.0313 | `legacy-noise_chain_2026-10-13_15-26-34-9bbc69c9cb74` |
| `noise_source_analysis_2026-10-13` | 0.0005 | `legacy-noise_source_analysis_2026-10-13-34eb54618923` |
| `noise_static_2026-10-13` | 0.0043 | `legacy-noise_static_2026-10-13-c72eccf282b2` |
| `noise_static_dense_2026-10-13` | 0.0120 | `legacy-noise_static_dense_2026-10-13-6c690c932c4d` |
| `noise_static_unit_resolution_2026-10-13` | 0.0035 | `legacy-noise_static_unit_resolution_2026-10-13-6aa837a9a79d` |
| `original_10min_replay_2026-10-13_16-58-15` | 28.9696 | `legacy-original_10min_replay_2026-10-13_16-58-15-6481d2b90b22` |
| `pose_permission_fix_2026-10-13_16-21-50` | 0.0010 | `legacy-pose_permission_fix_2026-10-13_16-21-50-ff7a2ea7290c` |
| `pose_permission_latest_map_2026-10-13_16-25-58` | 0.0027 | `legacy-pose_permission_latest_map_2026-10-13_16-25-58-2561f0fa6c24` |
| `realtime_fix_smoke_2026-10-15` | 0.5352 | `legacy-realtime_fix_smoke_2026-10-15-701af2a9db13` |
| `stop_ht_2026-10-12_14-00-05` | 0.0041 | `legacy-stop_ht_2026-10-12_14-00-05-3691b7f5c95e` |
| `surface_fix_live_2026-10-15` | 0.8977 | `legacy-surface_fix_live_2026-10-15-2ba802339659` |
| `surface_fix_live_reliable_isolated_2026-10-15` | 0.8403 | `legacy-surface_fix_live_reliable_isolated_2026-10-15-ddc185f2a07c` |
| `upstream_replay_scan_tf_smoke_2026-10-13` | 0.0001 | `legacy-upstream_replay_scan_tf_smoke_2026-10-13-0ce41d04283e` |
| `upstream_replay_scan_tf_verified_2026-10-13` | 0.0377 | `legacy-upstream_replay_scan_tf_verified_2026-10-13-9d9e6545dbf2` |
| `upstream_replay_smoke_2026-10-13` | 0.6439 | `legacy-upstream_replay_smoke_2026-10-13-1995dace135b` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段08完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-08.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/8398f538450a21c4ee9d65d17193ee084eacee03)：`8398f538450a21c4ee9d65d17193ee084eacee03`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
