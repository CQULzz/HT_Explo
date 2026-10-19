# 同场景版本10分钟对比

各组600秒；同场景原生起点、相同速度上限和体积统计定义。计时起点允许5cm/0.02rad差异，实际位姿保存在JSON中。不同闭环轨迹的单次试验，不能独立归因或证明普遍优劣。
体积是0.5m自由体素并集近似，不是真值覆盖率。平移速度为零也可能是在原地转向。

| 版本 | 代码 | 里程(m) | 观测自由体积(m³) | 最终状态 | BLOCKED抽样占比 | 规划P95(s) |
|---|---|---:|---:|---|---:|---:|
| 阶段39 | `6fc7549` | 199.69 | 6483.000 | EXPLORING | 0.0% | 0.511 |
| 阶段40 原TARE+HT | `42966cb` | 192.93 | 8467.000 | EXPLORING | 0.0% | 0.455 |
| 阶段41 接口修正 | `6870131` | 181.31 | 8660.125 | EXPLORING | 0.0% | 0.431 |

![体积、里程、速度和轨迹对比](comparison.png)

原始目录、输入CSV和记录校验文件的哈希保存在[comparison.json](comparison.json)。
视频、原始MCAP与地图快照在各运行目录；历史结果中的精选归档可能只含视频、CSV和末段快照。

- 阶段39：`/home/lzz/my test/HT_Explo-fixposition/docs/results/ht_successor_pruning_10min_2026-10-20/garage`

- 阶段40 原TARE+HT：`/home/lzz/my test/HT_Explo-fixposition/docs/results/ht_tare_waypoint_10min_2026-10-20/garage`

- 阶段41 接口修正：`/home/lzz/my test/HT_Explo-fixposition/presentations/scheduled_results/ht_tare_boundaries_10min_2026-10-20_02-29-24/garage`
