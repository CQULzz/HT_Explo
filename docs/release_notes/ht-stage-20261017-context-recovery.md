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
