# 阶段10：同版本复跑失败与完整数据发布

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[0b842e4](https://github.com/CQULzz/HT_Explo/commit/0b842e4ab71a1ed0249cc32da923a0f51940106a)。类型：失败复跑归档。
实际控制/功能来源：[dbce623](https://github.com/CQULzz/HT_Explo/commit/dbce623161087fcaac865b1d4db5305d1cfe2c9c)。

## 改了什么

新增完整视频、CSV/快照/录包下载与校验清单；697ae2e随后补GitHub下载和SHA-256复核。

## 实现了什么功能

可以复现并查看约102秒后的失败全过程，保留原Release附件链接。

## 实验与验证

180秒29.76米，最后60秒0米；HT_PATH_BLOCKED对应1562个零速指令样本。

## 存在什么问题

这是失败证据归档，不是算法修复；控车仍为dbce623。上层HT_ASSISTED不代表执行端允许运动。

## 报告与代码

- [docs/results/ht_repeat_2026-10-15/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_repeat_2026-10-15/REPORT.md)
- [docs/results/ht_repeat_2026-10-15/github_upload_verification.json](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_repeat_2026-10-15/github_upload_verification.json)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-10)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/0b842e4ab71a1ed0249cc32da923a0f51940106a)

## 原有附件（保留原URL）

- [garage_ht_xytheta_180s.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-garage-repeat-20261015-1225/garage_ht_xytheta_180s.mp4)
- [garage_ht_experiment_results.zip](https://github.com/CQULzz/HT_Explo/releases/download/ht-garage-repeat-20261015-1225/garage_ht_experiment_results.zip)
- [original_bag_0.mcap](https://github.com/CQULzz/HT_Explo/releases/download/ht-garage-repeat-20261015-1225/original_bag_0.mcap)
- [release_files.json](https://github.com/CQULzz/HT_Explo/releases/download/ht-garage-repeat-20261015-1225/release_files.json)

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。
