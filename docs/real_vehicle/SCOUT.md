# Scout实车接入与配置边界

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

## 已保留的停止条件

- 实车跟踪器默认关闭。实际底盘消费Twist还是TwistStamped、命令话题、急停与控制器所有权尚待核对，不能自动连到未知电机入口。
- HT八方向校准默认false，概率硬门槛仍0.5，没有照搬源显示配置的0.15；外参确认不会自动完成HT方向/地形阈值标定。
- 实车不继承仿真的1.2m假定可行启动圆，`ht_startup_radius=0`。未知支撑不足时保持不可执行，不能把缺测地面补成已观测自由。
- 定位、TF或时间明显不连续时锁定停用并要求整套建图/导航链重启；没有假装自动清一张图就能恢复所有历史状态。

尚需真实录包核对去畸变、时间同步、输入延迟和缺测，以及车体控制/制动、坡面滑移和模型实际误判。离线坐标计算与接口通过，不是实车运动验收。

## 运行图隔离

实车节点使用`ht_real`命名空间，并重映射原代码里的绝对路线、许可、完成状态、碰撞云、急停和航点话题到`/ht_real/*`。相对发布也在该命名空间内。仿真与实车还应使用不同ROS_DOMAIN_ID；实车设备/建图与HT两终端使用同一个实车域。外部TF仍由实车工作区提供，本包不广播重复TF。

实车的探索开始、手柄、停止控制对应`/ht_real/exploration_start`、`/ht_real/joy`、`/ht_real/stop`。外部控制器接入这些接口前需核对；没有自动连到仿真或电机驱动。
