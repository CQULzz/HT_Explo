# 阶段13：60分钟长测：运行连续但探索停滞

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[6bd5407](https://github.com/CQULzz/HT_Explo/commit/6bd5407b781771b0460ed1533eaee6d500c91bc4)。类型：长测归档。
实际控制/功能来源：[3912e37](https://github.com/CQULzz/HT_Explo/commit/3912e37df7541799c354bf568ff8f3d5b0383aab)。

## 改了什么

新增长测启动、健康与资源记录、抽样录包、源时间戳计数审计、分析工具及报告/视频；实验运行树基线为07ab006。

## 实现了什么功能

可检验长期资源增长、输入延迟、运动拒绝反馈与探索增益；被测规划算法与上阶段相同。

## 实验与验证

60分钟993.48米，无被测进程意外退出或重启；后40分钟又走约650米，仅增2.5m³估计自由空间，最后10分钟为0。

## 存在什么问题

未通过持续有效探索验证；全局引导长期不变、重复回访，网卡掉线时发生约13秒输入中断；内存未失控但持续扩图上界未验证。

## 报告与代码

- [docs/results/ht_endurance_2026-10-16/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_endurance_2026-10-16/REPORT.md)
- [docs/results/ht_endurance_2026-10-16/validation_checks.json](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_endurance_2026-10-16/validation_checks.json)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-13)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/6bd5407b781771b0460ed1533eaee6d500c91bc4)

## 最新结论

没有节点崩溃或重启不等于持续有效探索。后40分钟约650米、仅2.5m³新增估计自由空间，最后10分钟为0；探索未完成。

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。

<!-- legacy-full-data-start -->
## 历史完整实验数据补归档（2026-10-20）

本阶段关联的 **1 个历史目录**已作为本 Release 的 `legacy-*` 分卷附件补齐，并核对远端大小与 SHA256。

**阶段归属不等于标签就是实际测试提交。** 原始 manifest、测试提交、未提交补丁、源文件哈希、真实时长和失败/中止说明均保留在逐文件清单与数据中；没有证据的提交号仍标为未知。本次仅补数据，不改变原实验结论或标签。

[全部62目录的版本对应、逐文件清单、校验回执与下载恢复方法](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/legacy_archive/README.md)

| 历史目录 | 原始文件GiB | 完整数据前缀 |
|---|---:|---|
| `ht_endurance_2026-10-16_19-23-16` | 1.6717 | `legacy-ht_endurance_2026-10-16_19-23-16-1d2abdbb74bc` |

下载同一前缀的全部 `.tar.zst.partNNN`、`-files.json` 与 `-verified.json`；核对回执后按数字顺序合并解压。大MCAP/NPZ在Release附件，未加入Git历史。
<!-- legacy-full-data-end -->
