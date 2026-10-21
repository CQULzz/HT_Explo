# 阶段15｜60分钟复测：返回完成但仍有回访

实验预发布。核心规划代码仍为`c85ad1f`，本阶段只归档复测证据。比较对象为此前HT长测，不是重新运行原版TARE。

## 改了什么

对阶段14核心代码进行同Garage连续60分钟记录，补活动/等待分段控制、返航、低收益回访、地图时效及主动关停审计；不新增导航算法。

## 实现了什么功能

首次在本次最新规划代码的长测中观察到TARE触发返航并通过到家、低速和停稳条件，任务完成后保持停车；明确区分末尾正常等待与中途低收益回访。

## 实验与验证

44分28秒左右COMPLETED，距记录起点0.291米；共768.57米、371个轨迹格、6513.750m³近似观测，对照旧60分钟为3296.375m³。7201个轨迹采样、72000条录包控制指令；14项哈希不变，视频完整解码通过。

[报告、曲线与完整视频](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_endurance_progress_2026-10-17/REPORT.md)。后15.5分钟曲线平坦属于完成后等待；活动期回访单独审计。

## 存在什么问题

活动约44.5分钟，余下15.5分钟为完成后等待，不是主动探索60分钟。中途7.38分钟行驶106.17米仅增2.125m³；地图年龄最高3.37秒，1Hz检查3次超过3秒。主动SIGINT后CMU部分节点关停异常；无运行期意外退出记录。单场景一轮、非真值全覆盖或实车证明。 自由体积为抽样射线并集近似，两轮实际入选帧数不同，不能作为严格统计基准。

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。

<!-- legacy-full-data-start -->
## 历史完整实验数据补归档（2026-10-20）

本阶段关联的 **1 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。

**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。

[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)

| 历史目录 | 原始文件GiB | 完整数据前缀 |
|---|---:|---|
| `ht_endurance_progress_2026-10-17_00-39-55` | 2.3770 | `legacy-ht_endurance_progress_2026-10-17_00-39-55-4ae0e7291382` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段15完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-15.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/3fe5b9b5ee23c7a3cc8ec7a0243cdd2d09891a38)：`3fe5b9b5ee23c7a3cc8ec7a0243cdd2d09891a38`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
