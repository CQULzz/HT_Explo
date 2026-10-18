# 同场景版本10分钟对比

各组600秒；同场景原生起点、相同速度上限和体积统计定义。计时起点允许5cm/0.02rad差异，实际位姿保存在JSON中。不同闭环轨迹的单次试验，不能独立归因或证明普遍优劣。
体积是0.5m自由体素并集近似，不是真值覆盖率。平移速度为零也可能是在原地转向。

| 版本 | 代码 | 里程(m) | 观测自由体积(m³) | 最终状态 | BLOCKED抽样占比 | 规划P95(s) |
|---|---|---:|---:|---|---:|---:|
| 16航向＋停车修复 | `37f0d42` | 40.34 | 1000.125 | BLOCKED | 70.3% | 0.874 |
| 32航向＋单转角 | `67ade71` | 6.64 | 432.875 | BLOCKED | 94.8% | 0.912 |
| 混合转角＋旋转跟踪 | `12d85d8` | 17.82 | 778.000 | BLOCKED | 88.0% | 0.831 |
| 本轮：HT与物理障碍分层 | `149566d` | 134.00 | 3170.500 | BLOCKED | 7.8% | 1.616 |

![体积、里程、速度和轨迹对比](comparison.png)

原始目录、输入CSV和记录校验文件的哈希保存在[comparison.json](comparison.json)。
视频、原始MCAP与地图快照在各运行目录；历史结果中的精选归档可能只含视频、CSV和末段快照。

- 16航向＋停车修复：`/home/lzz/my test/HT_Explo-fixposition/docs/results/ht_zero_twist_only_10min_2026-10-18/indoor`

- 32航向＋单转角：`/home/lzz/my test/HT_Explo-fixposition/docs/results/ht_zero_twist_fine_heading_10min_2026-10-18/indoor`

- 混合转角＋旋转跟踪：`/home/lzz/my test/HT_Explo-fixposition/docs/results/ht_mixed_turns_10min_2026-10-18/indoor`

- 本轮：HT与物理障碍分层：`/home/lzz/my test/HT_Explo-fixposition/docs/results/ht_configuration_gate_10min_2026-10-18/indoor`
