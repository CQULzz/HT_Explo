# 阶段20｜观测支撑与停滞恢复：返航通过，探索仍有退步

标签固定到实测整栈源码`dee873d`，C++修改`73cae0b`；视频与数据归档`9fb2b63`。

## 改了什么

区分网络上下文与车体观测支撑；按实际观测时间保留拒绝，有限坏高度仅作八方向禁行上下文；增加12秒原地停滞释放、有限回退和0.35秒共享搜索预算，CPU改4线程channels-last。

## 实现了什么功能

避免网络缺测重复膨胀及旧方差反复否定历史；保留HT硬阈值、真实未知和碰撞检查，支持安全回退及实际返航。

## 实验与验证

311核心、17ROS、6跟踪及53Python回归通过；隧道/室内各600秒、两段15fps视频完整解码及各13项采集核验通过。均COMPLETED；等长前缀最长全零指令145.95→4.30秒、39.80→4.65秒；室内规划P95 1.576→1.004秒。

隧道249.58秒、室内328.43秒确认返航。两组都继续记录到600秒，后段零指令和不动属于正常完成后停车；等长前缀比较截止于新轮完成，未混淆主动停车与卡死。

## 存在什么问题

室内约215秒触发返航，总近似观测1900.250→1106.750m³（下降41.8%）；任务收尾不是全覆盖证明。室内HT年龄最大5.01秒，两场景各8个1Hz样本超过3秒。森林约4Hz本轮未重测，其他三场景未重跑。保留约195秒失败诊断；每配置仅一次、无实车或长期稳定性验收。

证据：[2026-10-17_context_recovery.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/fixes/2026-10-17_context_recovery.md) · [REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_recovery_comparison_2026-10-17/REPORT.md) · [REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_recovery_10min_2026-10-17/REPORT.md) · [REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_context_diagnostics_2026-10-17/REPORT.md)

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。

<!-- legacy-full-data-start -->
## 历史完整实验数据补归档（2026-10-20）

本阶段关联的 **7 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。

**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。

[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)

| 历史目录 | 原始文件GiB | 完整数据前缀 |
|---|---:|---|
| `ht_combined_admission_10min_2026-10-18_01-52-52` | 1.7468 | `legacy-ht_combined_admission_10min_2026-10-18_01-52-52-00014a2f02d8` |
| `ht_completion_diagnostic_2026-10-18_01-06-52` | 0.2692 | `legacy-ht_completion_diagnostic_2026-10-18_01-06-52-01fe8da2d70f` |
| `ht_context_recovery_10min_2026-10-17_14-42-07` | 0.0971 | `legacy-ht_context_recovery_10min_2026-10-17_14-42-07-507d7a8ee98a` |
| `ht_heading_reserve_10min_2026-10-18_01-47-41` | 0.3299 | `legacy-ht_heading_reserve_10min_2026-10-18_01-47-41-f2fe98d2f285` |
| `ht_recovery_verified_10min_2026-10-17_14-55-03` | 0.0000 | `legacy-ht_recovery_verified_10min_2026-10-17_14-55-03-3227ad8844b7` |
| `ht_recovery_verified_10min_2026-10-17_14-55-26` | 0.5603 | `legacy-ht_recovery_verified_10min_2026-10-17_14-55-26-71125d7a908e` |
| `ht_reversible_motion_10min_2026-10-18_01-26-31` | 1.1109 | `legacy-ht_reversible_motion_10min_2026-10-18_01-26-31-08cff2aceafa` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段20完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-20.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/dee873db9a25778eb67060100025bea2f619c0ee)：`dee873db9a25778eb67060100025bea2f619c0ee`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
