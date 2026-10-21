# 阶段17｜限制BLAS空转线程与分段计时（数值回归）

实验预发布；控制代码 `f1c8485`，C++规划沿用阶段16。用户改为五环境各10分钟记录，见阶段18；没有完成新的60分钟验证。

## 改了什么

单独限制HT桥接的BLAS库为1线程，保留PyTorch2线程；记录实际线程池和融合/支撑准备/网络/发布耗时。

## 实现了什么功能

消除周期性小矩阵拟合唤醒28个BLAS工作线程后大量空转的争用；不修改网络权重、HT门槛、未知策略和速度。

## 实验与验证

诊断默认配置0.653墙钟秒消耗7.695 CPU秒；BLAS单线程0.611墙钟秒消耗0.0105 CPU秒。地面参考最大差0；固定权重HT联合回归硬门槛逐格一致，另有3项参考面与6项融合回归通过。用户已改为五环境各10分钟，正在执行。

[CPU争用诊断与主动中止记录](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_blas_contention_2026-10-17/REPORT.md)。诊断轮第5–15分钟桥接CPU中位数约676%，100%代表一个逻辑核。离线周期拟合实测主要验证空转消耗，不冒充整车或网络推理吞吐。

## 存在什么问题

该CPU诊断不等于整张HT地图提速700倍，也不是整车长测通过；约17分钟诊断轮主动中止，不作为完成60分钟记录。尚未完成新的60分钟验证；五环境10分钟记录见阶段18。

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。

<!-- legacy-full-data-start -->
## 历史完整实验数据补归档（2026-10-20）

本阶段关联的 **1 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。

**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。

[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)

| 历史目录 | 原始文件GiB | 完整数据前缀 |
|---|---:|---|
| `ht_endurance_cpu_limited_2026-10-17_02-35-26` | 0.1556 | `legacy-ht_endurance_cpu_limited_2026-10-17_02-35-26-52aa222412e8` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->

<!-- repository-catalog-start -->
## 代码、视频与完整数据的对应关系

- [阶段17完整索引：实际实验候选、导航代码、报告、视频及数据回执](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/stage-17.md)
- [本阶段归档源码](https://github.com/CQULzz/HT_Explo/tree/f1c84854ccc147d40d7f9120c9713ba5e11c736c)：`f1c84854ccc147d40d7f9120c9713ba5e11c736c`。这是归档锚点；实际测量源码、运行patch与二进制哈希以原清单为准。
- [完整实验总目录](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md) · [分支和标签规则](https://github.com/CQULzz/HT_Explo/blob/main/docs/REPOSITORY_GUIDE.md)

早期历史目录只关联到研究阶段，未知测量提交保持待确认；补充回放视频不代表新的导航实验。原有报告、失败记录与全部附件保留。
<!-- repository-catalog-end -->
