# C02_VS_BASE：同种子配对结果

| seed/对比 | 指标 | 基线 | 候选 | 绝对变化 | 相对变化 |
|---|---|---:|---:|---:|---:|
| baseline_seed42_b01 → queue_seed42_c03 | GT distance m | 5.74360 | 19.70158 | +13.95798 | +243.02% |
| baseline_seed42_b01 → queue_seed42_c03 | Free volume m3 | 525.28000 | 925.35200 | +400.07200 | +76.16% |
| baseline_seed42_b01 → queue_seed42_c03 | HT callback P95 ms | 77.38386 | 83.15638 | +5.77252 | +7.46% |
| baseline_seed42_b01 → queue_seed42_c03 | Producer source age P95 s | 0.72400 | 1.01000 | +0.28600 | +39.50% |
| baseline_seed42_b01 → queue_seed42_c03 | Wall s | 126.13318 | 128.71468 | +2.58149 | +2.05% |
| baseline_seed42_b01 → queue_seed42_c03 | teardown nonzero | {} | {} | — | — |
| baseline_seed99_b02 → queue_seed99_c04 | GT distance m | 5.34231 | 10.36302 | +5.02071 | +93.98% |
| baseline_seed99_b02 → queue_seed99_c04 | Free volume m3 | 508.60800 | 756.06400 | +247.45600 | +48.65% |
| baseline_seed99_b02 → queue_seed99_c04 | HT callback P95 ms | 75.12000 | 77.38393 | +2.26393 | +3.01% |
| baseline_seed99_b02 → queue_seed99_c04 | Producer source age P95 s | 0.72750 | 0.97000 | +0.24250 | +33.33% |
| baseline_seed99_b02 → queue_seed99_c04 | Wall s | 136.22253 | 126.25671 | -9.96582 | -7.32% |
| baseline_seed99_b02 → queue_seed99_c04 | teardown nonzero | {'gazebo': -9} | {'observer': -2} | — | — |

种子只控制TARE采样流/Gazebo，ROS/GPU调度仍有波动；每种子单次配对无法排除调度影响，不宣称统计显著或全场景覆盖。固定场景、配置哈希、命令、实测commit及原始路径见各轮EXPERIMENT_CONTEXT/manifest；环境沿用b00/SEED_SETUP记录。

主源龄指标沿用基线的1Hz生产者性能遥测；DELIVERY_AGE.json额外覆盖MCAP全部已记录HT消息，以录包端最近收到的ROS时钟计算，包含传输/时钟采样，不替换主口径。所有MCAP计数/可用CRC/SHA及视频解码均单独核验。原始大文件仅本地保留，未发布Release。
