# 阶段17：限制BLAS空转线程与分段计时（数值回归）

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261017-blas-threads`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-blas-threads)。
- 归档标签提交：[`f1c84854ccc147d40d7f9120c9713ba5e11c736c`](https://github.com/CQULzz/HT_Explo/commit/f1c84854ccc147d40d7f9120c9713ba5e11c736c)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261017-blas-threads)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

单独限制HT桥接的BLAS库为1线程，保留PyTorch2线程；记录实际线程池和融合/支撑准备/网络/发布耗时。

消除周期性小矩阵拟合唤醒28个BLAS工作线程后大量空转的争用；不修改网络权重、HT门槛、未知策略和速度。

## 验证与剩余问题

诊断默认配置0.653墙钟秒消耗7.695 CPU秒；BLAS单线程0.611墙钟秒消耗0.0105 CPU秒。地面参考最大差0；固定权重HT联合回归硬门槛逐格一致，另有3项参考面与6项融合回归通过。原计划60分钟按用户新要求改为五环境各10分钟，见阶段18。

该CPU诊断不等于整张HT地图提速700倍，也不是整车长测通过；约17分钟诊断轮主动中止，不作为完成60分钟记录。尚不能证明60分钟稳定性；五环境10分钟记录进行中，见阶段18。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/results/ht_blas_contention_2026-10-17/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_blas_contention_2026-10-17/REPORT.md)
- [docs/fixes/2026-10-17_endurance_followup.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/fixes/2026-10-17_endurance_followup.md)
- 原版本总表记录的控制提交：`f1c84854ccc147d40d7f9120c9713ba5e11c736c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_endurance_cpu_limited_2026-10-17_02-35-26.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_endurance_cpu_limited_2026-10-17_02-35-26.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_endurance_cpu_limited_2026-10-17_02-35-26

- 数据分片前缀：`legacy-ht_endurance_cpu_limited_2026-10-17_02-35-26-52aa222412e8`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_endurance_cpu_limited_2026-10-17_02-35-26.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_endurance_cpu_limited_2026-10-17_02-35-26.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "f1c84854ccc147d40d7f9120c9713ba5e11c736c"}, "planned_duration_s": 3600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "FAILURE.json", "state": "see_original_file", "runs": [], "reason": null}]`。
- 包内视频：`camera_2fps.mp4`；2782938 bytes；SHA256 `28e88e33fbb8f476790b367861431f0ed677cea45ae033b425e03c94cc89e71a`。
