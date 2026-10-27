> Jetson Scout当前实车入口、三种模式与方向依据见 [启动说明](docs/real_vehicle/JETSON_STARTUP.md)。下文通用配置/早期记录不覆盖实车入口的模式解析。

# TARE + HT 八方向硬约束

2026-10-17 最新：[停滞修复说明](docs/fixes/2026-10-17_context_recovery.md)。隧道、室内各600秒均完成返航，等长任务区间最长全零指令缩至4.30/4.65秒；室内总观测体积反而下降，地图尾延迟仍存在。视频与原始失败均保留，不宣称探索效率或实车验收通过。

版本导航：[每个阶段的改动、功能、验证及问题](VERSIONS.md)。当前执行细节见[规划与执行衔接](docs/xytheta_execution_continuity.md)。2026-10-16长测确认：节点能连续运行，但仍长期回访，未通过持续有效探索验证，见[60分钟报告](docs/results/ht_endurance_2026-10-16/REPORT.md)。

2026-09-15 更新：已在 Ubuntu 24.04 / ROS 2 Jazzy / CMU Garage 完成编译与运动、故障注入验证。修复和复现步骤见 [VALIDATION.md](VALIDATION.md)。下面的模型范围限制仍适用。

2026-09-20 更新：重复探索实验发现并修复了路径图允许切角、执行检查却拒绝该段造成的停滞。探索对比及修复复测见 [EXPERIMENT_REPORT.md](EXPERIMENT_REPORT.md)。

这是一个供仿真和离线联调的源码原型，不是已经通过实车验证的导航软件。

## 当前局部规划（2026-10-17核对）

TARE 保留全局探索引导和局部覆盖视点采样。对它选出的高收益视点，局部规划器从实时里程计位姿出发，在连续 `(x,y,theta)` 状态上做 Hybrid A*；搜索键使用 0.3 米网格和 16 个朝向桶，轨迹仍是连续的。动作包括差速/滑移转向车可执行的前进、倒车圆弧及原地转向。每个动作经几何检查，并使用共用的 `motionSupport` 检查经过的HT栅格、车头变化与行驶方向。规划、发布前和执行检查统一；执行端另检查前约1米路径与指令弧线。任一采样点不满足硬阈值便删去该动作。搜索代价以行驶时间为主，倒车乘 1.15 惩罚；HT 概率不作软代价。

每个候选目标的单次搜索预算为 0.15 秒、8000 状态；一轮目标搜索共用 0.35 秒预算（不含地图预处理与视点更新）。连续具备新鲜地图但在 0.1 米范围内停滞 12 秒时，可更换目标；近期到达过的视点仅在普通目标没有安全路线时用于有限回退。规划范围为随车滚动的局部 HT 地图；远处的全局目标先选当前地图内的进展视点，随后继续重规划。返航也使用相同 XYθ 搜索。`/ht_xytheta_path` 保留每个轨迹姿态，独立 `xytheta_follower` 以 20 Hz 输出 `/cmd_vel`，限制线/角速度及加速度，并在路径、里程计、地图、扫描过期、明确禁止或 `/stop` 生效时停车。HT启用时不再仅因旧Bool许可年龄超过1.5秒而停车，执行器须独立校验最新HT图。仿真时只应有一个 `/cmd_vel` 控制器。

这里的速度和角速度约束能生成差速车可跟踪的动作，但尚没有轮胎滑移、轮速/轮矩、坡面动力学或整段轨迹的严格动力学可行性证明。实车需另外标定 HT 方向、制动能力和底盘参数。

## HT 硬门槛

每条候选边沿运动方向读取对应的 `ht_dir_k`。当前位置的网络上下文必须有效；整车足迹必须具备观测支撑，且其中每个有效低概率格都执行硬封锁。新增的 `ht_observation_valid` 只描述高程观测支撑，`ht_valid` 描述网络上下文；旧格式缺少观测层时仍采用原有严格检查。其车体覆盖范围内每个有效概率都必须满足 `P >= ht_min_probability`（默认 0.5）。不满足的动作不可选；当前XYθ搜索按预计运动时间、转向及倒车惩罚选择路线，HT概率不作为软代价。旧有向图接口中的长度代价不能代替当前XYθ规划目标。规划、发送前与执行使用统一运动段检查。`ht_min_probability` 是可配置的工程阈值，尚未由实车失败率标定。

```
J = 预计运动时间及运动惩罚  当运动学、几何及HT硬门槛全部通过
J = +∞     当任一已观测采样点低于阈值
```

- 未知区域默认禁止通行；仅任务起点附近 1.2 米、前 30 秒内的有界起步先验允许缺测。
- P 根据边的行驶方向查询最近的一个原始 `ht_dir_k`，不平均正反方向。
- 几何碰撞和局部范围检查仍独立运行；HT 概率不能替代实体碰撞检测。

例：A 路长 2 米、某点 P=0.2；B 路长 3 米、沿途最低 P=0.9。阈值为 0.5 时 A 不可通行，B 可参与按预计运动时间进行的路线比较。

参数在启动时读取，改 YAML 后重启节点，暂不支持运行中热更新。

## 两种运行模式

- ht_enabled=false：使用原版局部规划和 waypoint 逻辑，适合原版对照实验。
- ht_enabled=true：使用 HT 有向硬门槛和保守 waypoint 逻辑。

对照原版时应明确记录阈值和未知区域策略；`ht_enabled=false` 才关闭 HT 路径与执行检查。

## 地图接口与方向标定

默认输入 /ht_traversability/global_local，类型 grid_map_msgs/msg/GridMap。
必须包含 ht_dir_0 到 ht_dir_7 和 ht_valid；ELE 端需要关闭 aggregate_only。
本交付不包含 ELE，不会自动改动其配置。

地图有效条件：ht_valid>=0.5，八个概率均有限且在 [0,1]。
GridMap 循环缓冲区通过 grid_map 官方转换和位置索引展开，不能直接假设消息数组按普通二维图排列。
在消息时间戳查询地图坐标系到 map 的 TF；要求重力对齐，只接受平面旋转。
拒绝非单位 GridMap pose 旋转、缺失层、错误概率、缺失 TF 和过期数据。

ht_channel_order 的第 k 个值表示：几何方向 offset+k*45 度使用哪个原始 ht_dir 层。
方向角相对于 HT 地图坐标系 +X 轴，逆时针增加；offset 单位弧度。
默认 identity 只是占位，不意味着模型的方向已经核对过。

首次接入先做离线标定：用方向性明显的坡面，核对 +X、+Y、-X、-Y 及四个斜向，
再旋转输入地图核对通道随几何方向的对应关系，并用实际行驶记录交叉验证。
确认顺序和偏移后才将 ht_directions_calibrated 改为 true。
默认 false 时节点只输出当前位置，不会给出前进目标。

## 执行与保守边界

- 输入 `/ht_traversability/global_local` 过期、方向未标定、局部目标不可达或路径无效时，TARE 取消 `/ht_navigation_allowed`，`xytheta_follower` 停车。
- 未知区域默认禁止通行；仅起点附近有受时间和距离限制的启动先验。
- TARE 的旧 waypoint 发布保留用于状态与可视化；实际仿真运动由 `/ht_xytheta_path` 和 `xytheta_follower` 执行。不能同时启动旧 `pathFollower`。
- 当前还未实现专门的死胡同脱困或未知区域主动试探策略；无法找到合格动作时停车。

## 编译与启动

在已有 TARE 所需传感器/仿真链路的 Ubuntu ROS2 工作空间中使用本源码。
不要同时放入两个同名 tare_planner 包。保留你自己的旧版本备份。

```bash
source /opt/ros/humble/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select tare_planner --symlink-install
source install/setup.bash
colcon test --packages-select tare_planner
colcon test-result --verbose
ros2 launch tare_planner explore_ht.launch.py scenario:=garage
```

Jazzy 环境改用对应 setup.bash；已验证 Ubuntu 24.04 / Jazzy / x86_64。
已替换为官方 OR-Tools 9.8.3296 Ubuntu 22.04 x86_64 完整依赖集，并在 Jazzy 下验证。来源与校验和见 or-tools/SOURCE.md。
新增依赖 grid_map_core、grid_map_ros、grid_map_msgs、tf2_geometry_msgs。

默认配置 src/tare_planner/config/ht.yaml。
自定义配置可用 ht_config:=/absolute/path/ht.yaml 传入。
仿真回放使用 use_sim_time:=true，并确保 HT、TF、TARE 共用同一时钟。
新 launch 只启动 TARE；不启动 ELE、传感器、RViz 或车辆控制器。

## 联调验收

1. 首先断开车辆运动执行端，仅查看 waypoint 和 /ht_navigation_allowed。
2. 标定开关为 false：应输出当前位置且 allowed=false。
3. 配置正确的方向与 TF，持续发布有效地图：有效路径才允许 allowed=true。
4. 停发 HT 超过 timeout、移除 ht_dir 层、制造 NaN、断开 TF：应撤销前进目标。
5. 设置 `ht_min_probability: 0.5`：任一车体覆盖采样点在行驶方向的 HT 概率低于 0.5，该边不可通行；合格边只按距离计价。
6. 交换正反方向概率：验证去程、回程路径不被强制对称。
7. 在地图边缘和狭窄通道验证不外推目标、不跨角。
8. 最后才在具备独立急停、低速限制和人工监护的仿真/实车链路验证。

/ht_navigation_allowed 是规划状态 Bool，不是电机使能信号。
目前由规划周期发布，没有独立高频看门狗；规划卡住时也可能不及时更新。
输出当前位置并不保证底层控制器刹车。控制端必须独立处理消息超时、急停、LiDAR 近障、
侧翻、碰撞与卡住检测。使用独立 `xytheta_follower` 时发布 `/cmd_vel`；不要同时运行 CMU pathFollower。

## 当前验证结果与边界

初版在 Windows 上运行了 37 项独立 C++17 核心检查。当前 Linux 修订版为 81 项核心检查和 13 项 ROS 集成测试，全部通过。
覆盖方向索引、旋转、坐标偏移、无效数据、时间有效性、积分采样一致性、
不可达图、正反有向路径；新增二维/三维切角拒绝、合法斜向边保留及拐角绕行回归检查。
新增 ROS 测试覆盖 GridMap 循环缓冲区转换、旋转平移 TF、无效概率、过期/未来时间、缺层/缺 TF、NaN 姿态、畸形数组及车体侧边低概率格子的硬封锁。当前 XYθ 版本已在 CMU Garage + CuPy 高程图 + HT 桥接链路中闭环试跑；数据见 `docs/XYTHETA_EXPERIMENT_2026-10-12.md`。尚未做实车测试。
Hybrid A* 按局部滚动窗口和时间/节点预算截断；大地图性能及复杂地形脱困尚待验证。

独立测试可在 Linux 运行：
```bash
c++ -std=c++17 -I src/tare_planner/include src/tare_planner/tests/ht_core_test.cpp -o /tmp/ht_core_test
/tmp/ht_core_test
```

## 源码来源

原上传压缩包在制作时已无法从原路径读取，因此此版基于官方 humble-jazzy 分支，
不是对你原压缩包的逐文件修改。下载日期：2026-09-14。

- [TARE 官方源码](https://github.com/caochao39/tare_planner/tree/humble-jazzy)
- [GridMap ROS2 消息定义](https://github.com/ANYbotics/grid_map/blob/humble/grid_map_msgs/msg/GridMap.msg)
- [GridMap ROS2 转换接口](https://github.com/ANYbotics/grid_map/blob/humble/grid_map_ros/include/grid_map_ros/GridMapRosConverter.hpp)

上游下载 ZIP SHA256:
DD420C93C802D1AD335D5E264238E3F9436A8CA2A5A444CFC961AD6FAD24633D

release_manifest.json 记录修改文件及上游 ZIP 标识，ht_v1.patch 可用于审查本版差异。

## 独立工作区与实车驱动

本工作区的 `src/` 同时包含 `tare_planner`、Fixposition ROS 2 驱动及其 SDK、
RoboSense `rslidar_sdk`、`rslidar_msg`。不需要 source 其他工作区。
在 Ubuntu 24.04 / ROS 2 Jazzy 上从工作区根目录执行：

```bash
bash scripts/build_standalone.sh
source scripts/source_standalone.sh
ros2 launch tare_planner explore_ht_fixposition.launch.py
```

构建脚本只 source `/opt/ros/jazzy`；若系统未安装 `nlohmann-json3-dev`，
会把该开发包下载并解压到本工作区的 `.local_deps/`。驱动源码来自各自官方仓库，
固定版本与许可证见 `THIRD_PARTY.md`。默认 Fixposition 连接地址写在
`src/tare_planner/config/fixposition.yaml`，当前为 `192.168.1.103:21000`；
需要按实车设备地址核对。`rslidar_helios32.yaml` 使用 `RSHELIOS`、
UDP 3344/5566，并在 `rslidar` 坐标系发布 `/rslidar_points`。
启动文件同时运行两套驱动和 TARE，TARE 从 `/fixposition/odometry_enu` 定位，
驱动的 `nav2_mode` 会将其父坐标系设为 `map`。

驱动启动不等于探索闭环完成：还必须把点云正确配准后发布为同一 `map`
坐标系的 `/registered_scan`，提供 `/terrain_map`、`/terrain_map_ext` 与
八方向 HT GridMap，并将 `/way_point` 接到底盘控制器。原始点云不能只改
`frame_id` 当作配准点云。默认 `ht_directions_calibrated: false` 会保持停车，
需完成方向标定后再启用运动。
