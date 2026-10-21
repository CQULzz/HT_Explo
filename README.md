# HT_Explo · Scout Helios32 实车分支

**当前分支：`real/scout-helios32`。** 这里维护实车外参、输入转换和独立启动入口。`main`保留原仿真/实验归档基线，`develop`保留通用开发候选；本分支不会自动回写这两个分支。

实车外参来自用户指定的`CQULzz/eletranskit_scout`固定提交`cf0b73d`。用户于2026-10-22确认：FP_POI与fixposition_link同位、支架0.1162m高度均已实车核验。本次只做代码及离线验证，**没有启动仿真、传感器或车辆，没有实车通过结论**。

[实车接入说明](docs/real_vehicle/SCOUT.md) · [离线结果和剩余问题](validation/real_vehicle_scout_2026-10-22/REPORT.md) · [外参配置](src/ht_scout_bridge/config/scout_extrinsics.yaml)

## 实车数据链

```mermaid
flowchart LR
  FP[Fixposition ENU里程计] --> A[实车输入适配器]
  TF[外部已标定TF] --> A
  L[Helios32点云] --> A
  C[独立CuPy高程图] --> A
  A --> O[map中base_link里程计]
  A --> S[map中registered_scan]
  A --> E[291×291高程及已有观测年龄层]
  E --> H[HT八方向推理]
  O --> T[TARE覆盖与TSP顺序]
  S --> T
  H --> T
  T --> P[XYθ路线]
  P --> F[可选跟踪器]
  F --> V[base_link下TwistStamped]
```

外部工作区继续提供定位、雷达、TF和CuPy。本分支提供`ht_scout_bridge`输入适配器、已有HT推理及TARE/XYθ规划；不会重复启动定位驱动、雷达、TF广播器或原仓库的HT显示节点。

## 实际用到的外参

`T_parent_child`把child中的坐标变换到parent。以下平移单位为米，旋转均为零：

| 变换 | xyz |
|---|---|
| FP_POI → base_footprint | (-0.2005158179045505, 0, -0.65899) |
| base_footprint → base_link | (0, 0, 0.23479) |
| **FP_POI → base_link：规划参考点** | **(-0.2005158179045505, 0, -0.4242)** |
| **FP_POI → rslidar** | **(-0.0280158179045505, 0, 0.126)** |
| base_link → rslidar | (0.1725, 0, 0.5502) |

定位通过矩阵组合变为车辆参考点，速度加入角速度与杆臂的叉乘项，协方差按参考点变化传播。点云按原扫描时间查询TF并应用LiDAR外参，保留强度等字段；采用源配置的车体点过滤。不是单纯改`frame_id`。

## 独立构建和入口

```bash
bash scripts/build_real_scout.sh
source /opt/ros/jazzy/setup.bash
source install_real/setup.bash
ros2 run ht_scout_bridge check_scout_calibration \
  "$PWD/install_real/ht_scout_bridge/share/ht_scout_bridge/config/scout_extrinsics.yaml"
```

实车消费者入口为`ros2 launch ht_scout_bridge scout_real.launch.py`。默认跟踪器不启动，命令出口为`/ht_real/cmd_vel_stamped`；需要核对底盘实际消费接口后配置。HT八方向校准仍独立保留，传感器外参确认不等于方向/概率阈值已经标定。

外部建图使用本分支的[mapper_for_ht.yaml](src/ht_scout_bridge/config/mapper_for_ht.yaml)作为独立参数文件：原生0.04m/格，291×291，发布`elevation/variance/time`。适配器把已有`time`层按原值接入`observation_age`。模型中心裁剪输出241×241，即9.64m见方；不缩放250×250图，不伪造年龄。具体两终端集成方式和输入话题见[SCOUT.md](docs/real_vehicle/SCOUT.md)。

构建使用本工作区的`build_real/install_real`，HT终端只source ROS和本工作区install。两个独立工作区通过ROS话题通信，不互相source构建产物。

完整探索源码仍在[src/tare_planner](src/tare_planner)，HT模型和历史融合在[tools/ht_cupy_bridge](tools/ht_cupy_bridge)，新增实车专用代码在[src/ht_scout_bridge](src/ht_scout_bridge)。原实验资料和标签保留于Git历史及[归档索引](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/catalog/INDEX.md)。
