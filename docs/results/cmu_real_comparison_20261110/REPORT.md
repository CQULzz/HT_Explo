# 旧实车代码在 CMU AEDE 中的测试报告

实测结果：旧实车版可以行驶、转弯和返航，但在本轮场景里只探索了起点附近的一小段区域，就按自己的候选任务集合判定完成。181.85 秒进入返航，223.61 秒进入 COMPLETED，剩余 376.39 秒保持停车。它与新版的差距，直接表现为任务较早结束，不能归结为八方向模型一直拦车。

| 指标 | 旧实车版 b97d0fa | 最小八方向版 d613cf2 |
|---|---:|---:|
| 正式采集时间 | 600.004 秒 | 600.003 秒 |
| 实际积分里程 | 64.032 米 | 281.925 米 |
| 采样自由体积 | 980.125 m³ | 5408.000 m³ |
| 结束状态 | COMPLETED，在家停车 | 仍探索，finish=false |
| HT 发布源龄 P95 | 0.428 秒 | 0.338 秒 |

自由体积是相同统计程序对传感器射线的采样并集，分辨率 0.5 m、最多 1 Hz、1024 条射线、12 m 范围；它是观测代理指标，不是真值覆盖率。两轮匹配射线帧数分别为486/463，传感器及统计订阅存在不同程度的消息采样/丢失，不能把体积比值当作精确覆盖提升比例。

**停车原因有直接证据。** 首次完成判断前一轮还输出 native waypoint=(2.901,15.550)；随后日志变成 `global_return=1 local_complete=1 global_order_nodes=0 uncovered=0 frontier=9`。当前未访问候选的 `raw_gain=0 raw_frontier=0`，局部覆盖选择器给出 `complete=1`，系统据此返航。[关键原始日志](first_completion.log)保留了完整上下文。`frontier=9` 本身不足以证明还有达到增益门限、已经确认可达的任务，因此本报告没有把它直接定性为“忽略已确认任务”的代码缺陷，也没有据 COMPLETED 宣称整个场景已探索完。

旧跟踪器在采集期的状态持续时间约为：DRIVING 184.03 秒、TURNING 19.20 秒、初始 PATH_STALE 12.76 秒、PLANNER_HOLD 5.15 秒、SCAN_STALE 1.53 秒、HT_COMMAND_BLOCKED 0.128 秒、COMPLETED 376.39 秒，其余为短暂对齐。持续停车由任务完成驱动。旧版 HT 发布源龄 P99 约0.502秒，地图持续更新，不能解释成数百秒的地图失效或推理崩溃。MCAP 中的状态、命令另行核对，结果见 [BAG_STATE_CHECK.json](BAG_STATE_CHECK.json)。

**旧版把 HT 接进了 TARE 的任务生成。** `HtCostMap` 会把模型方向分数及物理占据合成为0.2米地形历史；`RefreshHTTerrainMask()` 将这些结果用于视点连通性和候选筛选。TARE 在这个候选集合上做覆盖、TSP及完成判断，再由 XYθ 路由和跟踪器执行。因此“当前 HT 指导下没有候选任务”能够一路影响到“完成并返航”。新版保留上游 TARE 的目标、覆盖及返航流程，八方向检查落在 CMU 局部路径及最终命令上，不把 HT 地形历史反馈给 TARE 候选集。改动范围的差别已由源码确认。

可核对的旧源码位置：[HT地形历史](https://github.com/CQULzz/HT_Explo/blob/b97d0fad5d15c0c7c37cec0499312f74afe6dd1d/src/tare_planner/src/ht_cost/ht_cost_map.cpp#L350)、[候选连通性筛选](https://github.com/CQULzz/HT_Explo/blob/b97d0fad5d15c0c7c37cec0499312f74afe6dd1d/src/tare_planner/src/viewpoint_manager/viewpoint_manager.cpp#L846)、[候选视点筛选](https://github.com/CQULzz/HT_Explo/blob/b97d0fad5d15c0c7c37cec0499312f74afe6dd1d/src/tare_planner/src/viewpoint_manager/viewpoint_manager.cpp#L1305)、[完成判断与返航锁存](https://github.com/CQULzz/HT_Explo/blob/b97d0fad5d15c0c7c37cec0499312f74afe6dd1d/src/tare_planner/src/sensor_coverage_planner/sensor_coverage_planner_ground.cpp#L1817)。完成后 `kNoExplorationReturnHome=true` 使覆盖更新停止，这也解释了后半段不会重新发现候选并恢复探索。

**实车参数与 CMU 参数也不同。** 这轮保留旧实车配置，以回答“之前代码实际跑起来怎样”；没有把多个参数同时改掉后再称为原状。具体差异如下。

| 参数/路径 | 旧实车版 | 最小八方向版 |
|---|---|---|
| 最大前进速度 | 0.4 m/s | 0.5 m/s |
| HT 物理支撑/占据检查半径 | 0.60 m | 0.45 m，与CMU原局部规划器一致 |
| TARE 视点间距/数量 | 1.2 m，40×40 | 0.6 m，50×50 |
| TARE 几何碰撞余量 | 0.7 m | 上游 indoor 的0.5 m |
| Frontier 聚类最小数量 | 30 | 10 |
| HT高度证据限定/小孔修补 | 开/开，moderate | 关/关 |
| HT上下文/线程 | CUDA/4 | NumPy/2，模型仍CUDA |
| 局部规划与执行 | XYθ搜索＋自有跟踪器 | CMU路径组＋原跟踪器＋八方向门禁 |

较低速度会减少里程，较大半径/碰撞余量及较稀的视点格点会影响窄通道和拐角的候选；HT地形历史又会反馈给任务集合。即使只看返航前181.8秒，旧版约54.10米，新版约85.67米，说明结束时刻以外还有速度、跟踪和路线选择差异。但本轮没有做同参数消融，不能声称已经证明是哪一个参数或哪一行筛选造成了首次任务耗尽，更不能把64/282米包装成纯算法性能排名。

**接入范围。** 旧源码为 `origin/real/scout-helios32@b97d0fad5d15c0c7c37cec0499312f74afe6dd1d`，独立编译，业务源码未修改。共同环境为 CMU AEDE `158e67b` 的 indoor、同一起点、与上一轮一致的64线向下观察传感器配置及4 Hz elevation mapper。此传感器配置不是CMU默认16线，也不是Helios实测标定。模拟点云已经在map系，直接转接；CMU sensor里程计经过局部z=-0.51521 m刚体变换得到虚拟base_link，保留原始测量时间；观察杠杆臂使用模拟传感器的[0,0,0.51521]，不套实车外参。旧模型本轮接收的里程计均来自该base_link适配器，TARE/跟踪器启用了base_link检查；模型单独运行时自身child-frame检查沿用空字符串默认值。HT权重哈希与既有方向映射证据核对通过，未宣称完成真实地形方向标定。

未启动物理传感器/底盘驱动，未测试实车外部定位配准、真实雷达盲区或真实制动。仿真适配器直接将旧跟踪器 TwistStamped 接到 CMU `/cmd_vel`，没有并行启动另一套局部控制器。该轮是两个现有接入方案的单场景诊断，规划随机性及调度没有做重复试验控制。

**验证与产物。** 正式采集完整、冻结哈希未变化；59项既有gtest通过，另有HT核心可执行检查通过，细节见[PREFLIGHT.json](PREFLIGHT.json)。MCAP 15.4 GiB、613.09秒（含准备段）、229370条已录制消息，逐文件SHA256保留。仓库文本副本仅规范行尾空白，CSV数值未改。完整运行日志、地图、参数、MCAP、冻结文件及失败的环境预检记录都在本机 `/home/lzz/cmu_real_compare_20261110`，未创建Release，未做完整远端数据备份，不清理。

600秒内没有子进程提前死亡。停止录包后的SIGINT清理仍出现CMU terrain/vehicle节点context失效退出-6，sensorScanGeneration退出-11；TARE/跟踪等也有SIGINT退出-2。外层launch返回0不表示所有子进程干净退出；这些退出问题发生在采集结束后，解释不了181秒的返航，但仍是保留的缺陷。启动实体生成前还出现过robot尚不存在的Gazebo日志，发生在正式采集起点之前。

[轨迹对比](trajectory_comparison.png) · [里程/观测体积/源龄/状态](progress_comparison.png) · [数值分析](ANALYSIS.json) · 10倍速轨迹视频（本机 /home/lzz/cmu_real_compare_20261110/delivery/recorded_comparison_10x.mp4）。视频由实际轨迹数据绘制，601帧、60.1秒，完整解码通过，不是Gazebo/RViz录屏。

本轮给出的判断是：继续以原TARE加局部八方向约束为主线更符合交付目标。旧版的候选生成反馈、实车采样配置和XYθ执行链需要分别审计；目前没有证据支持把这些改动整套搬回去。旧版任务耗尽的具体首因尚未通过同参对照隔离，本轮不再自动开启新的候选或额外仿真。
