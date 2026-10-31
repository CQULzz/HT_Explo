# Scout实车接入与配置边界

Jetson ARM64 / ROS Humble 的本机构建与隔离启动方式见
[Jetson 本机启动说明](JETSON_STARTUP.md)。当前三种模式、方向依据和插补行为以该说明为准；以下保留早期原环境与按日期记录。

本说明针对`real/scout-helios32`。传感器外参及配置来源于用户指定仓库固定提交`cf0b73d7d01b4b6a2718c7ff3124f4b7a3368c36`；仅导入任务所需数值和派生建图配置，不复制源私有仓库的无关软件、网络或设备设置。

## 实车与仿真分开

- 当前实车工作目录：`/home/lzz/my test/HT_Explo-scout-real`。构建和安装为`build_real/install_real`。
- 原`HT_Explo-fixposition`工作目录及`main/develop`分支未切换、未覆盖。实车分支从已有离线修正`8b10207`派生。
- 实车入口只解析`ht_scout_bridge`、已有HT推理、TARE规划和可选跟踪器，不包含CMU/Gazebo/world/模拟里程计启动项。`tare_scout.yaml`独立保存TARE采样参数初值，未加载garage/campus参数文件。
- 底层覆盖/TSP函数及模型权重不变。只有跟踪器增加可配置`command_frame`，原默认`vehicle`保留，实车入口显式设置`base_link`。

## 外参如何进入计算

定义`T_A_B`为把B坐标变到A坐标的变换：

```
T_map_base = T_map_ENU0 · T_ENU0_POI · T_POI_base
T_map_lidar(t_scan) = T_map_POI(t_scan) · T_POI_lidar
```

`T_POI_base`与`T_POI_lidar`由[scout_extrinsics.yaml](../../src/ht_scout_bridge/config/scout_extrinsics.yaml)的完整链计算。平移随机器人朝向旋转，不能简单从map的x/z减去常数。输出里程计固定为`header.frame_id=map, child_frame_id=base_link`。

速度按`v_base=R_POI_baseᵀ(v_POI+ω_POI×r_POI_base)`变换，角速度按姿态旋转。Pose协方差使用小角度一阶Jacobian传播；Twist协方差依据`twist_covariance_frame`选择源parent/child轴后传播。默认parent对应源FP_A-ODOMENU协方差约定；原驱动未给出的角速度不确定度不被自动补成测量保证。

速度坐标解释参考[Fixposition ROS Driver](https://docs.fixposition.com/fd/fixposition-ros-driver)，协方差来源参考[Covariance Estimations](https://docs.fixposition.com/fd/covariance-estimations)。这些资料用于明确消息约定，不是本车辆精度测量。

适配器还核对外部TF：POI到base_link/LiDAR与配置差异超过1mm或1mrad时锁定停用；同时间TF与ENU里程计差异超过2cm或0.02rad时也锁定。外部TF仍是唯一广播方，本包不发布第二套map/odom/FP_POI父子关系。缺TF时等待原时间戳，不用最新TF冒充。

点云采用整帧刚性变换，保留原时间戳、强度、ring/逐点时间等额外字段；NaN点和源配置车体过滤范围内的返回被移除。**本包没有实现逐点运动去畸变。** 若外部已有去畸变且仍在rslidar系的点云，用`cloud_topic`选择该话题。

## 两个工作区如何接线

外部定位/雷达/建图工作区保持独立。将本仓库`config/mapper_for_ht.yaml`复制为该工作区的自定义参数文件，然后向它原有`real_car.launch.py`传入`mapping_config:=<该文件绝对路径>`，并设`start_traversability:=false`避免重复运行旧HT显示网络。外部工作区自己的启动方式仍以其README为准；本轮没有执行该启动命令，也没有修改其本地未提交文件。

参数文件保留源实车TF、车体过滤和全局瓦片等设置，单独指定：

- `resolution=0.04`，`map_length=11.64`。源核心`cell_n=round(map_length/resolution)+2`，发布时去掉两格内部边界，因此消息是原生291×291。
- 原始图层为`elevation/variance/time`；`time`是源建图器维护的秒级年龄层。适配器原值转成`observation_age`，不把历史图整体填0。该层由源timer按time_interval累计，不是本包生成的逐格硬件绝对时间；负载下的年龄精度仍需录包评估。
- 读取滚动原始高程图，HT保留自身历史融合。不是把源全局旧后验当成每帧新观测再次刷新。
- 高程值按绝对Z处理；map/odom间存在纯平移时，xy中心和高度值一起变换，GridMap元信息Z保持中性0。旋转的高程网格需要显式重投影，本包拒绝静默改名。

HT终端仅执行：

```bash
source /opt/ros/jazzy/setup.bash
source install_real/setup.bash
ros2 launch ht_scout_bridge scout_real.launch.py
```

这是未来集成入口示例；本轮没有启动它。两终端必须使用一致ROS域、时间基准和相容的RMW。HT终端不source外部工作区的install，外部终端也不source本工作区的install。

| 数据 | 输入/输出话题 | 坐标/语义 |
|---|---|---|
| 输入定位 | `/fixposition/odometry_enu` | FP_ENU0 / FP_POI，外部驱动nav2_mode=false |
| 输入雷达 | `/rslidar_points`或配置的去畸变话题 | rslidar；原扫描时间 |
| 输入高程 | `/elevation_mapping_node/elevation_map_raw` | odom或map；291×291原生格；elevation/variance/time |
| 输出定位 | `/ht_real/odometry` | map / base_link |
| 输出配准点云 | `/ht_real/registered_scan` | map |
| 输出高程 | `/ht_real/elevation_raw` | map；elevation/variance/observation_age |
| HT输出 | `/ht_real/traversability` | 八方向及物理支持层 |
| 输入状态/锁定停止 | `/ht_real/input_status`、`/ht_real/stop` | 等待、拒绝、时间或外参故障 |
| 可选跟踪命令 | `/ht_real/cmd_vel_stamped` | geometry_msgs/TwistStamped，frame=base_link |

参数`odometry_topic/cloud_topic/elevation_topic/source_age_layer/calibration_file/command_topic/use_sim_time/start_follower`可以覆盖。`use_sim_time`默认false；可在今后离线录包回放时显式使用测试时钟，不代表启动仿真。

## 初期停止条件（当前模式见上方启动说明）

- 实车跟踪器默认关闭。实际底盘消费Twist还是TwistStamped、命令话题、急停与控制器所有权尚待核对，不能自动连到未知电机入口。
- HT八方向校准默认false，概率硬门槛仍0.5，没有照搬源显示配置的0.15；外参确认不会自动完成HT方向/地形阈值标定。
- 用户于2026-10-31进一步明确前30s起点通行许可独立于HT观测：实车`ht_startup_radius=1.5`、`ht_startup_duration=30`、`ht_startup_assume_traversable=true`。固定任务锚点和绝对截止时间，期间离圈不提前退役；圈内覆盖HT低分、HT障碍及缺测许可，期满恢复正常检查。原始观测保持，独立碰撞/急停/定位及通信门槛仍生效，详见[CUDA与启动策略](HT_CUDA_STARTUP.md)。
- 2026-10-24统一先验来源：收到任务开始请求且定位/点云有效时，规划器锁定起点与30秒到期时间，通过`/ht_real/ht_startup_prior`发布`StartupPrior`（可靠、保留最新状态）。跟踪器不再自行初始化；晚启动只能获得剩余时间。等待地图/校准、重发路径或重复开始指令均不刷新先验。固定30s模式共享策略位和绝对到期，原未知补充模式仍有离圈退役；收到另一套起点或到期时间会报`HT_STARTUP_PRIOR_CONFLICT`并保持停止，需整套导航重启。
- 定位、TF或时间明显不连续时锁定停用并要求整套建图/导航链重启；没有假装自动清一张图就能恢复所有历史状态。

尚需真实录包核对去畸变、时间同步、输入延迟和缺测，以及车体控制/制动、坡面滑移和模型实际误判。离线坐标计算与接口通过，不是实车运动验收。

## 运行图隔离

实车节点使用`ht_real`命名空间，并重映射原代码里的绝对路线、许可、完成状态、碰撞云、急停和航点话题到`/ht_real/*`。相对发布也在该命名空间内。仿真与实车还应使用不同ROS_DOMAIN_ID；实车设备/建图与HT两终端使用同一个实车域。外部TF仍由实车工作区提供，本包不广播重复TF。

实车的探索开始、手柄、停止控制对应`/ht_real/exploration_start`、`/ht_real/joy`、`/ht_real/stop`。外部控制器接入这些接口前需核对；没有自动连到仿真或电机驱动。

## 2026-10-23 Jetson 离线修正（历史阶段记录）

- Scout 入口默认 `ht_device:=cuda`；只改变实车入口，通用桥接默认 CPU 保留。CUDA 不可用时明确失败，不静默退回 CPU。GPU 初始化在接收地图前完成；输入时间戳保留，不通过刷新时间戳掩盖延迟。
- 使用严格 FP32（关闭 TF32）以通过同一权重的 CPU/GPU 数值对照。Orin 上模型加 softmax/拷回约 0.34 秒，291×291 平地生成输入的完整回调约 0.80–0.84 秒；这不是 10 Hz，也未包含真实输入或 DDS 延迟。地图 1 秒有效期未放宽，真实负载超时仍停车。
- 增加可选 `start_command_bridge:=true`，默认 false；`start_follower` 仍默认 false。适配器把 `/ht_real/cmd_vel_stamped` 的 TwistStamped 转为 `chassis_command_topic`（默认 `/cmd_vel`）的 Twist。它要求唯一命令源与唯一输出控制者、有效规划许可和新鲜里程计；命令超时 0.3 秒、里程计超时 0.5 秒、显式停止、时钟回退、坐标/数值/限速不符均输出零速度。许可有效期 3 秒，前进速度上限与跟踪器统一 0.4 m/s。
- SIGINT/SIGTERM 正常退出时发送零速度。进程崩溃或断电的保障仍须由底盘驱动/硬件独立看门狗提供，本适配器不能替代硬件急停或证明 CAN 控制模式正确。
- `ht_directions_calibrated=false`、`kAutoStart=false`、未知区域严格检查、车体过滤及零启动安全圆均保留；不自动合并外部 TF 或部署建图工作区。
- 碰撞边界回归用运行时配置生成参考半径，修正 ARM64 编译期 hypot 与运行期 libm 相差一 ULP 导致的测试等号差异；实际碰撞半径与判据不变。

当前仅完成离线修正与测试；没有启动设备或进行车辆运动验收。外部建图仍需按 `mapper_for_ht.yaml` 提供 291×291 的 elevation/variance/time，实测 TF、点云 QoS、方向标定与底盘失联停车仍待集成核验。见 `validation/jetson_scout_2026-10-23/recheck/FIX_REPORT.md`。

### 后续静止性能优化

CUDA 的 `ht_channels_last` 默认改为 false（连续 NCHW）；CPU 默认仍 true。严格 FP32/时间戳/地图1秒有效期保持，未启用 TF32。接收与推理使用两个执行线程，最多保留一份最新待处理地图；里程计加锁，计算期间新检测的定位/时钟故障阻止发布。地图历史只由处理回调修改，退出先等待回调完成。未订阅的历史显示图不做序列化。

同一份实车输入回调均值 0.728→0.380 秒，几何/支撑/障碍层一致，全部0.5通行判据一致。静止短测约2.46Hz、地图年龄中位数0.70秒；尚非10Hz，尚未做运动验证。详细对照与局限见 `validation/jetson_scout_2026-10-23/optimization/REPORT.md`。

### 高程质量过滤编译优化

`ht_quality_backend` 可选 auto/numpy/numba，默认 auto；Numba 不可用时用原 NumPy 实现，显式 numba 不可用则报错。只编译邻域掩码判断（串行、无 fastmath），只在已满足原平滑条件的格子执行原 NumPy 平滑计算，保留源质量判断和历史图过滤两次处理。启动时预热，不刷新输入时间戳。

本机同一实车输入的全部输出图层精确一致，157项测试通过；两次过滤合计约140→20毫秒，完整回调369→238毫秒。静止短测约3.60Hz、地图年龄中位数0.54秒；仍未达到10Hz，中心 HT 上下文有效性仍未通过。速度输出保持关闭。完整证据见 `validation/jetson_scout_2026-10-23/quality_optimization/REPORT.md`。


2026-10-31实车小孔填补默认moderate：最近邻18cm、总8点、四象限各1点、RMS10mm；其余保护与原测量/支撑保持。可设ht_small_hole_profile=strict回到旧强度，见[参数与边界](SMALL_HOLE_PROFILES.md)。新增插值会影响模型概率，不保证所有0.5判定不变。


2026-11-01离线候选：原始/注册点云采用可靠订阅，新增输入计数与QoS诊断；TARE射线/覆盖使用扫描时刻的雷达原点，车辆参考点和已核验外参保持。可选16MiB DDS配置默认不启用，外部进程须独立配置。仍有一次连续9帧缺口，提前完成及ARM未验收，见[接口、参数与诊断](TARE_INPUT_AND_ORIGIN.md)及[实验报告](../results/real_tare_input_fix_2026-11-01/REPORT.md)。
