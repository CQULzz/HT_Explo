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
