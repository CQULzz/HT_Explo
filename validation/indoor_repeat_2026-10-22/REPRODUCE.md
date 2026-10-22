# 室内同版本复跑与原因核对

实测标签`ht-sim-20261022-indoor-repeat`，提交`0087a008f9d8beb26f2efa636f65fbf3e940a268`。运行源码/二进制未相对上次e640c0c修改；测前133个运行文件及上轮72项manifest输入核验见frozen_inputs.json。实际参数与测后检查见docs/results/ht_indoor_repeat_2026-10-22/repeat_equivalence.json。本轮没有新编译导航或再次宣称运行前轮的单元测试。

在独立sim工作树、只source系统ROS环境运行（新输出目录必须不存在）：

```bash
source /opt/ros/jazzy/setup.bash
python3 presentations/run_ht_multiscene.py --duration 600 --scenarios indoor --domain 226 \
  --encoder /home/lzz/.cache/ht-report-tools/python/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2 \
  --output "$PWD/presentations/scheduled_results/ht_indoor_repeat_2026-10-22"
```

另一个终端在同一域只读抓取参数：

```bash
source /opt/ros/jazzy/setup.bash
ROS_DOMAIN_ID=226 ROS_LOCALHOST_ONLY=1 python3 validation/sim_check_2026-10-22/capture_parameters.py \
  --wait-file presentations/scheduled_results/ht_indoor_repeat_2026-10-22/indoor/current/measurement_started.json \
  --output presentations/scheduled_results/ht_indoor_repeat_2026-10-22/indoor/current/effective_parameters
```

独立CMU/CuPy工作区由各进程单独加载，不在HT工作树内合并或编译；详情继承validation/sim_check_2026-10-22/REPRODUCE.md。未启动实车。测量期间只进行了读取既有数据的轻量、nice15离线分析，未改本轮运行文件。

600秒采集、视频及退出检查完成后：

```bash
source /opt/ros/jazzy/setup.bash
python3 presentations/archive_ht_multiscene.py presentations/scheduled_results/ht_indoor_repeat_2026-10-22 \
  --scenarios indoor --output docs/results/ht_indoor_repeat_2026-10-22
python3 presentations/compare_ht_iterations.py \
  --run '上次HT（同一运行版本）=docs/results/ht_sim_check_2026-10-22/indoor' \
  --run '本次HT重复=docs/results/ht_indoor_repeat_2026-10-22/indoor' \
  --output docs/results/ht_indoor_repeat_2026-10-22/same_version_comparison
python3 validation/sim_check_2026-10-22/assess_runs.py \
  --suite presentations/scheduled_results/ht_indoor_repeat_2026-10-22 \
  --output docs/results/ht_indoor_repeat_2026-10-22
python3 presentations/audit_ht_mission_commands.py presentations/scheduled_results/ht_indoor_repeat_2026-10-22/indoor \
  --output docs/results/ht_indoor_repeat_2026-10-22/indoor/mission_commands.json
source install_standalone/setup.bash  # 仅给离线解码加载本工作树grid_map_msgs
python3 validation/indoor_repeat_2026-10-22/extract_candidates.py \
  presentations/scheduled_results/ht_sim_check_2026-10-22/indoor \
  --output validation/indoor_repeat_2026-10-22/previous_early_candidates --until 35
python3 validation/indoor_repeat_2026-10-22/extract_candidates.py \
  presentations/scheduled_results/ht_indoor_repeat_2026-10-22/indoor \
  --output validation/indoor_repeat_2026-10-22/repeat_early_candidates --until 35
python3 validation/indoor_repeat_2026-10-22/audit_transition.py validation/indoor_repeat_2026-10-22/previous_early_candidates
python3 validation/indoor_repeat_2026-10-22/audit_connectivity.py validation/indoor_repeat_2026-10-22/previous_early_candidates
python3 validation/indoor_repeat_2026-10-22/audit_connectivity.py validation/indoor_repeat_2026-10-22/previous_early_candidates --latest-at-publication
python3 validation/indoor_repeat_2026-10-22/write_report.py
```

归档和对比工具拒绝覆盖既有输出；复现需新目录并相应调整路径。write_report.py为本轮固定路径报告器；运行前需将两个提取目录拷入结果归档diagnosis/。assess_runs.py保留原轮泛化文案/链接，必须由本轮write_report.py重写REPORT后再发布。关键结论来自逐项JSON，不以继承文案代替证据。图中历史原TARE/HT由该工具核验源秒选择及同一指标定义，并未本轮重跑。

地图/图诊断限制：原生map帧、configuration分数、0.5阈值、0.6m半径，对应本次实际参数；简化图只有三帧已发布候选并集，省略高度、LOS和未发布的拒绝节点，不是完整规划器/车辆可行路线重放。门槛地图取日志推算视点阶段结束前最新bag接收，不能冒称内部pointer精确捕获。未对齐的latest-at-publication结果作为反例独立保存。

代码定位：

- src/tare_planner/src/viewpoint_manager/viewpoint_manager.cpp：RefreshHTTerrainMask、CheckViewPointConnectivity、GetViewPointCandidate。
- src/tare_planner/src/ht_cost/ht_cost_map.cpp：terrainGuidanceAllowed、terrain_history_聚合；最新物理车体障碍与历史粗格门槛。
- src/tare_planner/src/local_coverage_planner/tare_original.cpp：SolveTareCoverageProblem的local_coverage_complete_条件。
- src/tare_planner/src/local_coverage_planner/local_coverage_planner.cpp：EnqueueViewpointCandidates和random_device采样。
- src/tare_planner/src/sensor_coverage_planner/sensor_coverage_planner_ground.cpp：execute中的完成锁定和后续ResetViewPointCoverage分支。

完整新raw在本轮Release；上一轮raw在ht-sim-20261022-input-contracts Release；压缩NPZ诊断缓存放本轮results附件，不写Git。发布后需逐附件大小和SHA256核验。原始输入为抽样录制，不能宣称全频无损传感器包。
