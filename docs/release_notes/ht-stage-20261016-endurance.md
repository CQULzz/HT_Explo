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
