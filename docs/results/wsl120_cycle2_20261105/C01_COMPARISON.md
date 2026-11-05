# C01：同种子配对结果

| seed/对比 | 指标 | 基线 | 候选 | 绝对变化 | 相对变化 |
|---|---|---:|---:|---:|---:|
| baseline_seed42_b01 → threshold_seed42_c01 | GT distance m | 5.74360 | 4.61112 | -1.13247 | -19.72% |
| baseline_seed42_b01 → threshold_seed42_c01 | Free volume m3 | 525.28000 | 460.92000 | -64.36000 | -12.25% |
| baseline_seed42_b01 → threshold_seed42_c01 | HT callback P95 ms | 77.38386 | 76.76592 | -0.61794 | -0.80% |
| baseline_seed42_b01 → threshold_seed42_c01 | Producer source age P95 s | 0.72400 | 0.73500 | +0.01100 | +1.52% |
| baseline_seed42_b01 → threshold_seed42_c01 | Wall s | 126.13318 | 126.18647 | +0.05329 | +0.04% |
| baseline_seed42_b01 → threshold_seed42_c01 | teardown nonzero | {} | {} | — | — |
| baseline_seed99_b02 → threshold_seed99_c02 | GT distance m | 5.34231 | 6.76005 | +1.41773 | +26.54% |
| baseline_seed99_b02 → threshold_seed99_c02 | Free volume m3 | 508.60800 | 560.92800 | +52.32000 | +10.29% |
| baseline_seed99_b02 → threshold_seed99_c02 | HT callback P95 ms | 75.12000 | 74.13503 | -0.98497 | -1.31% |
| baseline_seed99_b02 → threshold_seed99_c02 | Producer source age P95 s | 0.72750 | 0.76750 | +0.04000 | +5.50% |
| baseline_seed99_b02 → threshold_seed99_c02 | Wall s | 136.22253 | 128.58096 | -7.64157 | -5.61% |
| baseline_seed99_b02 → threshold_seed99_c02 | teardown nonzero | {'gazebo': -9} | {} | — | — |
种子只控制TARE采样流/Gazebo，ROS/GPU调度仍有波动；每种子单次配对无法排除调度影响，不宣称统计显著或全场景覆盖。固定场景、配置哈希、命令、实测commit及原始路径见各轮EXPERIMENT_CONTEXT/manifest；环境沿用b00/SEED_SETUP记录。

主源龄指标沿用基线的1Hz生产者性能遥测；DELIVERY_AGE.json额外覆盖MCAP全部已记录HT消息，以录包端最近收到的ROS时钟计算，包含传输/时钟采样，不替换主口径。所有MCAP计数/可用CRC/SHA及视频解码均单独核验。原始大文件仅本地保留，未发布Release。
