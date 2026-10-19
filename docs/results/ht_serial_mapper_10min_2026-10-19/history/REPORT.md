[合并PDF图册（24页）](all_comparisons.pdf) · [网页图册](index.html) · [全部指标CSV](measurements.csv) · [有效增益与回访CSV](efficiency.csv)

# 历次修改：多角度探索变化对比

按场景分别比较完整600秒记录，失败轮、同版失败复测和阶段34退出异常均保留。统一速度/初始位姿容差检查；不同场景不合并排名。所有体积统一绝对源秒、0.5m自由体素并集近似，旧口径从原始MCAP重新计算，原报告不回写。

没有同一协议600秒数据的早期版本不会补造曲线；1至最新阶段逐项覆盖情况见[版本数据覆盖表](version_data_coverage.csv)。D编号为另存的诊断/未采用候选，具体改动和来源见[完整数据表](measurements.csv)。单次闭环轨迹不构成统计或单项因果证明，体积不是物理覆盖真值。

停车按|v|<0.01m/s且|ω|<0.05rad/s，转向按|v|<0.01且|ω|>0.05；倒车占比是全部消息中v<−0.05的子集。内部COMPLETED不是全环境覆盖真值。旧轮缺失的搜索/晚拒绝审计值留空。

![indoor_01_overview](indoor_01_overview.png)

![indoor_02_curves](indoor_02_curves.png)

![indoor_03_minute_gain](indoor_03_minute_gain.png)

![indoor_04_motion](indoor_04_motion.png)

![indoor_05_latency](indoor_05_latency.png)

![indoor_06_trajectories](indoor_06_trajectories.png)

![indoor_07_mission](indoor_07_mission.png)

![indoor_08_resources](indoor_08_resources.png)

![garage_01_overview](garage_01_overview.png)

![garage_02_curves](garage_02_curves.png)

![garage_03_minute_gain](garage_03_minute_gain.png)

![garage_04_motion](garage_04_motion.png)

![garage_05_latency](garage_05_latency.png)

![garage_06_trajectories](garage_06_trajectories.png)

![garage_07_mission](garage_07_mission.png)

![garage_08_resources](garage_08_resources.png)

![all_versions_01_12](all_versions_01_12.png)

![all_versions_13_24](all_versions_13_24.png)

![all_versions_25_36](all_versions_25_36.png)

![all_versions_37_37](all_versions_37_37.png)

## 每次记录与改动

| ID | 环境 | 改动/目的 | 里程m | 近似体积m³ | 最长停车s | 最终状态 |
|---|---|---|---:|---:|---:|---|
| S18 | garage | 五环境各10分钟与15fps录像（已完成记录） | 189.57 | 4028.250 | 5.00 | EXPLORING |
| S18 | campus | 五环境各10分钟与15fps录像（已完成记录） | 199.76 | 9336.625 | 2.05 | EXPLORING |
| S18 | indoor | 五环境各10分钟与15fps录像（已完成记录） | 3.11 | 347.875 | 567.18 | BLOCKED |
| S18 | forest | 五环境各10分钟与15fps录像（已完成记录） | 168.09 | 13452.500 | 5.00 | EXPLORING |
| S18 | tunnel | 五环境各10分钟与15fps录像（已完成记录） | 26.33 | 402.875 | 496.37 | BLOCKED |
| S19 | indoor | 室内视点细化：恢复推进，仍有停顿回访 | 145.28 | 1900.250 | 39.80 | EXPLORING |
| S20 | tunnel | 观测支撑与停滞恢复：返航通过，探索仍有退步 | 68.86 | 622.250 | 353.34 | COMPLETED |
| S20 | indoor | 观测支撑与停滞恢复：返航通过，探索仍有退步 | 71.57 | 1106.750 | 273.13 | COMPLETED |
| D1 | indoor | 完成触发诊断复跑 | 54.02 | 1099.750 | 369.00 | BLOCKED |
| D2 | indoor | 强制双向支撑候选（未采用） | 20.66 | 702.375 | 515.73 | BLOCKED |
| D3 | indoor | 组合支撑与恢复候选（未采用） | 67.69 | 1218.250 | 123.63 | BLOCKED |
| S21a | indoor | 晚拒绝发零，原航向数 | 40.34 | 1000.125 | 413.58 | BLOCKED |
| S21b | indoor | 晚拒绝发零与32航向 | 6.64 | 432.875 | 570.05 | BLOCKED |
| S21b | tunnel | 晚拒绝发零与32航向 | 79.00 | 621.375 | 373.35 | COMPLETED |
| S22 | indoor | 混合转角与旋转跟踪：室内仍停滞 | 17.82 | 778.000 | 525.23 | BLOCKED |
| S23 | indoor | HT配置得分与物理障碍分层：恢复推进，仍有短停 | 134.00 | 3170.500 | 6.20 | BLOCKED |
| S24 | indoor | 同规则室内诊断复跑：发现几何根状态拒绝 | 23.86 | 993.125 | 519.72 | BLOCKED |
| S25 | indoor | 连续位姿几何检查：旧反例修正，仍有HT未知停滞 | 65.80 | 1959.875 | 335.13 | BLOCKED |
| S26 | indoor | 有限质量拒绝高度保留为硬障碍：里程增加但体积退步 | 116.15 | 1258.000 | 95.02 | BLOCKED |
| S27 | indoor | 等价连续碰撞查询提速：仍因执行进入几何边界停滞 | 41.90 | 815.625 | 463.30 | BLOCKED |
| S28 | indoor | 执行几何与跟踪余量：600秒内部完成并返航，覆盖待核验 | 117.66 | 2292.750 | 249.65 | COMPLETED |
| S29 | indoor | 逐单元审计：正收益任务未登记/移出邻域被核销 | 133.17 | 2025.125 | 86.60 | COMPLETED |
| S30 | indoor | 正收益全局任务保留：600秒169.57m/3321.25m³仍探索 | 169.57 | 3321.250 | 17.50 | EXPLORING |
| S31 | indoor | 候选缺失保留有效收益：核销正确但体积退步 | 162.71 | 2703.875 | 3.70 | EXPLORING |
| S32 | indoor | 相同导航程序复测：早期长期停滞 | 5.66 | 419.750 | 586.04 | BLOCKED |
| S33 | indoor | 普通恢复目标提前搜索 | 151.57 | 2480.000 | 35.80 | EXPLORING |
| S34 | indoor | 先验算简单SE2连接，再做图搜索 | 168.77 | 2169.875 | 3.60 | EXPLORING |
| S35 | indoor | 诊断写入与完整退出，同导航二进制复测 | 169.10 | 2674.750 | 4.20 | EXPLORING |
| S36 | garage | 冻结版本车库600秒与历史统一口径对比 | 187.25 | 7900.375 | 4.95 | EXPLORING |
| S37 | garage | 地图串行执行与独立TF接收，修复调度长等待 | 179.78 | 4522.625 | 1.15 | EXPLORING |

## 有效增益与回访

最后一分钟体积差除以该分钟里程，里程<1m不计算；没有用初始扫描体积抬高每米增益。1m轨迹格按连续进入序列去除原地重复采样，重复进入之前已到访格的次数除以总进入次数（不含起点）；格边界抖动可能影响数值，不是真值覆盖率或全局探索最优性。

![室内有效增益与回访](indoor_09_efficiency.png)

![车库有效增益与回访](garage_09_efficiency.png)
