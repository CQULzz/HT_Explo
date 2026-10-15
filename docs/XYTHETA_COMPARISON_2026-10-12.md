# Garage XYθ 探索对比（2026-10-12）

![四次 Garage 实验的距离与新增探索体积](../../ht_cupy_bridge_ws/results/xytheta_comparison_2026-10-12/garage_xytheta_comparison.png)

这次实验保持 HT 硬门槛、XYθ 搜索及 0.5 m/s 前进速度上限，仅把独立跟踪器的许可超时从 0.5 秒改为 1.5 秒。CMU Garage、CuPy 高程图和 HT 桥接器在各自独立工作空间运行；CMU 原 `pathFollower` 没有启动。为接近上一轮 90 秒实验的 `(0.30, 3.53)`，先在仿真中将车移到 `(0.34, 3.36)`，等待地图建立，然后**先启动记录器、后启动 TARE**；预移动不计入数据。本轮记录器从任务第一次进入探索状态即开始采样。

曲线从各次实验第一帧有效注册点云起算，并把该时刻的距离和自由体积置为零。体积口径相同：0.5 米体素中，被有效注册雷达光线穿过的不同自由体素累计体积。由于历史实验的初始地图、视点选择和局部路径不完全相同，此图是观察性对比，不能把所有差异都归因于许可超时。橙线仅有 45 秒记录。

| Garage 实验 | 30 秒行驶 | 30 秒新增体积 | 约 90 秒行驶 | 约 90 秒新增体积 | 结束状态 |
|---|---:|---:|---:|---:|---|
| 早期硬门槛、旧跟踪器 | 0.48 m | 66 m³ | 0.48 m | 66 m³ | 停车 |
| 进展视点原型、旧跟踪器 | 1.54 m | 86 m³ | — | — | 45 秒仍探索 |
| 上一轮 XYθ、0.5 秒许可超时 | 2.06 m | 246 m³ | 5.39 m | 463 m³ | 90 秒时仍探索，随后停车 |
| 本轮 XYθ、1.5 秒许可超时 | **6.26 m** | **555 m³** | **6.26 m** | **555 m³** | 约 21.5 秒后停车 |

本轮前 30 秒行驶距离约为上一轮的 **3.0 倍**，新增自由体积约为 **2.3 倍**，与单独的控制器对照测试一致：旧的 0.5 秒超时在 TARE 的 1 Hz 许可周期中造成反复停车。但速度提高没有转化为持续 90 秒探索。本轮约 21.5 秒时先出现一条 `HT_MAP_STALE` 状态；地图随后继续更新，TARE 日志持续显示 `HT_start=3`（`BLOCKED`）、`collision=0`，XYθ 搜索在起点拒绝动作并撤销行驶许可。诊断窗口内收到 124 张 HT 图，最大间隔 1.433 秒、最大消息年龄 0.658 秒、地图中心有效率 100%。现有记录不能判断当前位置的低概率是地形真实风险、感知变化还是车身覆盖检查的保守误判。不能通过忽略硬门槛来宣称任务成功。

对比图：[PNG](../../ht_cupy_bridge_ws/results/xytheta_comparison_2026-10-12/garage_xytheta_comparison.png) · [SVG](../../ht_cupy_bridge_ws/results/xytheta_comparison_2026-10-12/garage_xytheta_comparison.svg)；[对比表](../../ht_cupy_bridge_ws/results/xytheta_comparison_2026-10-12/comparison_summary.csv)；[本轮逐秒数据](../../ht_cupy_bridge_ws/results/xytheta_permission_fixed_garage_synced_2026-10-12/timeseries.csv)和[诊断](../../ht_cupy_bridge_ws/results/xytheta_permission_fixed_garage_synced_2026-10-12/diagnostics.json)。
