# 阶段12：最新原版TARE配对评测

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[07ab006](https://github.com/CQULzz/HT_Explo/commit/07ab0067dc7f47dc6eb7e5e2b9924f79f2ed9a24)。类型：对比评测归档。
实际控制/功能来源：[3912e37](https://github.com/CQULzz/HT_Explo/commit/3912e37df7541799c354bf568ff8f3d5b0383aab)。

## 改了什么

增加同场景/同前进目标的独立配对运行、公共自由体积统计、对比图和分屏视频。

## 实现了什么功能

明确量化原版与当前完整系统差距；与上阶段相比没有再升级运动规划算法。

## 实验与验证

180秒原版/HT里程81.08/54.52米，估计自由体积6242.625/3224.625m³；HT体积约为原版51.7%。

## 存在什么问题

每组一次且倒车/角速度/加速度未完全对齐，是端到端比较；HT转向、停车和回访更多，未追平原版。

## 报告与代码

- [docs/results/tare_ht_pair_2026-10-16/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/tare_ht_pair_2026-10-16/REPORT.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-12)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/07ab0067dc7f47dc6eb7e5e2b9924f79f2ed9a24)

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。
