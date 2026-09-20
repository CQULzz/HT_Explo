# TARE + HT 8dir 第一版

2026-09-15 更新：已在 Ubuntu 24.04 / ROS 2 Jazzy / CMU Garage 完成编译与运动、故障注入验证。修复和复现步骤见 [VALIDATION.md](VALIDATION.md)。下面的模型范围限制仍适用。

2026-09-20 更新：重复探索实验发现并修复了路径图允许切角、执行检查却拒绝该段造成的停滞。探索对比及修复复测见 [EXPERIMENT_REPORT.md](EXPERIMENT_REPORT.md)。

这是一个供仿真和离线联调的源码原型，不是已经通过实车验证的导航软件。

## 这一版做了什么

HT 不是直接调整车辆速度，而是改变 TARE 对局部路线的评价：

```
HT 8 个方向概率
  -> 候选点之间的有向边代价
  -> 有向最短路
  -> 局部 TSP 排序及候选路线比较
  -> 沿选中路线输出短 waypoint
```

保留原来的覆盖增益候选点采样、全局规划、几何碰撞检查。没有修改 HT 模型或全局 TSP。
这不是完整的 (x,y,theta) 状态格规划：方向取每条边的运动方向，尚未加入车辆转弯半径、原地转向风险或姿态连续性约束。

## HT 权重到底怎么用

每条边的代价为：

```
J = L + ht_weight * R + ht_unknown_penalty * U
R = sum(ds * [-ln(max(P(x,y,heading), 0.001))])
```

- L 是路径长度，单位米。
- R 是已知区域的方向风险积分；乘以采样间距 ds，避免仅因采样更密就增加惩罚。
- U 是 HT 未知或无效部分的长度，单位米。
- P 根据每段的行驶方向查询最近的一个原始 ht_dir_k，不平均正反方向。
- 这只是相对风险代价，不宣称是整条路径的实际失败概率。

例：A 路长 2 米、P=0.2；B 路长 3 米、P=0.9。
ht_weight=0 时 A 的代价 2、小于 B 的 3；ht_weight=1 时 A 约 5.22、B 约 3.32，选择 B。
未知区域代价独立于 HT 权重。

建议先对比 0、0.5、1、2，不把这些初始值当成已标定参数。
参数在启动时读取，改 YAML 后重启节点，暂不支持运行中热更新。

## 两种运行模式

- ht_enabled=false：使用原版局部规划和 waypoint 逻辑，适合原版对照实验。
- ht_enabled=true：使用新增有向代价和保守 waypoint 逻辑。

ht_weight=0 不等于完全恢复原版，因为未知惩罚、有向路线起终点和 waypoint 限制仍然生效。
要做严格消融，请区分“原版 TARE”“融合逻辑但权重为零”“融合逻辑且权重非零”。

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

## Waypoint 的限制

- 有向局部路线始终从机器人附近的候选点开始，不事后倒序。
- 保留一个全局路线边界候选点作为末端；优先原 start 边界，否则使用 end 边界。
- 局部 TSP 的距离矩阵逐方向计算，求解时间上限 200 ms；不可达或无解则返回空路线。
- HT 连通搜索和路径图共用边支持检查：端点高度差满足连接阈值，斜向连接经过的角点相邻网格均须无碰撞且已在视线内。禁止跨不可用网格切角，保留其他合法斜向边及其有向 HT 代价。
- 只跟随首个非近邻路径节点，目标距离最多 ht_lookahead_distance；不会跨越后续转角。
- 跳过首个 ROBOT 网格锚点；按水平距离判定路径节点到达。默认 ht_waypoint_reached_distance=0.3 米，必须大于控制器的停车距离（CMU 默认 stopDisThre=0.2 米），且小于 ht_lookahead_distance，避免双方对“已到达”的判断不一致而停滞。
- 沿机器人到目标采样，要求在 TARE 局部范围、当前视线内且无几何碰撞。
- 同时要求 ht_validity_radius 范围内有有效 HT 数据，未知路径可参与排序，但不会作为本次实际执行目标。
- 禁用原版初始 12 米前推、waypoint 外推和直接 rush-home 捷径。
- 无新关键帧、地图过期、方向未标定、无候选点或无有效路线时输出当前位置。

注意：有效性圆盘只是数据支持范围检查，不是精确车身碰撞检测。
风险积分目前查询中心线；尚未实现 footprint 最低概率惩罚，也没有启用 p_block 硬阈值。
因此很低的 P 仍可能被选择，不能据此宣称车辆安全。
此保守版本在有效地图边缘可能停住；没有实现自动试探未知地形或脱困策略。

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
5. 在相同场景、相同候选采样条件下比较权重 0 与 1：低概率方向的路线总成本应增大。
6. 交换正反方向概率：验证去程、回程路径不被强制对称。
7. 在地图边缘和狭窄通道验证不外推目标、不跨角。
8. 最后才在具备独立急停、低速限制和人工监护的仿真/实车链路验证。

/ht_navigation_allowed 是规划状态 Bool，不是电机使能信号。
目前由规划周期发布，没有独立高频看门狗；规划卡住时也可能不及时更新。
输出当前位置并不保证底层控制器刹车。控制端必须独立处理消息超时、急停、LiDAR 近障、
侧翻、碰撞与卡住检测。本交付不发布 /cmd_vel。

## 当前验证结果与边界

初版在 Windows 上运行了 37 项独立 C++17 核心检查。当前 Linux 修订版为 52 项核心检查和 9 项 ROS 集成测试，全部通过。
覆盖方向索引、旋转、坐标偏移、无效数据、时间有效性、积分采样一致性、
未知代价、不可达图、正反有向路径和权重改变偏好；新增二维/三维切角拒绝、合法斜向边保留及拐角绕行回归检查。
新增 ROS 测试覆盖 GridMap 循环缓冲区转换、旋转平移 TF、无效概率、过期/未来时间、缺层/缺 TF、NaN 姿态与畸形数组。已完成完整 colcon 构建和 CMU 车库运动测试；没有进行实车测试，也没有真实 HT 模型推理输入。详细结果见 VALIDATION.md。
全对最短路和有效性圆盘检查尚未做大地图性能优化；新增 TSP 未计入上游细分运行时间统计。

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
