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

第一轮返航BLOCKED；已补容差回归，但最新一轮未触发返航，不能称闭环通过。尚未重跑60分钟；地图年龄最高4.17秒，仍有过期停车。没有真值全域覆盖率或实车验收。 体积是抽样点云射线的自由体素并集近似，不是官方覆盖率。两轮不是严格单一改动消融。
