# 实车接口与时序：评估及离线修正

结论：旧报告关于QoS、里程计入口、时序和输入校验的判断有依据；“缺少配准链”只能指仓库自带入口。用户确认已有外部配准与标定，不能据仓库文件推断整套实车系统缺少它。当前补齐内部接口与故障处理，但仍未完成实车闭环验收。未启动仿真、设备或车辆。

## 逐项评估与改动

| 原判断 | 评估 | 本次处理 |
|---|---|---|
| 原始雷达未接通地图系点云 | 对自带launch成立；外部链路存在，具体总launch/TF待提供 | 不增加重复配准/SLAM；新增统一的外部里程计、registered_scan、高程图、HT话题参数；独立安装HT桥接与模型，并加入可开关的桥接/跟踪节点 |
| Fixposition定位QoS不兼容，三处里程计不统一 | 代码确认；best-effort发布无法满足原reliable订阅 | 规划器及跟踪器改为传感器QoS；桥接沿用best-effort；三者由同一launch参数接收同一里程计，可选检查child_frame。实际best-effort发布/订阅回调测试通过 |
| 点云采用最新位置，未按扫描时刻绑定 | 对入图参考位置和关键帧成立；不等于外部已配准点云坐标必然错误 | 使用位姿缓存：默认100ms以内的前后位姿插值，或50ms内最近位姿；最多缓存10帧先到的扫描，后到里程计触发重试；匹配失败不刷新last-good时刻，最终由原新鲜度门槛停用 |
| 固定50ms无法约束真实间隔下的指令变化 | 成立；定时器标称周期不是每次真实发送间隔 | 由上次publish结束到本次限幅计算之间的单调时间计算dt；大间隔最多按50ms计，避免追赶式增量。早于/等于参考时刻为0；publish后更新参考；故障零速仍绕过普通减速度限制 |
| 定位跳变、时间倒退后会继续复用旧状态 | 缺少统一重置机制的判断成立；未证明实车已经出现该故障 | 乱序/重复消息丢弃；明显位置/姿态跳变或ROS时钟回退时锁定停用，要求完整外部建图+导航链重启/重置；不假装只清一张历史图即可完成全链路恢复 |
| 非法姿态和规划参数可能被接受 | follower部分字段与XYθ部分尺度参数确认缺校验 | 检查map/可选child、有限位置和单位四元数、Path内各Pose；补充8个规划尺度参数的有限/正值检查；角度归一化对Inf拒绝，对极大有限角度不再循环减法 |
| 分辨率291→241宜先保留 | 接口兼容性有依据，不能据此证明实车最优 | 输入输出大小、中心裁剪、米/格、模型与权重均未改；不修改HT校准门槛 |

**本次再次审查发现的反例：**仅增加时间匹配并立即丢弃无匹配点云，可能因点云总是先于对应里程计到达而持续丢扫描。已在最终版本补上等待队列，并直接调用真实规划器输入回调测试该到达顺序；没有据最初实现就宣称修复完整。

定位跳变判据为位移>0.75m+3m/s×dt，或转角>0.5rad+4rad/s×dt；四元数q/-q不视为跳变。它是保守启发式，不能检出所有细小重定位、原点变化或传感器故障。乱序包与ROS时钟回退分开处理，单个晚到包不会被当作地图重定位。

## 验证结果

- C++全量增量构建成功；CTest **6/6目标通过**。GTest实际**79项通过、4项缺历史fixture跳过**；另有既有核心检查程序通过。跳过项见[validation.json](validation.json)，不宣称覆盖了所有历史捕获地图。
- Python **72项通过**：畸形高程、循环索引、合法输入发布、历史融合/质量、地面参考以及新里程计状态检查。新增实桥回调测试确认旧地图不会回退融合时间，跳变后不继续发布旧历史推理结果。
- 新增C++用例：时间插值/航向跨±180°、乱序与间隙、明显跳变、单调时间限幅、参数NaN/Inf；真实规划器回调的先扫描后里程计与队列上限；follower best-effort接收、坏frame/四元数、跳变锁定、坏路径，以及测试时钟倒退后仍锁定。
- 原TARE **6个覆盖/探索函数体与原参考哈希一致**。没有改覆盖/TSP访问顺序。
- launch静态求值验证三处共享外部输入、禁用重复驱动、桥接/跟踪开关；**没有执行launch动作**。安装后的桥接入口、同目录模块和权重与源码逐字节一致。
- ROS组件测试使用合成消息和测试时钟，隔离于ROS域231，跟踪指令重映射到`/offline_test/*`。检查结束后没有仿真、导航或设备驱动进程遗留。

初次Python检查因PYTHONPATH覆盖ROS路径导致收集失败，已保留ROS路径后重跑；launch检查脚本曾错误假设executable为替换列表，C++新增测试曾误用Python风格to_msg，均已修正后完成最终验证。构建仍有已有源码告警，不作为无告警构建宣称。具体日志与结果保留在本目录。

## 接入边界与待补资料

1. 用户将提供的实际总launch、TF树、雷达外参，以及Fixposition POI/`vrtk_link`与规划车体参考点定义。话题统一不会自动完成参考点平移/旋转；`odometry_child_frame`只有配置后才检查指定child。
2. 外部点云逐点去畸变、map系转换、真实传感器原点与规划参考点关系仍由该链路决定。本次修的是入图参考时刻，不宣称补齐了外部SLAM或去畸变。
3. 底盘实际消费的命令话题/消息类型待总launch核对；当前follower输出`geometry_msgs/TwistStamped`，不能推断底盘已接收。`start_follower`可关闭，防止与已有控制器并存；四个启动开关默认为true。
4. 外参已标定不等于HT八方向和车辆参考点已核验；`ht_directions_calibrated=false`仍保留，不自行改true。
5. 没有真实录包、地形标注及完整训练规格，不能确认模型实车精度或动力学安全；本轮没有600秒仿真或实车通过结论。候选保存在开发分支，不替换main中已有实验的导航基线。

## 复核命令

只执行构建、离线测试或静态解析：

```bash
source /opt/ros/jazzy/setup.bash
cmake --build build_standalone/tare_planner --parallel 2
ROS_DOMAIN_ID=231 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
  HT_CONFIGURATION_FIXTURE="$PWD/docs/fixes/fixtures/mixed_turn_stop.txt" \
  ctest --test-dir build_standalone/tare_planner --output-on-failure --parallel 1
PYTHONPATH="$PWD/tools/ht_cupy_bridge:$PYTHONPATH" \
  ROS_DOMAIN_ID=231 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST \
  python3 -m pytest -q tools/ht_cupy_bridge/test_input_odometry.py \
  tools/ht_cupy_bridge/test_source_contract.py tools/ht_cupy_bridge/test_postfilter_bridge.py \
  tools/ht_cupy_bridge/test_historical_elevation.py tools/ht_cupy_bridge/test_elevation_quality.py \
  tools/ht_cupy_bridge/test_local_surface.py
python3 validation/real_vehicle_offline_fix_2026-10-22/check_launch_contract.py
python3 scripts/check_tare_waypoint_contract.py
```

需先在干净checkout按已有构建说明配置系统依赖；本轮使用现有独立build_standalone，不依赖相邻工作区构建覆盖。
