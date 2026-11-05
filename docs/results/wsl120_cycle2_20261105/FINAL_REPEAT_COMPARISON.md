# FINAL_REPEAT：同种子配对结果

| seed/对比 | 指标 | 基线 | 候选 | 绝对变化 | 相对变化 |
|---|---|---:|---:|---:|---:|
| threshold_seed42_c01 → retained_repeat42_r01 | GT distance m | 4.61112 | 4.68741 | +0.07629 | +1.65% |
| threshold_seed42_c01 → retained_repeat42_r01 | Free volume m3 | 460.92000 | 495.92000 | +35.00000 | +7.59% |
| threshold_seed42_c01 → retained_repeat42_r01 | HT callback P95 ms | 76.76592 | 72.92650 | -3.83942 | -5.00% |
| threshold_seed42_c01 → retained_repeat42_r01 | Producer source age P95 s | 0.73500 | 0.70000 | -0.03500 | -4.76% |
| threshold_seed42_c01 → retained_repeat42_r01 | Wall s | 126.18647 | 126.14150 | -0.04497 | -0.04% |
| threshold_seed42_c01 → retained_repeat42_r01 | teardown nonzero | {} | {} | — | — |

种子只控制TARE采样流/Gazebo，ROS/GPU调度仍有波动；每种子单次配对无法排除调度影响，不宣称统计显著或全场景覆盖。固定场景、配置哈希、命令、实测commit及原始路径见各轮EXPERIMENT_CONTEXT/manifest；环境沿用b00/SEED_SETUP记录。

主源龄指标沿用基线的1Hz生产者性能遥测；DELIVERY_AGE.json额外覆盖MCAP全部已记录HT消息，以录包端最近收到的ROS时钟计算，包含传输/时钟采样，不替换主口径。所有MCAP计数/可用CRC/SHA及视频解码均单独核验。原始大文件仅本地保留，未发布Release。
