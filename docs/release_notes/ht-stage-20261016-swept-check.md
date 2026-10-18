# 阶段11：统一运动段检查与执行拒绝反馈

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[919d826](https://github.com/CQULzz/HT_Explo/commit/919d826f340c11e34421a738e80d2a2e85066eb9)。类型：功能。
实际控制/功能来源：[3912e37](https://github.com/CQULzz/HT_Explo/commit/3912e37df7541799c354bf568ff8f3d5b0383aab)。

## 改了什么

3912e37使规划、发布前和执行共用motionSupport及经过栅格检查；拒绝边反馈、6秒冷却重规划；后续提交补两轮视频/统计。

## 实现了什么功能

消除已复现的规划通过/执行拒绝循环；检查车头变化、倒车方向和前约1米路径；不放宽HT门槛或未知策略。

## 实验与验证

冻结原停车地图：旧路一致拒绝、重规划41姿态；155项核心、15项HT ROS、5项跟踪器检查通过。两轮180秒57.87/63.45米，最长完全零速1.65/1.50秒。

## 存在什么问题

只解决特定持续拒绝循环；仍有转向、回访与短暂停顿，短测不保证全局探索完成；最新长测进一步证实长期推进不足。

## 报告与代码

- [docs/results/ht_swept_gate_2026-10-16/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_swept_gate_2026-10-16/REPORT.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-11)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/919d826f340c11e34421a738e80d2a2e85066eb9)

## 2026-10-18后续复核

2026-10-18复核确认本阶段含晚HT拦截仍发布非零候选Twist的缺陷，阶段21修正；历史记录保留，不能由原通过项推断该晚分支正确停车。 [证据与修正](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。这不是对所有历史停滞的统一归因。
