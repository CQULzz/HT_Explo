# 阶段19｜室内视点细化：恢复推进，仍有停顿回访

标签固定源码，验证与问题以本说明为准。C++规划仍为bd0c2c2，HT桥接仍为f1c8485。

## 改了什么

室内视点从50×50、0.6m改为100×100、0.3m，保持30×30m范围；原HT分辨率、概率阈值、足迹半径、运动学搜索和控制速度不变。

## 实现了什么功能

为窄HT支撑带提供候选端点，保留原参数失败视频；新增实际栅格、足迹硬门槛、时间戳与配置归档。

## 实验与验证

独立600秒补测、9000帧完整解码及13项采集/进程核验通过。里程3.11→145.28m，近似观测347.875→1900.25m³，全零指令98.2%→23.0%；运行中实际参数读取与源哈希证明仅室内视点配置不同。

## 存在什么问题

仍有最长39.80秒停车和2.3%倒车；第6至7.5分钟行驶22.94m仅增8.375m³，低收益回访未消失。活跃搜索耗时P95为1.576秒、HT年龄最大4.67秒。隧道返航未知足迹问题未解决；每配置一次，不能视为所有场景通过。

证据：[REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_indoor_sampling_comparison_2026-10-17/REPORT.md) · [REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_indoor_viewpoint_10min_2026-10-17/REPORT.md) · [README.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_multiscene_10min_2026-10-17/indoor/diagnostics/README.md)
