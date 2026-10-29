# Jetson 实车入口（更新于2026-10-27）

仓库：`/mnt/nvme0n1/autoware/HT_Explo`，分支`real/scout-helios32`。
适用Ubuntu22.04/ARM64/ROS Humble。下面是当前入口；早期验证结果按日期保留，不代表本版本实车验收。

## 构建与终端

```bash
cd /mnt/nvme0n1/autoware/HT_Explo
HT_ROS_DISTRO=humble bash scripts/build_real_scout.sh
source scripts/source_real_scout.sh
export ROS_DOMAIN_ID=74 ROS_LOCALHOST_ONLY=1 RMW_IMPLEMENTATION=rmw_fastrtps_cpp
unset CYCLONEDDS_URI
```

74是此前实车检查使用的域，需与外部传感器、建图、底盘的实际域一致。离线检查使用独立域，不把测试流量送入实车域。HT终端不source外部工作区install。构建仅处理两个包，独立使用build_real/install_real/log_real；OR-Tools9.8需匹配ARM64，路径`.local_deps/ortools-arm64`或`TARE_ORTOOLS_ROOT`，不包含在源码包中。

## 三种启动模式

| run_mode | 跟踪器 | 速度适配器 | 输出 |
|---|---|---|---|
| inspect（默认） | 关闭 | 关闭 | 地图、规划诊断；无速度发布者 |
| preview | 开启 | 关闭 | 仅`/ht_real/preview/cmd_vel_stamped`，不接底盘 |
| drive | 开启 | 开启 | `/ht_real/cmd_vel_stamped`转`/cmd_vel`的Twist |

仅查看：

```bash
ros2 launch ht_scout_bridge scout_real.launch.py run_mode:=inspect start_rviz:=true
```

预览：

```bash
ros2 launch ht_scout_bridge scout_real.launch.py run_mode:=preview start_rviz:=true
```

实车运行入口（会启用速度输出，外部定位/点云/建图与底盘驱动须已正确运行）：

```bash
ros2 launch ht_scout_bridge scout_real.launch.py run_mode:=drive direction_acceptance:=mapping start_rviz:=true
```

上述入口本身不启动外部硬件驱动，也不自动开始探索。旧`start_follower/start_command_bridge`参数改为默认auto；显式值若与所选模式矛盾会直接报错。preview的话题限制在`/ht_real/preview/`，避免把预览接到正式控制话题。

收到有效输入后，手动开始：

```bash
ros2 topic pub --once /ht_real/exploration_start std_msgs/msg/Bool '{data: true}'
```

停止：

```bash
ros2 topic pub --once /ht_real/stop std_msgs/msg/Int8 '{data: 1}'
```

起点许可固定1.2m/30s，由规划器发布、跟踪器共享；重复开始/重发路径不续期。任务重开需要重启导航，不能用重复开始指令重置先验。

## 方向依据

`config/direction_validation.yaml`分别记录代码映射核对和实车地形响应验证。入口核验实际安装权重SHA256、通道顺序与航向偏移，不能仅修改一个布尔值冒充证据。

- 默认`direction_acceptance:=mapping`采用此前核对的八方向映射；状态显示mapping_verified=true、terrain_response_validated=false。兼容参数`ht_directions_calibrated`由入口据此计算，不表示完成实车坡面验证。
- `direction_acceptance:=validated`要求文件中已有真实地形响应验证记录；目前该状态为false，drive模式会拒绝启动。inspect/preview仍可查看拒绝原因。
- 权重或方向配置不匹配时不接受旧映射依据。模型参考点、地形响应和完整训练溯源的物理不确定性没有因代码开关而消失。

## 看停车原因和地图

```bash
ros2 topic echo /ht_real/runtime_status --once
```

状态包含运行模式、输入/地图年龄、规划器/跟踪器/速度适配器的停车原因、起点许可剩余时间、车旁缺测与插补数量。`COMMAND_SENT_NOT_WHEEL_CONFIRMED`只表示软件命令已发送且存在订阅者，不表示底盘接受了命令或车轮实际转动。

RViz中：灰点是实测高程，外围红绿是HT最佳概率；白圈是0.6m车身诊断，青框是9.64m HT输出范围；绿色起点圈是仍有效的1.2m先验，灰色表示退役。红/黄车身格仍反映缺测/上下文无效，不会被先验涂成实测绿色。可打开插补来源图层查看`ht_interpolated`，不要将其当作新的实测地面。

## 小孔与窄扫描间隙

实车默认`small_hole_repair:=true`，可设false作同输入对照。仅从原有新鲜、通过质量判断的测量拟合，不把插补持久写入历史。要求四象限各至少2个邻点、总计至少12个、最近测量不远于0.12m、局部窗口半径0.16m（4cm分辨率下9×9）、坡度≤0.35、平面RMS≤6mm。观察到的跳变、质量拒绝和障碍附近不插补；不外推地图边缘或填平大片盲区。

输出保留原12层，并增加`ht_measured_valid`（质量认可的历史测量格，不一定是当前帧新观测）和`ht_interpolated`。`ht_observation_valid`仍为原物理支持接口（包含既有近邻支持语义），不是逐格直接实测声明。有限测量不改写，物理支持/HT上下文/障碍掩码均不扩张；模型输入仅在获准插补位置改变高度，不能从插补点二次传播支持；模型输入改变可能影响预测概率，不能宣称所有0.5阈值决策不变，也不能保证未观测到的小坑必然安全。

## 外部输入约定

- 原生291×291、0.04m高程，层elevation/variance/observation_age，使用mapper_for_ht.yaml。`observation_age`必须由实际被接受点云的源时间更新；定时器累计的`time`不能代替。外部mapper须已应用真实观测年龄补丁（见tools/elevation_mapping_fixes/OBSERVATION_AGE.md）；旧版只发time的入口会明确拒绝。
- 默认输入`/fixposition/odometry_enu`、`/rslidar_points`、`/elevation_mapping_node/elevation_map_raw`。
- 外部TF为唯一来源。标定来自eletranskit_scout@cf0b73d：FP_POI到base_link平移[-0.2005158179045505,0,-0.4242]m，base_link到rslidar为[0.1725,0,0.5502]m，旋转为0。
- 车身过滤按指定模型的车体、四轮和传感器几何执行，参考坐标为base_link、余量2cm；外参不变。余量是工程假设，尚未单独实车验收。本包没有逐点运动去畸变。
- 新的`/ht_real/lidar_filtered`保持rslidar坐标系和原时间戳，供独立mapper使用；`/ht_real/registered_scan`为同一过滤结果变换到map后给TARE使用。mapper_for_ht.yaml已切换前者并关闭旧大包围盒，避免重复删地面。禁止把map坐标点改名为rslidar。

测试结果与限制见`validation/navigation_completion_2026-10-27/REPORT.md`，起点共享修正见`validation/startup_prior_sync_2026-10-24/REPORT.md`。软件回归和保存数据对照不等于实车导航验收。

## 2026-10-28 离线审查候选

导出的副本可能缺少OR-Tools的`libortools.so.9`别名。构建现在从实际原生库生成工作区私有运行副本，并随安装打包；不修改外部依赖目录。雷达订阅改为BEST_EFFORT请求，可接入BEST_EFFORT及RELIABLE发布者。命令适配器的看门狗改用稳定时钟定时器，ROS时钟暂停后仍检查接收超时并发布零速。

本候选只在x86_64/ROS Jazzy做了独立构建和离线回归，未验证Jetson/ARM64、CUDA/Numba或车辆运动。原有方向策略、模型、起点先验、1秒地图时效和地形阈值保留。静态保存帧中车旁缺测仍存在；不能将本次修复称为已完成实车自主探索。原因、测试与剩余项见`validation/real_review_2026-10-28/REPORT.md`。

第二轮同时提供CPU推理Conv/BN融合（`ht_cpu_fuse_bn`，默认true，仅CPU生效；false可作对照）。它只折叠eval统计，不修改检查点或地形规则；FP32舍入可能相差数个微小单位。CUDA路径不启用该优化。第二轮问题简报和同输入实验见`docs/results/real_round2_2026-10-28/`。

## 2026-10-30 HT频率优化候选

本地新候选将同一eval Conv/BN融合扩展到CUDA，`ht_fuse_bn`默认true；false可关闭，CPU还受旧`ht_cpu_fuse_bn`开关约束。仍使用FP32、关闭TF32，CUDA布局保持连续。此段取代上面历史记录中“CUDA路径不启用”的当前行为描述。

`ht_history_backend`默认auto，Numba可用时编译多表面选择并在订阅前预热；不可用时告警并回退原NumPy路径。显式设为numba则要求编译成功，numpy可用于同输入对照。Jetson需在实际HT Python环境中提供可用Numba，缓存应在目标机重新编译，不复制本机x86缓存或二进制。

新只读诊断：`ros2 topic echo /ht_real/ht_performance --once`。`source_interval_s`是相邻已处理源时间戳间隔，`publish_interval_s`是实际发布墙钟间隔，`callback_service_s`是本次处理耗时，另有消息年龄、分阶段耗时和`pending_maps_replaced`。源间隔可能包含输入被替换，不能单凭它当作上游原始发布频率；需同时测原始高程和HT输入话题。禁止用重复旧图或放宽地图时效来制造高频。

本地117帧各3次对照中位数60.8→45.1ms，但合并P95未改善；尚未部署Jetson或保证实车不再2.2Hz。证据及完整限制见[HT频率优化报告](../results/real_ht_frequency_2026-10-30/REPORT.md)。

## 2026-10-30 输入桥接与发布减负候选

输入桥接改为三线程executor，点云接收与重计算分组独立，精确源时刻TF和单调性保持；发布前再次检查故障、关闭、时钟及年龄，两个坐标系的点云一起通过检查。点云只解析和过滤一次，保留原中间float32舍入；高程不再复制被丢弃的整条消息。独立输入进程默认`input_blas_threads=1`（可设1～8），部署环境需有`python3-threadpoolctl`，不要把本机28线程条件当作Jetson实际配置。

独立CuPy发布补丁由`tools/install_elevation_fixes.py --workspace /path/to/independent_cupy_ws --publication-performance`安装，只改已知ROS wrapper，不切换融合/配准或trial参数；按原独立build/install路径重建。无订阅时跳过地图锁/GPU取图；有订阅时仍发完整图。需要无订阅录制/捕获的发布器可设`publish_without_subscribers: true`，离线预加载默认保持无条件发布。不使用重复旧图、降低阈值或放宽时效制造高频。

641帧有效录包点云与117帧高程的新旧转换全部字段及载荷字节一致；235项回归通过。本机点云转换中位数20.83→10.72ms，P95 25.62→11.72ms，均不含DDS与在线排队，尚未在Jetson部署或保证车上频率。[输入桥接报告](../results/real_input_pipeline_2026-10-30/REPORT.md)保留完整慢帧、失败尝试及版本哈希。
