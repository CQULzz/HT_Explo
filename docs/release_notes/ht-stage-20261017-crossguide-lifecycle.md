# 阶段16｜跨目标记忆与正常关停修复（短测验证）

实验预发布，控制代码 `bd0c2c2`。上一轮 44 分钟返回的数据属于阶段15，不能当作本次改动的实验效果。

## 改了什么

全局引导进展跨目标切换保留；零收益到达目标暂缓回访；拆分CuPy发布调度，修复CMU/CuPy/Gazebo关停及完成状态显示。

## 实现了什么功能

A→B→A不再重置A的停滞预算；新收益可绕过恢复目标冷却；工作区独立，HT硬门槛、严格未知、3秒时效和0.5m/s上限保留。

## 实验与验证

260核心、15 ROS、6跟踪器、8 CuPy/调度及2关停集成测试通过；第四轮仿真关停回归所有子节点正常退出，无残留。首轮复测发现BLAS线程争用，已主动中止；后续修复及新长测见阶段17。

[修复说明](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/fixes/2026-10-17_endurance_followup.md) · [四次短回归证据](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_followup_smoke_2026-10-17/REPORT.md)。保留前两次失败记录，没有将父进程退出码0当作全部子节点成功。

## 存在什么问题

短测不证明7.4分钟低收益回访已消除；新长测早期仍采样到超过3秒的地图年龄峰值。远端引导仍是距离启发，无完整全局可执行图；未做实车验证。

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。

<!-- legacy-full-data-start -->
## 历史完整实验数据补归档（2026-10-20）

本阶段关联的 **5 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。

**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。

[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)

| 历史目录 | 原始文件GiB | 完整数据前缀 |
|---|---:|---|
| `ht_clean_shutdown_smoke2_2026-10-17` | 0.0479 | `legacy-ht_clean_shutdown_smoke2_2026-10-17-371d7d55bff2` |
| `ht_clean_shutdown_smoke3_2026-10-17` | 0.0320 | `legacy-ht_clean_shutdown_smoke3_2026-10-17-87ed2633ff21` |
| `ht_cycle_shutdown_smoke_2026-10-17` | 0.0799 | `legacy-ht_cycle_shutdown_smoke_2026-10-17-1e23e5775a1d` |
| `ht_direct_gazebo_shutdown_smoke4_2026-10-17` | 0.0000 | `legacy-ht_direct_gazebo_shutdown_smoke4_2026-10-17-c6c31266fb7a` |
| `ht_endurance_crossguide_2026-10-17_02-14-09` | 0.5103 | `legacy-ht_endurance_crossguide_2026-10-17_02-14-09-9fc29aa09fd9` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段16完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-16.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/bd0c2c24f7eac383a3d8120b312fa4eb499c3199)：`bd0c2c24f7eac383a3d8120b312fa4eb499c3199`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
