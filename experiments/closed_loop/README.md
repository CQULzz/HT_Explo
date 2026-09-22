# 真实 HT 与 TARE 的山地闭环试验

此处实际运行 CMU Gazebo、局部规划器和 TARE；HT 输入来自在线 registered_scan，调用提供的 `original_scout` 八方向学生权重。没有把模型离线准确率冒充探索提升，也没有把地形真值喂给 HT。脚本不使用模型 API，不进行训练。

## 一键复现

在仓库根目录运行（输出目录必须不存在）：

```bash
experiments/closed_loop/run.sh --duration 60 --pairs 2 --output experiments/results/mountain_repeat
python3 experiments/closed_loop/analyze.py experiments/results/mountain_repeat
```

需要现有 CMU Jazzy 和 TARE 构建、Python torch/numpy/scipy/opencv/matplotlib，以及当前机器 `/home/lzz/下载/data_scout`、`original_scout` 和相邻 `eletranskit_scout` 模型源码。CPU 推理，无需 CUDA。默认独立 ROS_DOMAIN_ID=86；同一时刻只运行一个套件。

默认使用原始雷达；显式运行命令：

```bash
HT_DOWNWARD_LIDAR=0 experiments/closed_loop/run.sh --duration 30 --pairs 1 --output experiments/results/mountain_stock_sensor
```

脚本生成独立 OBJ 山地及 SDF，不修改 CMU 仓库、生产雷达配置、网络权重或 TARE 源码。`prepare.py` 固定使用 n47 山地、2 m 高度比例；启动点按固定角落区域的低坡度选取，未根据模型结果选择。

## 条件与公平性

- 两组同一地形、起点、正常车速 0.5 m/s、模型推理负载和 15 秒预热。HT 局部缺测时以 0.2 m/s、0.5 m 短航点降级；这是集成策略的一部分。
- HT 权重固定 1；地图新鲜度 3 秒；保留低概率软代价，局部未知区域按可配置策略处理，没有为结果临时加硬阈值。
- 八方向顺序按训练坐标核对：yaw=0 的 patch 行指向 -X，列指向 -Y，通道 k 对应世界方向 k×45°。`test_bridge.py` 检查坐标旋转、FCN/单 patch 对应与列主序存储。
- 高程只累积激光观测：0.1 m 栅格最低高度，推理分辨率 21/513 m，51×51 感受野，最近观测距离不超过 0.25 m 才计已知，窗口至少 90% 已知才输出有效概率。
- 默认 CMU 雷达垂直范围 ±15°，0.75 m 安装高度形成约 2.8 m 近地面盲区，起点高程无法支持 HT。第二个实验条件将两组雷达同样扩展到 −75°～15°、64 垂直采样，并屏蔽机器人视觉几何的雷达回波。这属于理想化传感器适配，不等于默认 CMU/实车直接部署有效。原始 horizontal/vertical resolution 字段保持 0.2/2.0，64 指 SDF samples，不声称硬件 64 线雷达。
- `kUseTerrainHeight=true` 对两组相同，适配非平坦地形。局部规划器启动目标设为实际起点，避免预热期间向原点移动。

## 已保留的联调过程

- `mountain_live_pilot1`：Gazebo 不接受空格路径被 URL 编码的 OBJ URI，未形成有效实验。
- `mountain_live_pilot2`：初版未加围墙且启动目标仍为原点；发生提前移动和规划器退出，不纳入最终比较。
- `mountain_live_pilot3`：原始雷达、30 秒有效配对。TARE 可移动；HT 因近地面未知区域原地停车。
- `mountain_live_pilot4`：25 秒 HT 诊断复测，中心及 0.6 m 范围有效率为 0，确认高程盲区。
- `mountain_live_pilot5`：增加向下视场但未排除车体自回波，两组都被局部避障阻挡；HT 门控本身已经允许前进。
- `mountain_live_20260921`：固定最终感知配置，baseline→HT→HT→baseline，各 60 秒，不因结果不利更换地形/起点/权重。

原始日志保留本地；主要协议、时序数据和诊断快照归档。比较不能混合不同雷达配置或不同预热条件。

## 指标边界

参考体素仅统计真实山地表面，与是否被 HT 判为可通行无关。地形坡度 >15° 只作为几何暴露指标，未校准为 Scout 的危险阈值；CMU 通过设定位姿控制简化机器人，不能测真实轮胎接触、打滑、翻车或碰撞成功率。停住不会被解释为“零危险所以更好”。

当前集成的 HT 开关同时影响图代价、路径和航点执行逻辑；试验比较整体集成效果，不是单独学习网络的因果消融。地形属于模型训练域，TARE 内部随机源未固定，两次重复只适合初步判断，不用于显著性/泛化声明。

## 修复前发现的返航问题（历史记录）

`src/tare_planner/src/sensor_coverage_planner/sensor_coverage_planner_ground.cpp:988`
在 HT 开启时直接 `return local_path`，位于 `exploration_finished_ && near_home_ && kRushHome` 的返航拼接之前。两次正式 HT 试验均出现 `finished=true`、局部路径仅一个点、停止位置仍距起点约 2 m 的现象。这是集成逻辑问题的具体证据；本轮保持被测算法版本不变并记录问题，不能把少走返航段称作效率收益。

车辆仍是 CMU 简化平台，其几何尺寸和动力学并未变成标签采集时的 Scout。因而即使分类输出接通，也不能把坡度暴露或覆盖变化直接解释为真实 Scout 通过成功率。

## 整改版复现与消融

`run.sh` 现在默认原始雷达（`HT_DOWNWARD_LIDAR=0`）。起点 1.2 m 先验只对缺测有效，最长 30 秒，离开后永久失效；缺测几何降级累计不超过 60 秒或 10 m。调参会记录在协议中。

```bash
# 包含构建、测试、两组各两次闭环和自动出图；无需模型 API。
bash experiments/closed_loop/verify_remediation.sh experiments/results/my_remediation
# 相同 HT 图与执行分支，移除学习风险权重：
experiments/closed_loop/run.sh --condition ht --weight 0 --pairs 2 --duration 90 --output experiments/results/no_risk
# 原严格缺测门控，无启动先验：
experiments/closed_loop/run.sh --condition ht --policy strict --startup-radius 0 --pairs 1 --duration 30 --output experiments/results/strict
```

`metrics.json` 新增 `mission_completed`、完成时刻、状态事件和每个采样的执行模式。`finished` 保留旧探索阶段语义。详见 `docs/HT_TARE_REMEDIATION_IMPLEMENTED.md`。

整改版本 `b847710` 的实测归档：`experiments/results/remediation_stock_20260922/VALIDATION.md`。
自动检查脚本 `check_regression.py` 可单独读取既有结果，避免重复跑仿真：

```bash
python3 experiments/closed_loop/check_regression.py experiments/results/remediation_stock_20260922 --require-completion
python3 experiments/closed_loop/check_regression.py experiments/results/remediation_map_outage_20260922 --require-outage
```
