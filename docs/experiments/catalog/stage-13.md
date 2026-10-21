# 阶段13：60分钟长测：运行连续但探索停滞

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261016-endurance`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261016-endurance)。
- 归档标签提交：[`6bd5407b781771b0460ed1533eaee6d500c91bc4`](https://github.com/CQULzz/HT_Explo/commit/6bd5407b781771b0460ed1533eaee6d500c91bc4)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261016-endurance)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

新增长测启动、健康与资源记录、抽样录包、源时间戳计数审计、分析工具及报告/视频；实验运行树基线为07ab006。

可检验长期资源增长、输入延迟、运动拒绝反馈与探索增益；被测规划算法与上阶段相同。

## 验证与剩余问题

60分钟993.48米，无被测进程意外退出或重启；后40分钟又走约650米，仅增2.5m³估计自由空间，最后10分钟为0。

未通过持续有效探索验证；全局引导长期不变、重复回访，网卡掉线时发生约13秒输入中断；内存未失控但持续扩图上界未验证。 2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。

## 报告及版本证据

- [docs/results/ht_endurance_2026-10-16/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_endurance_2026-10-16/REPORT.md)
- [docs/results/ht_endurance_2026-10-16/validation_checks.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_endurance_2026-10-16/validation_checks.json)
- 原版本总表记录的控制提交：`3912e37df7541799c354bf568ff8f3d5b0383aab`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

- [docs/experiments/legacy_archive/receipts/ht_endurance_2026-10-16_19-23-16.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_endurance_2026-10-16_19-23-16.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

### ht_endurance_2026-10-16_19-23-16

- 数据分片前缀：`legacy-ht_endurance_2026-10-16_19-23-16-1d2abdbb74bc`。
- [上传回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/receipts/ht_endurance_2026-10-16_19-23-16.json) · [包内逐文件SHA256清单](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/legacy_archive/inventories/ht_endurance_2026-10-16_19-23-16.json)。
- 原测量源码记录：`[{"path": "manifest.json", "recorded_commits": {"git_head": "07ab0067dc7f47dc6eb7e5e2b9924f79f2ed9a24"}, "planned_duration_s": 3600, "working_tree_patch_preserved": true}]`。
- 原状态证据：`[{"path": "COMPLETED.json", "state": "see_original_file", "runs": [], "reason": null}]`。
- 包内视频：`camera_2fps.mp4`；35542532 bytes；SHA256 `f007b5bdbd7ae28c556ff2d41634f2078435ded53ba0e804b055bed9886aaf1a`。
- 包内视频：`camera_h264.mp4`；21435821 bytes；SHA256 `3b7047924f8d92b1285c620d4a262c9aa03b4fe4093383033081702231b4d3b2`。
