# CMU Garage 探索能力对比

目的：评估修复后 HT 集成对持续探索、覆盖增长和规划耗时的影响。
基线是**同一份修复后规划器关闭 HT**，不是另行移植的原版 TARE。
不把短时间能移动等同于完整探索成功。

## 固定协议

- 初始对比的规划器源码：`c4b7a41d3ae3466c8b5eb043c8f1f3f81b3c9e8d`。初始实验工具和数据归档提交为 `e1afe89`。
- CMU Jazzy 环境：`8313dfed10533787582be8a6044483fe3299622f`，Garage 场景。
- 每次重新启动仿真，从相同原点出发，速度上限 0.5 m/s。
- `baseline`（HT 关闭）和 `ht`（HT 开启）各 3 次，各记录 300 秒。
- 顺序：baseline 1 → HT 1 → HT 2 → baseline 2 → baseline 3 → HT 3。
- 仿真预启动 10 秒，测量节点预热 5 秒，通过 `/start_exploration` 发出开始信号。
- 导航流、HT 和规划器均使用 CMU 默认的系统时钟；同时记录 `/clock`，监控仿真速度。
- 上游局部规划器使用 `std::random_device`，本实验不改动其随机逻辑；重复不是相同随机种子的配对试验。
- 两组均发布同样的合成 HT 图以保持测量负担一致：80 m × 80 m、0.5 m 分辨率、5 Hz、8 个方向均为 0.9、valid 为 1。基线忽略该输入。
- 不注入故障。实验期间不修改规划器或调参。

这是一组**均匀可通行输入下的集成效率实验**。它不能检验真实地形风险预测、方向区分能力或复杂危险地形中的安全收益。

## 指标及解释

主指标是开始信号之后**新增命中的参考表面体素数**：将 `/registered_scan` 的 XYZ 点和 CMU 官方 Garage 参考 PLY 分别映射到固定世界坐标系的 0.5 m 网格，去重后求交集。负坐标使用向下取整。预热阶段已见体素不计入新增值。

参考 PLY 包含 4,617,947 个点，形成 339,912 个唯一体素。表中的“参考表面命中率”是累计命中数除以此固定分母。参考文件包含多层及可能不可到达的表面，因此该比例**不是可通行空间探索完成率**。

同时报告：

1. 覆盖随时间的曲线及曲线平均值，用于观察覆盖是否较早增长。
2. 平面行驶距离、每米新增参考体素、最后 60 秒新增参考体素。
3. 低速停留：忽略前 5 秒，按 1 秒划分，连续至少 5 个区间内平面累计行程均小于 0.05 m。完成信号之后的区间不计入。它也包括主动转向或等待，不能直接解释为碰撞或死锁次数。
4. `/runtime_breakdown` 的最后一项：规划主流程的毫秒耗时，记录中位数和 P95。该计时覆盖表示更新、全局/局部规划与目标点计算，**不等于整个节点的 CPU 时间**，不含独立 HT 消息回调和后续可视化发布。
5. CMU `/explored_volume`：命中体素数乘以体素体积，只作辅助指标，不称为已探索自由空间体积。
6. `/exploration_finish`、激光频率、消息年龄、记录间隔、仿真时钟速率，用于判断实验是否完整有效。

每组报告 3 次独立运行的均值、样本标准差和范围，图中阴影是观测最小值至最大值，**不是置信区间**。样本少且只有一个场景，不作统计显著性或泛化性能结论。

## 复现

依赖及 CMU 场景安装见仓库根目录 `VALIDATION.md`。先应用其中的 `validation/cmu_jazzy.patch`。CMU 自带统计器另有输出路径问题，应用本目录的补丁并编译：

```bash
git -C ../autonomous_exploration_development_environment apply \
  "$PWD/experiments/cmu_metrics_path.patch"
cd ../autonomous_exploration_development_environment
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select visualization_tools
cd ../HT_Explo-codex-ht8dir-v1
source ../autonomous_exploration_development_environment/install/setup.bash
source install/setup.bash
python3 experiments/coverage_metrics.py
python3 experiments/run_exploration_suite.py --duration 300 \
  --output experiments/results/new_garage_run
python3 experiments/analyze_exploration.py experiments/results/new_garage_run
```

输出目录必须是新的，已有单次实验不覆盖。完整数据包括每 0.2 秒的测量、每次规划耗时、所有激光帧到达时间、去重后的观测体素、CMU 原始统计和轨迹、参数文件、参考体素及协议。`protocol.json` 在运行前保存输入 PLY 和采集脚本的 SHA-256。大量控制台日志仅本地保留，不加入 Git。

`--pilot --duration 20` 只用于检查采集链路，不纳入正式对比。每次完成后检查记录时长、激光频率、规划计时和 CMU 统计是否存在；不以“必须有位移”为有效性条件，以免排除规划失败或长期停滞的真实结果。

## 拐角修复后的复测

初始 6 次实验发现 HT 第 2 次在约 81 秒后持续停滞。原始失败、路径/几何快照及统计均保留在 `results/garage_20260920/`。在这组实验全部结束后，才修改规划器，使 HT 连通搜索和路径图一致地拒绝穿过不可用网格角点的对角连接；保留其他合法斜向连接和方向代价，也保留执行阶段检查。

修复后另跑 3 次 HT，各 300 秒，使用相同输入和指标；基线复用初始实验的 3 次 HT-off 记录。它们不是与复测交替运行的新基线，不能把两个阶段当成同随机种子的配对试验。当前启动脚本记录实际 Git 提交，并要求规划器源码已提交，避免版本不明确。

```bash
python3 experiments/run_exploration_suite.py --ht-only --duration 300 \
  --output experiments/results/new_corner_fix_run
python3 experiments/analyze_exploration.py experiments/results/new_corner_fix_run \
  --baseline-results experiments/results/garage_20260920
python3 -m unittest discover -s experiments -p 'test_*.py' -v
```

分析工具会验证两阶段的时长、速度、参考地图和 HT 输入协议一致，并从保存的体素集合独立重算覆盖计数。

## 本次新增的工程修改

- `cmu_metrics_path.patch`：CMU 统计器原先直接替换路径中的 `/install/`，遇到自定义绝对输出路径会越界异常。现在仅在找到该片段时替换，并检查输出文件能否打开。
- `validation/sim_probe.py`：允许实验设置 HT 图大小和频率，原有验证默认值保持不变。
- `experiments/`：增加启动、采集、体素匹配、统计和绘图工具。
- 初始 6 次实验期间不改变规划算法；之后的拐角修复使用独立复测目录。之前的移动、依赖和接口修复见 `VALIDATION.md`。
