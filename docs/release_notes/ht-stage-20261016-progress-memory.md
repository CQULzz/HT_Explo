# 阶段14｜全局停滞恢复与返航容差修正

实验预发布，核心代码为`c85ad1f`；探索修复起于`7f1c253`。比较对象是此前HT长测，不是本轮重新运行原版TARE。

## 改了什么

全局引导独立进展计时、180秒失败冷却、世界坐标重复访问记忆；修正恢复评分、返航检查点到达容差及无用探索搜索。

## 实现了什么功能

局部目标完成不再掩盖全局停滞；零收益主目标不能压住所有恢复候选；保留HT硬门槛、严格未知和速度上限。

## 实验与验证

242项核心、15项ROS和5项跟踪测试通过。两轮20/25分钟；最新同期20分钟估计观测6498m³，对照3293.875m³；第10–20分钟增益1654.125m³，对照26.375m³。25分钟447.50米、294格，最终EXPLORING。

两段完整H.264视频、曲线和CSV随仓库报告保存，视频已全文件解码。[docs/results/ht_progress_fix_2026-10-16/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_progress_fix_2026-10-16/REPORT.md) · [docs/results/ht_progress_fix_2026-10-16/same_duration_metrics.json](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_progress_fix_2026-10-16/same_duration_metrics.json) · [docs/results/ht_progress_fix_2026-10-16/return_fix_trial/validation_checks.json](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_progress_fix_2026-10-16/return_fix_trial/validation_checks.json)

## 存在什么问题

第一轮返航BLOCKED；补容差回归后，25分钟轮未触发返航。后续阶段15的60分钟记录验证了一次返回完成，但活动期仍有低增益回访、短时地图过期和关停清理报错；无实车或真值全覆盖验收。 体积是抽样点云射线的自由体素并集近似，不是官方覆盖率。两轮不是严格单一改动消融。

2026-10-17后续验证：[阶段15完整60分钟记录与返航审计](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_endurance_progress_2026-10-17/REPORT.md)。原两轮20/25分钟的失败与未验证状态仍保留。

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。

<!-- legacy-full-data-start -->
## 历史完整实验数据补归档（2026-10-20）

本阶段关联的 **3 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。

**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。

[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)

| 历史目录 | 原始文件GiB | 完整数据前缀 |
|---|---:|---|
| `ht_guide_fix_2026-10-16_22-53-33` | 0.5761 | `legacy-ht_guide_fix_2026-10-16_22-53-33-630c6e89580a` |
| `ht_progress_return_fix_2026-10-16_23-20-58` | 0.0000 | `legacy-ht_progress_return_fix_2026-10-16_23-20-58-1ac23c13d31a` |
| `ht_progress_return_fix_2026-10-16_23-23-20` | 0.7262 | `legacy-ht_progress_return_fix_2026-10-16_23-23-20-4a6357c73099` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段14完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-14.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/9393e7da7d1eeabf04a4325593834304f236e405)：`9393e7da7d1eeabf04a4325593834304f236e405`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
