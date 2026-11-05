# C02_VS_C01：同种子配对结果

| seed/对比 | 指标 | 基线 | 候选 | 绝对变化 | 相对变化 |
|---|---|---:|---:|---:|---:|
| threshold_seed42_c01 → queue_seed42_c03 | GT distance m | 4.61112 | 19.70158 | +15.09045 | +327.26% |
| threshold_seed42_c01 → queue_seed42_c03 | Free volume m3 | 460.92000 | 925.35200 | +464.43200 | +100.76% |
| threshold_seed42_c01 → queue_seed42_c03 | HT callback P95 ms | 76.76592 | 83.15638 | +6.39046 | +8.32% |
| threshold_seed42_c01 → queue_seed42_c03 | Producer source age P95 s | 0.73500 | 1.01000 | +0.27500 | +37.41% |
| threshold_seed42_c01 → queue_seed42_c03 | Wall s | 126.18647 | 128.71468 | +2.52821 | +2.00% |
| threshold_seed42_c01 → queue_seed42_c03 | teardown nonzero | {} | {} | — | — |
| threshold_seed99_c02 → queue_seed99_c04 | GT distance m | 6.76005 | 10.36302 | +3.60297 | +53.30% |
| threshold_seed99_c02 → queue_seed99_c04 | Free volume m3 | 560.92800 | 756.06400 | +195.13600 | +34.79% |
| threshold_seed99_c02 → queue_seed99_c04 | HT callback P95 ms | 74.13503 | 77.38393 | +3.24890 | +4.38% |
| threshold_seed99_c02 → queue_seed99_c04 | Producer source age P95 s | 0.76750 | 0.97000 | +0.20250 | +26.38% |
| threshold_seed99_c02 → queue_seed99_c04 | Wall s | 128.58096 | 126.25671 | -2.32425 | -1.81% |
| threshold_seed99_c02 → queue_seed99_c04 | teardown nonzero | {} | {'observer': -2} | — | — |

种子只控制TARE采样流/Gazebo，ROS/GPU调度仍有波动；每种子单次配对无法排除调度影响，不宣称统计显著或全场景覆盖。固定场景、配置哈希、命令、实测commit及原始路径见各轮EXPERIMENT_CONTEXT/manifest；环境沿用b00/SEED_SETUP记录。

主源龄指标沿用基线的1Hz生产者性能遥测；DELIVERY_AGE.json额外覆盖MCAP全部已记录HT消息，以录包端最近收到的ROS时钟计算，包含传输/时钟采样，不替换主口径。所有MCAP计数/可用CRC/SHA及视频解码均单独核验。原始大文件仅本地保留，未发布Release。
