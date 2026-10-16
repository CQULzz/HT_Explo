# 阶段08：实际XYθ硬约束规划与分层历史高程

**状态：实验里程碑，不是稳定版；尚未完成实车完整验证。**

归档提交：[8398f53](https://github.com/CQULzz/HT_Explo/commit/8398f538450a21c4ee9d65d17193ee084eacee03)。类型：功能。
实际控制/功能来源：[322ec85](https://github.com/CQULzz/HT_Explo/commit/322ec85c728c5900d3e47f22b4c3c5a4e6bccc99)。

## 改了什么

322ec85一次归档此前本地XYθ、历史高程工作及当日修复：引入Hybrid A*和独立执行器，修正坐标翻转、固定世界索引、分层高程和真实观测时间。

## 实现了什么功能

从odom位姿到目标视点规划前进/倒车/原地旋转路径；P≥0.5硬门槛、默认严格未知；全局历史高程裁局部窗口供HT推理。

## 实验与验证

180秒实际HT控车仅行驶14.35米；对应窗口接收984帧、成功融合窗口983帧；225组地图时间戳一致。

## 存在什么问题

运动连续性差、旧许可1.5秒超时导致大量停车，目标反复切换；仍有噪声/未知区，未完成探索或实车验证。10月12日只是本地实验日期，不是独立Git发布。

## 报告与代码

- [docs/XYTHETA_EXPERIMENT_2026-10-12.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/XYTHETA_EXPERIMENT_2026-10-12.md)
- [docs/HISTORICAL_ELEVATION_EXPERIMENT_2026-10-12.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/HISTORICAL_ELEVATION_EXPERIMENT_2026-10-12.md)
- [docs/ELEVATION_MAPPING_FIXES_2026-10-15.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/ELEVATION_MAPPING_FIXES_2026-10-15.md)
- [docs/results/ht_validation_2026-10-15/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_validation_2026-10-15/REPORT.md)
- [全部版本对照](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/VERSIONS.md#stage-08)
- [该阶段源码](https://github.com/CQULzz/HT_Explo/tree/8398f538450a21c4ee9d65d17193ee084eacee03)
