# 阶段09：目标保持与执行器独立校验

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[dbce623](https://github.com/CQULzz/HT_Explo/commit/dbce623161087fcaac865b1d4db5305d1cfe2c9c)。类型：功能。
实际控制/功能来源：[dbce623](https://github.com/CQULzz/HT_Explo/commit/dbce623161087fcaac865b1d4db5305d1cfe2c9c)。

## 改了什么

按世界位置保持目标、停滞冷却、稳定全局引导、候选预筛和侧向恢复；跟踪器独立读取新鲜HT图校验路径。

## 实现了什么功能

减少目标尚未完成时反向切换；HT启用时旧Bool许可年龄不再单独触发停车，地图/扫描/定位/路径时效和显式禁止仍有效。

## 实验与验证

一轮180秒56.54米，目标方向反转9→0；149项核心、13项HT ROS和4项跟踪器检查通过。

## 存在什么问题

同代码后续复跑29.76米、102秒后长期停车，故不能把这次56.54米视为稳定通过。仍有规划/执行采样不一致。

## 报告与代码

- [docs/xytheta_execution_continuity.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/xytheta_execution_continuity.md)
- [docs/results/ht_continuity_2026-10-15/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_continuity_2026-10-15/REPORT.md)
- [docs/results/ht_repeat_2026-10-15/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_repeat_2026-10-15/REPORT.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-09)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/dbce623161087fcaac865b1d4db5305d1cfe2c9c)

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。

<!-- legacy-full-data-start -->
## 历史完整实验数据补归档（2026-10-20）

本阶段关联的 **5 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。

**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。

[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)

| 历史目录 | 原始文件GiB | 完整数据前缀 |
|---|---:|---|
| `ht_continuity_candidates_2026-10-15` | 1.2712 | `legacy-ht_continuity_candidates_2026-10-15-9146d7827481` |
| `ht_continuity_escape_2026-10-15` | 1.8119 | `legacy-ht_continuity_escape_2026-10-15-4f556a31eb5e` |
| `ht_continuity_final_2026-10-15` | 1.8976 | `legacy-ht_continuity_final_2026-10-15-3ed39cf33caa` |
| `ht_target_continuity_2026-10-15` | 0.4081 | `legacy-ht_target_continuity_2026-10-15-9937c4a8a0d5` |
| `ht_target_continuity_verified_2026-10-15` | 0.2403 | `legacy-ht_target_continuity_verified_2026-10-15-d67600d6c799` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->
