# Scout / Helios32 实车外参接入：离线验证记录

日期：2026-10-22。专用分支：`real/scout-helios32`，基于 `8b10207a705d73a00c830872570eabf61748ada5`。本轮只修改代码、构建和离线检查，未启动传感器、仿真或车辆；没有新的探索性能数据或实车通过结论。

## 依据与改动

外参取自用户指定的 `CQULzz/eletranskit_scout@cf0b73d7d01b4b6a2718c7ff3124f4b7a3368c36`。用户明确确认 FP_POI 与 fixposition_link 重合、支架高度 0.1162m 已实车核验。固定源文件路径、SHA256 和派生结果见 [source_evidence.json](source_evidence.json)。没有修改该源仓库的本地工作区。

`T_parent_child` 将 child 中坐标变到 parent；当前旋转均为零：

| 派生变换 | 平移 xyz，m |
|---|---|
| FP_POI → base_link | (-0.2005158179045505, 0, -0.4242) |
| FP_POI → rslidar | (-0.0280158179045505, 0, 0.126) |
| base_link → rslidar | (0.1725, 0, 0.5502) |

新增 [ht_scout_bridge](../../src/ht_scout_bridge) 实际执行以下转换：

- Fixposition 的 ENU/POI 位姿转换成 map/base_link 位姿，随车身旋转应用杆臂；速度包含角速度叉乘杆臂，协方差按参考点传播。
- 雷达点云按扫描原时间查询外部 TF，应用上述外参后发布到 map；保留强度等额外字段，按源配置过滤车体点。仅做整帧刚性配准，没有新增逐点去畸变。
- TF 暂不可用时有界排队等待，不退回最新位姿；外参不一致、定位跳变、时钟倒退会锁定停止。外部工作区仍是唯一 TF 广播方。
- 独立 mapper 参数使用原生 0.04m、291×291 输入，原值接入源 `time` 年龄层，HT 中心裁剪输出 241×241、9.64m 见方。没有把 250×250 缩放成模型输入，也没有将历史年龄填零。

实车 [launch](../../src/ht_scout_bridge/launch/scout_real.launch.py) 仅包含输入适配、已有 HT 推理、TARE 和可选跟踪器。不会启动 CMU 环境、定位/雷达驱动或重复 TF。里程计统一为 `/ht_real/odometry`；导航数据、许可、停止和命令使用 `/ht_real/*`。跟踪器默认关闭；命令为 `TwistStamped`，坐标系 `base_link`。

原跟踪器只增加 `command_frame` 参数，原默认 `vehicle` 保留，实车入口指定 `base_link`。TARE 六个原覆盖/TSP/航点函数的函数体校验通过，参考为已有 ROS2 适配基线 `b6760adb4280b379567c76f4e684ce628e28ef71`；这不表示整个官方 ROS1 项目字节相同。[校验结果](tare_contract.json)

使用独立工作树 `/home/lzz/my test/HT_Explo-scout-real` 和 `build_real/install_real/log_real`，未切换原 HT 工作区分支，未修改 `main/develop`。外部设备/建图工作区通过 ROS 通信，HT 构建不依赖相邻工作区的 install。集成步骤见 [SCOUT.md](../../docs/real_vehicle/SCOUT.md)。

## 验证结果

| 检查 | 结果与证据 |
|---|---|
| 独立构建、安装 | 两个包成功；ROS 可发现各自 install_real 前缀；安装的模块、配置和 launch 与源码一致。[最终构建](build_verified.log) |
| 新实车 Python 测试 | 29 通过；包括旋转杆臂、协方差、点云字段/时间、TF 等待/故障、原生图层转换和真实 HT 模型端到端输入。[日志](tests_final.log) |
| C++ 回归 | 6/6 CTest 目标通过；其中 GTest 80 通过、4 个缺历史录制样本的用例跳过，不能称这些用例已验收。[CTest](cpp_tests_final.log)、[逐项统计](gtest_summary.json) |
| TARE 原函数检查 | 六个函数体 SHA256 一致。[结果](tare_contract.json) |
| launch 静态解析 | 四个消费者节点配置可解析，跟踪器默认关闭，统一输入和独立话题映射通过；未执行节点进程。[结果](launch_contract.json) |
| 已安装入口 | `ros2 launch ... --show-args` 成功，只显示参数，没有启动设备或导航。[输出](installed_launch_arguments.txt) |
| 来源与成品 | 源外参与派生矩阵匹配；运行代码 SHA256、安装前缀及未验证项见 [validation.json](validation.json) |

测试使用本地独立 ROS 域 231。初次构建因 sparse checkout 缺少仓库已有测试 fixture 头文件而失败；首次 C++ 回归另缺已有 collision_points.csv，均从 Git 恢复原样本后通过，没有降低断言。保留 [首次构建日志](build.log) 和 [首次回归日志](cpp_tests.log)。另修正新增包的无效 maintainer 邮箱元数据，使 colcon 正确识别为 `ros.ament_python` 并生成可发现的安装环境；不是通过手动添加邻接 overlay 绕过。

## 离线复现

在本分支工作区根目录、已安装本项目所需 ROS Jazzy / C++ / Python 依赖的终端执行：

```bash
bash scripts/build_real_scout.sh
source /opt/ros/jazzy/setup.bash
source install_real/setup.bash
export ROS_DOMAIN_ID=231
export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
python3 -m pytest -q src/ht_scout_bridge/test
HT_CONFIGURATION_FIXTURE="$PWD/docs/fixes/fixtures/mixed_turn_stop.txt" \
  ctest --test-dir build_real/tare_planner --output-on-failure
python3 scripts/check_tare_waypoint_contract.py
python3 validation/real_vehicle_scout_2026-10-22/check_launch.py
ros2 run ht_scout_bridge check_scout_calibration \
  "$PWD/install_real/ht_scout_bridge/share/ht_scout_bridge/config/scout_extrinsics.yaml"
ros2 launch ht_scout_bridge scout_real.launch.py --show-args
```

以上 ROS 测试会创建本地测试节点，不启动设备、仿真或底盘。依赖包括 ROS Jazzy、grid_map、PCL、OpenCV、仓库内 OR-Tools，以及 NumPy / SciPy / PyYAML / pytest 和已有 HT 推理依赖；本轮环境为 Ubuntu 24.04 / Python 3.12。若使用 sparse checkout，还需保留 `docs/fixes/evidence`、`docs/fixes/fixtures` 与 `docs/results/ht_latency_diagnosis_10min_2026-10-18/geometry_capture`，否则已有回归缺样本。

## 限制与下一步

以下仍为待验证项，不能由本次离线通过推导出实车闭环已可用：

1. 底盘实际命令消息类型、话题、控制权和制动接口尚未验收，跟踪器默认关闭。
2. HT 八方向标定仍为 false，硬概率门槛仍为 0.5；传感器外参核验不等于 HT 方向/地形判别已经标定。
3. 不继承仿真的 1.2m 假定可行启动圆，实车启动半径为 0；车体下缺测可能导致合法的不可执行状态，需要用真实观测评估，不能补成已知自由。
4. 源 `time` 层由 mapper timer 按配置间隔累加，不是逐格硬件绝对观测时钟；高负载下的年龄精度、同步、实际延迟和去畸变需要真实录包验证。
5. 当前适配拒绝需要旋转重投影的高程网格；只支持源仓库当前轴向对齐的 map/odom 链。定位/时间故障要求重启整套建图和导航历史，没有实现自动跨 epoch 恢复。
6. 差速/滑移的实际运动跟随、坡面打滑、HT 对真实地形的准确率均未测量。

后续首先在无底盘输出的真实录包回放中核对 TF、参考点、291 格输入、年龄和 HT 方向；满足这些前提后再核对控制接口。当前用户只授权代码与离线阶段，本报告没有安排实车或仿真自动运行。
