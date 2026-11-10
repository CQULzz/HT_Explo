# 旧实车代码在 CMU AEDE 中的对照

用户于 2026-11-10 要求将之前的实车代码放入同一 CMU 环境，核实效果差异。
本入口只用于仿真，不启动实车传感器、驱动或物理底盘命令桥。

- 旧代码：`origin/real/scout-helios32`，`b97d0fad5d15c0c7c37cec0499312f74afe6dd1d`。
- 参考：最小八方向接入 `d613cf2000202cbeb2c130f6bab26b0ea86e6517` 的 `ht_600s_06`。
- 共同环境、起点、传感器、建图器和统计方法沿用 `tools/cmu_minimal`。
- 旧 TARE、XYθ 路由、跟踪及 HT 处理源码不修改；加载实车原参数。
- 输入适配：CMU 里程计的 `sensor` 原点距地 0.75 m，虚拟 `base_link` 距地 0.23479 m；在测量姿态下施加局部 `[0,0,-0.51521]` 平移，时间戳不变；注册点云已经在 map 系中，不再二次配准。
- 观察杠杆臂改为模拟传感器的 `[0,0,0.51521]`；不套用真实雷达外参。
- 旧跟踪器直接输出 CMU 所需的 TwistStamped `/cmd_vel`，不启动另一套局部控制器。
- 方向检查仍核对旧权重及既有 channel mapping 证据，不宣称完成真实不对称地形标定。

旧版与参考存在明确参数差异：最大速度 0.4/0.5 m/s、HT 半径 0.6/0.45 m、Scout/indoor 采样配置，以及高度证据限定和小孔修补开关。不能直接用里程比值宣称某种融合算法更优。

本机准备：先 source `/home/lzz/cmu_test_20261110/env.sh`，再 source `install_cmu/setup.bash`、`install_mapper/setup.bash` 和 `/home/lzz/cmu_real_compare_20261110/install_old/setup.bash`。Xvfb 使用 `:88`。运行 `python3 tools/cmu_real_compare/run.py --name old_real_600s_01`。

输出在 `/home/lzz/cmu_real_compare_20261110/runs`。每次独立目录，冻结哈希/运行文件、录包、参数、日志、CSV 和状态；失败也保留。完整数据保留本机，未经远端完整核验不清理。结果由报告明确给出，不以入口脚本存在代替实际运行。
