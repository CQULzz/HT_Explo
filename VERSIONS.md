# HT_Explo 版本说明

更新时间：2026-10-16。维护分支：`codex/ht8dir-v1`。本页按功能阶段整理，并逐条标注全部历史提交；阶段标签是实验里程碑，不代表稳定版。

## 当前版本先看这里

**当前已加入全局停滞检测、失败引导冷却、重复访问记忆与恢复评分修正。最新25分钟探索推进改善，但修复后的60分钟稳定性和返航闭环尚未通过验证，偶发地图过期仍存在。**

同一Garage前20分钟，估计累计观测从原长测同期3293.875m³增至6498m³，第10–20分钟增益从26.375m³增至1654.125m³。最新25分钟结束仍为EXPLORING，不能称全域完成。

- 当前核心规划代码：[`c85ad1f`](https://github.com/CQULzz/HT_Explo/commit/c85ad1f004bbaceae14cd65351be38c3a9e61273)；引导修复：[`7f1c253`](https://github.com/CQULzz/HT_Explo/commit/7f1c253feccb1b7ec4b4912f70312d7b308e3a20)。
- [最新修改与两轮复测报告](docs/results/ht_progress_fix_2026-10-16/REPORT.md) · [最新视频](docs/results/ht_progress_fix_2026-10-16/return_fix_trial/camera_h264.mp4)。
- [此前60分钟失败长测](docs/results/ht_endurance_2026-10-16/REPORT.md) · [此前原版TARE配对比较（旧HT）](docs/results/tare_ht_pair_2026-10-16/REPORT.md) · [GitHub Releases](https://github.com/CQULzz/HT_Explo/releases)。

历史阶段标签与中文Release说明于2026-10-16补录，固定到原始提交；不会改写旧提交日期或移动原有实验标签。

## 功能阶段速查

| 阶段 | 归档提交 | 做了什么 / 已实现 | 已知问题与结论 |
|---|---|---|---|
| [01 八方向HT软代价初版](#stage-01) | [`46f9642`](https://github.com/CQULzz/HT_Explo/tree/46f9642221ff7e251e601818a45fe041831b928c) | 按边的移动方向计算长度、风险和未知长度代价，输出经检查的短航点。 | 低概率仍可能被选中；没有真实XYθ状态搜索、车体朝向连续性或真实HT闭环部署证明。 |
| [02 Jazzy编译与起点停滞修复](#stage-02) | [`c4b7a41`](https://github.com/CQULzz/HT_Explo/tree/c4b7a41d3ae3466c8b5eb043c8f1f3f81b3c9e8d) | 可在CMU Garage闭环移动，异常地图输入能停车并恢复。 | 使用合成八方向地图，未运行真实HT网络；仍是软代价与旧控制链路，未完成全域探索。 |
| [03 旧有向图拐角修复与重复实验](#stage-03) | [`a6c015a`](https://github.com/CQULzz/HT_Explo/tree/a6c015a3a3f703d0b0acb880ed0230e08d49f9bd) | 修复旧图允许而执行端拒绝的特定对角边，具备重复运行、统计及绘图工具。 | HT为80×80米、0.5米栅格、八方向全0.9的合成输入；不是学习模型收益，9轮均未完成全域探索。 |
| [04 真实HT推理与通过性评测工具](#stage-04) | [`4315dd9`](https://github.com/CQULzz/HT_Explo/tree/4315dd9deaed24245d6fbdd3c8ebe8726f74b476) | 将真实八方向预测接入雷达观测高程，区分模型误放/误拒、路线选择和实际车辆通过。 | 传感器适配且地形来自训练域；旧软代价、近地盲区和返航问题仍在，不能以离线准确率代替闭环效果。 |
| [05 起点先验、降级预算与返航状态](#stage-05) | [`29f80bc`](https://github.com/CQULzz/HT_Explo/tree/29f80bc76789a7075f4dfb987cb2e51bfbb56add) | 区分探索结束与真正返航完成；地图故障时停车，恢复后继续；提供可复用回归验证。 | 小样本且HT运行有约52秒几何降级，不能称为纯HT或全域完成；仍是软风险代价与CMU控制器，非当前XYθ。 |
| [06 Fixposition与Helios32驱动接入](#stage-06) | [`d63b9b8`](https://github.com/CQULzz/HT_Explo/tree/d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30) | 提供定位/里程计与Helios32点云输入入口，工作区构建不依赖相邻驱动工作区。 | 硬件IP、雷达型号、TF/外参、时间同步、方向标定和底盘控制仍需实车确认；有驱动不等于已能安全实车探索。 |
| [07 Campus地图传输与前瞻航点](#stage-07) | [`087c42d`](https://github.com/CQULzz/HT_Explo/tree/087c42d45801a34a355cac936488efe19141768d) | 改善大地图送达和CMU路径末端频繁减速，旧控制器继续实际控车。 | 长测倒车占48.4%，另一短测79.3%；旧长测缺XY轨迹/探索体积。此时没有实际XYθ闭环，不能用里程代表探索效果。 |
| [08 实际XYθ硬约束规划与分层历史高程](#stage-08) | [`8398f53`](https://github.com/CQULzz/HT_Explo/tree/8398f538450a21c4ee9d65d17193ee084eacee03) | 从odom位姿到目标视点规划前进/倒车/原地旋转路径；P≥0.5硬门槛、默认严格未知；全局历史高程裁局部窗口供HT推理。 | 运动连续性差、旧许可1.5秒超时导致大量停车，目标反复切换；仍有噪声/未知区，未完成探索或实车验证。10月12日只是本地实验日期，不是独立Git发布。 |
| [09 目标保持与执行器独立校验](#stage-09) | [`dbce623`](https://github.com/CQULzz/HT_Explo/tree/dbce623161087fcaac865b1d4db5305d1cfe2c9c) | 减少目标尚未完成时反向切换；HT启用时旧Bool许可年龄不再单独触发停车，地图/扫描/定位/路径时效和显式禁止仍有效。 | 同代码后续复跑29.76米、102秒后长期停车，故不能把这次56.54米视为稳定通过。仍有规划/执行采样不一致。 |
| [10 同版本复跑失败与完整数据发布](#stage-10) | [`0b842e4`](https://github.com/CQULzz/HT_Explo/tree/0b842e4ab71a1ed0249cc32da923a0f51940106a) | 可以复现并查看约102秒后的失败全过程，保留原Release附件链接。 | 这是失败证据归档，不是算法修复；控车仍为dbce623。上层HT_ASSISTED不代表执行端允许运动。 |
| [11 统一运动段检查与执行拒绝反馈](#stage-11) | [`919d826`](https://github.com/CQULzz/HT_Explo/tree/919d826f340c11e34421a738e80d2a2e85066eb9) | 消除已复现的规划通过/执行拒绝循环；检查车头变化、倒车方向和前约1米路径；不放宽HT门槛或未知策略。 | 只解决特定持续拒绝循环；仍有转向、回访与短暂停顿，短测不保证全局探索完成；最新长测进一步证实长期推进不足。 |
| [12 最新原版TARE配对评测](#stage-12) | [`07ab006`](https://github.com/CQULzz/HT_Explo/tree/07ab0067dc7f47dc6eb7e5e2b9924f79f2ed9a24) | 明确量化原版与当前完整系统差距；与上阶段相比没有再升级运动规划算法。 | 每组一次且倒车/角速度/加速度未完全对齐，是端到端比较；HT转向、停车和回访更多，未追平原版。 |
| [13 60分钟长测：运行连续但探索停滞](#stage-13) | [`6bd5407`](https://github.com/CQULzz/HT_Explo/tree/6bd5407b781771b0460ed1533eaee6d500c91bc4) | 可检验长期资源增长、输入延迟、运动拒绝反馈与探索增益；被测规划算法与上阶段相同。 | 未通过持续有效探索验证；全局引导长期不变、重复回访，网卡掉线时发生约13秒输入中断；内存未失控但持续扩图上界未验证。 |
| [14 全局停滞恢复与返航容差修正](#stage-14) | [`9393e7d`](https://github.com/CQULzz/HT_Explo/tree/9393e7da7d1eeabf04a4325593834304f236e405) | 局部目标完成不再掩盖全局停滞；零收益主目标不能压住所有恢复候选；保留HT硬门槛、严格未知和速度上限。 | 第一轮返航BLOCKED；已补容差回归，但最新一轮未触发返航，不能称闭环通过。尚未重跑60分钟；地图年龄最高4.17秒，仍有过期停车。没有真值全域覆盖率或实车验收。 |

## 各阶段的修改、功能与问题

下列“已知问题”包含该版本后来复跑暴露的问题；实验日期和Git提交日期不同的地方已注明。10月12日本地修改主要在10月15日的322ec85统一入库，未虚构不存在的独立发布。

<a id="stage-01"></a>

### 01｜八方向HT软代价初版

标签：[`ht-stage-20260914-ht8dir`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20260914-ht8dir)；归档提交：[`46f9642`](https://github.com/CQULzz/HT_Explo/commit/46f9642221ff7e251e601818a45fe041831b928c)；类型：功能。

- **改动：** 将HT八方向概率接入有向边代价、最短路与局部TSP；保留TARE覆盖采样和全局引导。
- **实现功能：** 按边的移动方向计算长度、风险和未知长度代价，输出经检查的短航点。
- **验证结果：** 初始归档以本地核心检查为主；后续Jazzy构建发现包识别、OR-Tools和起点停滞问题。
- **存在问题：** 低概率仍可能被选中；没有真实XYθ状态搜索、车体朝向连续性或真实HT闭环部署证明。
- **证据：** [release_manifest.json](release_manifest.json) · [VALIDATION.md](VALIDATION.md)

<a id="stage-02"></a>

### 02｜Jazzy编译与起点停滞修复

标签：[`ht-stage-20260915-jazzy`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20260915-jazzy)；归档提交：[`c4b7a41`](https://github.com/CQULzz/HT_Explo/commit/c4b7a41d3ae3466c8b5eb043c8f1f3f81b3c9e8d)；类型：功能。

- **改动：** 修复包识别、Eigen/GridMap与OR-Tools依赖；跳过过近的起始锚点，补输入校验及故障注入工具。
- **实现功能：** 可在CMU Garage闭环移动，异常地图输入能停车并恢复。
- **验证结果：** 约135秒故障注入试跑行驶40.56米；41项核心、9项ROS检查通过。
- **存在问题：** 使用合成八方向地图，未运行真实HT网络；仍是软代价与旧控制链路，未完成全域探索。
- **证据：** [VALIDATION.md](VALIDATION.md)

<a id="stage-03"></a>

### 03｜旧有向图拐角修复与重复实验

标签：[`ht-stage-20260920-corner`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20260920-corner)；归档提交：[`a6c015a`](https://github.com/CQULzz/HT_Explo/commit/a6c015a3a3f703d0b0acb880ed0230e08d49f9bd)；类型：功能。

- **改动：** 增加gridEdgeSupported和共用连通检查，拒绝切角；保留修复前失败轮并归档复测。
- **实现功能：** 修复旧图允许而执行端拒绝的特定对角边，具备重复运行、统计及绘图工具。
- **验证结果：** 修复后3轮各300秒未见原219秒持续停滞；52项核心、9项ROS、3项统计检查通过。
- **存在问题：** HT为80×80米、0.5米栅格、八方向全0.9的合成输入；不是学习模型收益，9轮均未完成全域探索。
- **控制/功能来源：** `df8815c`；归档提交不表示修改了运动规划算法。
- **证据：** [EXPERIMENT_REPORT.md](EXPERIMENT_REPORT.md) · [README.md](experiments/results/garage_corner_fix_20260920/README.md)

<a id="stage-04"></a>

### 04｜真实HT推理与通过性评测工具

标签：[`ht-stage-20260921-real-ht`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20260921-real-ht)；归档提交：[`4315dd9`](https://github.com/CQULzz/HT_Explo/commit/4315dd9deaed24245d6fbdd3c8ebe8726f74b476)；类型：评测与接口。

- **改动：** 增加固定通过性评测、数据/模型审计、配对推理和真实学生模型山地闭环。
- **实现功能：** 将真实八方向预测接入雷达观测高程，区分模型误放/误拒、路线选择和实际车辆通过。
- **验证结果：** 山地各2轮60秒中，HT平均新增表面体素550.5，基线606.5，未显示探索提升；暴露HT提前返回造成返航遗漏。
- **存在问题：** 传感器适配且地形来自训练域；旧软代价、近地盲区和返航问题仍在，不能以离线准确率代替闭环效果。
- **控制/功能来源：** `df8815c`；归档提交不表示修改了运动规划算法。
- **证据：** [README.md](experiments/traversability/README.md) · [REPORT.md](experiments/traversability/evidence/REPORT.md) · [REPORT.md](experiments/results/mountain_live_20260921/REPORT.md)

<a id="stage-05"></a>

### 05｜起点先验、降级预算与返航状态

标签：[`ht-stage-20260922-return`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20260922-return)；归档提交：[`29f80bc`](https://github.com/CQULzz/HT_Explo/commit/29f80bc76789a7075f4dfb987cb2e51bfbb56add)；类型：功能。

- **改动：** 固定起点并限制缺测先验，累计未知降级预算；补任务状态、到家停车确认、返航拼接和单调检查点。
- **实现功能：** 区分探索结束与真正返航完成；地图故障时停车，恢复后继续；提供可复用回归验证。
- **验证结果：** 限定山地小场景中一组基线/HT均到家完成；另有地图暂停6秒恢复检查。
- **存在问题：** 小样本且HT运行有约52秒几何降级，不能称为纯HT或全域完成；仍是软风险代价与CMU控制器，非当前XYθ。
- **控制/功能来源：** `b847710`；归档提交不表示修改了运动规划算法。
- **证据：** [HT_TARE_REMEDIATION_IMPLEMENTED.md](docs/HT_TARE_REMEDIATION_IMPLEMENTED.md) · [REPORT.md](experiments/results/remediation_stock_20260922/REPORT.md) · [REPORT.md](experiments/results/remediation_map_outage_20260922/REPORT.md)

<a id="stage-06"></a>

### 06｜Fixposition与Helios32驱动接入

标签：[`ht-stage-20261010-drivers`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261010-drivers)；归档提交：[`d63b9b8`](https://github.com/CQULzz/HT_Explo/commit/d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30)；类型：功能。

- **改动：** 将Fixposition、RoboSense驱动源码及依赖纳入本工作区，补实车配置和启动接线。
- **实现功能：** 提供定位/里程计与Helios32点云输入入口，工作区构建不依赖相邻驱动工作区。
- **验证结果：** 源码、配置及构建接线按仓库留档；不是完整实车探索验收。
- **存在问题：** 硬件IP、雷达型号、TF/外参、时间同步、方向标定和底盘控制仍需实车确认；有驱动不等于已能安全实车探索。
- **证据：** [THIRD_PARTY.md](THIRD_PARTY.md) · [explore_ht_fixposition.launch.py](src/tare_planner/launch/explore_ht_fixposition.launch.py) · [rslidar_helios32.yaml](src/tare_planner/config/rslidar_helios32.yaml)

<a id="stage-07"></a>

### 07｜Campus地图传输与前瞻航点

标签：[`ht-stage-20261011-campus`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261011-campus)；归档提交：[`087c42d`](https://github.com/CQULzz/HT_Explo/commit/087c42d45801a34a355cac936488efe19141768d)；类型：功能。

- **改动：** HT地图改可靠订阅；只沿已检查且近乎直线的路段跨过近航点；补倒车和探索局限审计。
- **实现功能：** 改善大地图送达和CMU路径末端频繁减速，旧控制器继续实际控车。
- **验证结果：** 15分钟367.85米、该轮HT_MAP_STALE为0；另5分钟对照零线速占比11.2%→5.8%。
- **存在问题：** 长测倒车占48.4%，另一短测79.3%；旧长测缺XY轨迹/探索体积。此时没有实际XYθ闭环，不能用里程代表探索效果。
- **控制/功能来源：** `83b44a3`；归档提交不表示修改了运动规划算法。
- **证据：** [HT_long_run_report_2026-10-11.md](validation/results/HT_long_run_report_2026-10-11.md)

<a id="stage-08"></a>

### 08｜实际XYθ硬约束规划与分层历史高程

标签：[`ht-stage-20261015-elevation-xytheta`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261015-elevation-xytheta)；归档提交：[`8398f53`](https://github.com/CQULzz/HT_Explo/commit/8398f538450a21c4ee9d65d17193ee084eacee03)；类型：功能。

- **改动：** 322ec85一次归档此前本地XYθ、历史高程工作及当日修复：引入Hybrid A*和独立执行器，修正坐标翻转、固定世界索引、分层高程和真实观测时间。
- **实现功能：** 从odom位姿到目标视点规划前进/倒车/原地旋转路径；P≥0.5硬门槛、默认严格未知；全局历史高程裁局部窗口供HT推理。
- **验证结果：** 180秒实际HT控车仅行驶14.35米；对应窗口接收984帧、成功融合窗口983帧；225组地图时间戳一致。
- **存在问题：** 运动连续性差、旧许可1.5秒超时导致大量停车，目标反复切换；仍有噪声/未知区，未完成探索或实车验证。10月12日只是本地实验日期，不是独立Git发布。
- **控制/功能来源：** `322ec85`；归档提交不表示修改了运动规划算法。
- **证据：** [XYTHETA_EXPERIMENT_2026-10-12.md](docs/XYTHETA_EXPERIMENT_2026-10-12.md) · [HISTORICAL_ELEVATION_EXPERIMENT_2026-10-12.md](docs/HISTORICAL_ELEVATION_EXPERIMENT_2026-10-12.md) · [ELEVATION_MAPPING_FIXES_2026-10-15.md](docs/ELEVATION_MAPPING_FIXES_2026-10-15.md) · [REPORT.md](docs/results/ht_validation_2026-10-15/REPORT.md)

<a id="stage-09"></a>

### 09｜目标保持与执行器独立校验

标签：[`ht-stage-20261015-goal-continuity`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261015-goal-continuity)；归档提交：[`dbce623`](https://github.com/CQULzz/HT_Explo/commit/dbce623161087fcaac865b1d4db5305d1cfe2c9c)；类型：功能。

- **改动：** 按世界位置保持目标、停滞冷却、稳定全局引导、候选预筛和侧向恢复；跟踪器独立读取新鲜HT图校验路径。
- **实现功能：** 减少目标尚未完成时反向切换；HT启用时旧Bool许可年龄不再单独触发停车，地图/扫描/定位/路径时效和显式禁止仍有效。
- **验证结果：** 一轮180秒56.54米，目标方向反转9→0；149项核心、13项HT ROS和4项跟踪器检查通过。
- **存在问题：** 同代码后续复跑29.76米、102秒后长期停车，故不能把这次56.54米视为稳定通过。仍有规划/执行采样不一致。
- **证据：** [xytheta_execution_continuity.md](docs/xytheta_execution_continuity.md) · [REPORT.md](docs/results/ht_continuity_2026-10-15/REPORT.md) · [REPORT.md](docs/results/ht_repeat_2026-10-15/REPORT.md)

<a id="stage-10"></a>

### 10｜同版本复跑失败与完整数据发布

标签：[`ht-garage-repeat-20261015-1225`](https://github.com/CQULzz/HT_Explo/tree/ht-garage-repeat-20261015-1225)；归档提交：[`0b842e4`](https://github.com/CQULzz/HT_Explo/commit/0b842e4ab71a1ed0249cc32da923a0f51940106a)；类型：失败复跑归档。

- **改动：** 新增完整视频、CSV/快照/录包下载与校验清单；697ae2e随后补GitHub下载和SHA-256复核。
- **实现功能：** 可以复现并查看约102秒后的失败全过程，保留原Release附件链接。
- **验证结果：** 180秒29.76米，最后60秒0米；HT_PATH_BLOCKED对应1562个零速指令样本。
- **存在问题：** 这是失败证据归档，不是算法修复；控车仍为dbce623。上层HT_ASSISTED不代表执行端允许运动。
- **控制/功能来源：** `dbce623`；归档提交不表示修改了运动规划算法。
- **证据：** [REPORT.md](docs/results/ht_repeat_2026-10-15/REPORT.md) · [github_upload_verification.json](docs/results/ht_repeat_2026-10-15/github_upload_verification.json)

<a id="stage-11"></a>

### 11｜统一运动段检查与执行拒绝反馈

标签：[`ht-stage-20261016-swept-check`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261016-swept-check)；归档提交：[`919d826`](https://github.com/CQULzz/HT_Explo/commit/919d826f340c11e34421a738e80d2a2e85066eb9)；类型：功能。

- **改动：** 3912e37使规划、发布前和执行共用motionSupport及经过栅格检查；拒绝边反馈、6秒冷却重规划；后续提交补两轮视频/统计。
- **实现功能：** 消除已复现的规划通过/执行拒绝循环；检查车头变化、倒车方向和前约1米路径；不放宽HT门槛或未知策略。
- **验证结果：** 冻结原停车地图：旧路一致拒绝、重规划41姿态；155项核心、15项HT ROS、5项跟踪器检查通过。两轮180秒57.87/63.45米，最长完全零速1.65/1.50秒。
- **存在问题：** 只解决特定持续拒绝循环；仍有转向、回访与短暂停顿，短测不保证全局探索完成；最新长测进一步证实长期推进不足。
- **控制/功能来源：** `3912e37`；归档提交不表示修改了运动规划算法。
- **证据：** [REPORT.md](docs/results/ht_swept_gate_2026-10-16/REPORT.md)

<a id="stage-12"></a>

### 12｜最新原版TARE配对评测

标签：[`ht-stage-20261016-tare-compare`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261016-tare-compare)；归档提交：[`07ab006`](https://github.com/CQULzz/HT_Explo/commit/07ab0067dc7f47dc6eb7e5e2b9924f79f2ed9a24)；类型：对比评测归档。

- **改动：** 增加同场景/同前进目标的独立配对运行、公共自由体积统计、对比图和分屏视频。
- **实现功能：** 明确量化原版与当前完整系统差距；与上阶段相比没有再升级运动规划算法。
- **验证结果：** 180秒原版/HT里程81.08/54.52米，估计自由体积6242.625/3224.625m³；HT体积约为原版51.7%。
- **存在问题：** 每组一次且倒车/角速度/加速度未完全对齐，是端到端比较；HT转向、停车和回访更多，未追平原版。
- **控制/功能来源：** `3912e37`；归档提交不表示修改了运动规划算法。
- **证据：** [REPORT.md](docs/results/tare_ht_pair_2026-10-16/REPORT.md)

<a id="stage-13"></a>

### 13｜60分钟长测：运行连续但探索停滞

标签：[`ht-stage-20261016-endurance`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261016-endurance)；归档提交：[`6bd5407`](https://github.com/CQULzz/HT_Explo/commit/6bd5407b781771b0460ed1533eaee6d500c91bc4)；类型：长测归档。

- **改动：** 新增长测启动、健康与资源记录、抽样录包、源时间戳计数审计、分析工具及报告/视频；实验运行树基线为07ab006。
- **实现功能：** 可检验长期资源增长、输入延迟、运动拒绝反馈与探索增益；被测规划算法与上阶段相同。
- **验证结果：** 60分钟993.48米，无被测进程意外退出或重启；后40分钟又走约650米，仅增2.5m³估计自由空间，最后10分钟为0。
- **存在问题：** 未通过持续有效探索验证；全局引导长期不变、重复回访，网卡掉线时发生约13秒输入中断；内存未失控但持续扩图上界未验证。
- **控制/功能来源：** `3912e37`；归档提交不表示修改了运动规划算法。
- **证据：** [REPORT.md](docs/results/ht_endurance_2026-10-16/REPORT.md) · [validation_checks.json](docs/results/ht_endurance_2026-10-16/validation_checks.json)

<a id="stage-14"></a>

### 14｜全局停滞恢复与返航容差修正

标签：[`ht-stage-20261016-progress-memory`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261016-progress-memory)；归档提交：[`9393e7d`](https://github.com/CQULzz/HT_Explo/commit/9393e7da7d1eeabf04a4325593834304f236e405)；核心：`c85ad1f`。

- **改动：** 全局引导独立进展计时、180秒失败冷却、世界坐标重复访问记忆；修正恢复评分、返航检查点到达容差及无用探索搜索。
- **实现功能：** 局部目标完成不再掩盖全局停滞；零收益主目标不能压住所有恢复候选；保留HT硬门槛、严格未知和速度上限。
- **验证结果：** 242项核心、15项ROS和5项跟踪测试通过。两轮20/25分钟；最新同期20分钟估计观测6498m³，对照3293.875m³；第10–20分钟增益1654.125m³，对照26.375m³。25分钟447.50米、294格，最终EXPLORING。
- **存在问题：** 第一轮返航BLOCKED；已补容差回归，但最新一轮未触发返航，不能称闭环通过。尚未重跑60分钟；地图年龄最高4.17秒，仍有过期停车。没有真值全域覆盖率或实车验收。
- **证据：** [两轮报告与视频](docs/results/ht_progress_fix_2026-10-16/REPORT.md)。

## 全部历史提交逐条说明

下表覆盖截至6bd5407的27个归档提交，包括资料、方案和数据格式提交，避免把每一次push都误认为算法升级。点击提交可查看当时源码和差异。当前补充版本说明本身属于文档维护，不新增导航功能。

| 日期 | 提交 | 类别 | 改动 | 功能 / 问题 |
|---|---|---|---|---|
| 2026-09-14 | [`46f9642`](https://github.com/CQULzz/HT_Explo/commit/46f9642221ff7e251e601818a45fe041831b928c) | 规划原型 | 八方向有向软风险代价和局部TSP | 可输出保守短航点；无实际XYθ、低概率仍可被选择。 |
| 2026-09-15 | [`c4b7a41`](https://github.com/CQULzz/HT_Explo/commit/c4b7a41d3ae3466c8b5eb043c8f1f3f81b3c9e8d) | 构建与规划修复 | Jazzy/OR-Tools、输入校验、起点航点停滞修复 | 合成地图运动/故障恢复通过；不证明真实HT探索效果。 |
| 2026-09-20 | [`e1afe89`](https://github.com/CQULzz/HT_Explo/commit/e1afe895b3e7856861be12196ba8b07a912befbf) | 失败实验归档 | 六轮Garage对照与切角诊断 | 保留HT一轮约219秒停滞；该提交尚未修复。 |
| 2026-09-20 | [`df8815c`](https://github.com/CQULzz/HT_Explo/commit/df8815c61a22a76d0314d372e4c280ac233ee23c) | 规划修复 | 拒绝图上的切角边，共用连通检查 | 修复旧有向图特定不一致；仍为合成HT输入评测。 |
| 2026-09-20 | [`a6c015a`](https://github.com/CQULzz/HT_Explo/commit/a6c015a3a3f703d0b0acb880ed0230e08d49f9bd) | 复测归档 | 补三轮修复后对照及独立重算 | 短测不再持续卡住；均未探索完成。 |
| 2026-09-21 | [`60fda52`](https://github.com/CQULzz/HT_Explo/commit/60fda52dcc55342dacd81de94f9591af98ae14b8) | 评测工具 | 固定通过性分类与路线选择评测 | 可接真实标签CSV；合成测试不是模型精度。 |
| 2026-09-21 | [`f7a7ae1`](https://github.com/CQULzz/HT_Explo/commit/f7a7ae1b0f71aed548a48958e819dfc09aaad837) | 数据格式 | 统一生成CSV换行 | 无规划功能变化，指标数值不变。 |
| 2026-09-21 | [`54f5324`](https://github.com/CQULzz/HT_Explo/commit/54f53240eaf1ff77931f80c78854ced2b63e3234) | 证据审计 | 核对模型、标签、历史曲线和数据划分 | 离线结果存在泛化与标签溯源边界，不能当闭环效果。 |
| 2026-09-21 | [`f4577e8`](https://github.com/CQULzz/HT_Explo/commit/f4577e8ea0661b4eb2861ecc4751bbdeb150a618) | 模型评测 | 配对Scout检查点推理与筛选指标 | 形成误放/误拒和对照图；不是导航策略升级。 |
| 2026-09-21 | [`4315dd9`](https://github.com/CQULzz/HT_Explo/commit/4315dd9deaed24245d6fbdd3c8ebe8726f74b476) | 闭环实验工具 | 真实八方向学生模型与在线雷达高程山地试验 | 两组各2次未显示HT探索提升，并发现HT返航遗漏。 |
| 2026-09-22 | [`05f2bd6`](https://github.com/CQULzz/HT_Explo/commit/05f2bd64dff42dfb35dc6a73b349cbdb4c06ce49) | 方案文档 | 记录起点盲区、降级和返航整改计划 | 仅方案，不表示功能已实现或验证。 |
| 2026-09-22 | [`3912524`](https://github.com/CQULzz/HT_Explo/commit/3912524be6184d9cd860ae28c24b3ee622dae346) | 任务与执行修复 | 固定起点、缺测先验/降级预算、到家停车确认与返航接线 | 实现任务状态与约束；后续仍需修正返航节点反复吸附。 |
| 2026-09-22 | [`b847710`](https://github.com/CQULzz/HT_Explo/commit/b8477101476bfbff09c97f22190fa0c7c40ee54c) | 返航修复 | 返航检查点只向前推进，补地图暂停用例 | 避免返航反复选回已通过点；不保证动态封路可脱困。 |
| 2026-09-22 | [`29f80bc`](https://github.com/CQULzz/HT_Explo/commit/29f80bc76789a7075f4dfb987cb2e51bfbb56add) | 验证归档 | 归档小场景完成和地图失联恢复结果、可复用检查 | 小样本通过不代表大范围探索或实车能力。 |
| 2026-10-10 | [`d63b9b8`](https://github.com/CQULzz/HT_Explo/commit/d63b9b8db2c9aecea20aa2390fc89cfc0fd5ed30) | 硬件输入接入 | 纳入Fixposition、RoboSense源码及独立工作区配置 | 提供定位/点云接线；未完成实车标定及任务验收。 |
| 2026-10-11 | [`83b44a3`](https://github.com/CQULzz/HT_Explo/commit/83b44a37c2e905022c1d396a738092eabdaa3aee) | 传输与航点修复 | 可靠地图订阅、受检直线前瞻和长测工具 | 改善送达和近航点停顿；仍用CMU控制器。 |
| 2026-10-11 | [`087c42d`](https://github.com/CQULzz/HT_Explo/commit/087c42d45801a34a355cac936488efe19141768d) | 问题审计 | 补大量倒行和探索指标缺失说明 | 不改规划算法；不能把旧15分钟里程当覆盖率。 |
| 2026-10-15 | [`322ec85`](https://github.com/CQULzz/HT_Explo/commit/322ec85c728c5900d3e47f22b4c3c5a4e6bccc99) | 规划与高程改造 | 归档实际XYθ硬约束/跟踪器、历史裁图及坐标/分层/时效修复 | 本地10月12–15日工作一次提交；180秒仅14.35米且停车多。 |
| 2026-10-15 | [`8398f53`](https://github.com/CQULzz/HT_Explo/commit/8398f538450a21c4ee9d65d17193ee084eacee03) | 实验与可视化 | 归档实时控车结果、许可超时与视频状态审计 | 无新规划算法；揭示执行衔接停顿仍未解决。 |
| 2026-10-15 | [`dbce623`](https://github.com/CQULzz/HT_Explo/commit/dbce623161087fcaac865b1d4db5305d1cfe2c9c) | 目标与执行修复 | 目标承诺、恢复候选、执行器独立HT校验 | 一轮56.54米，后续同版29.76米失败；未稳定通过。 |
| 2026-10-15 | [`0b842e4`](https://github.com/CQULzz/HT_Explo/commit/0b842e4ab71a1ed0249cc32da923a0f51940106a) | 失败复跑发布 | 完整复跑失败视频、实验包和原始MCAP入口 | 约102秒停车保留；控车代码仍dbce623。 |
| 2026-10-15 | [`697ae2e`](https://github.com/CQULzz/HT_Explo/commit/697ae2e82859f0381ee6455d39617159eb97295a) | 发布验证 | 补远端附件大小/哈希和下载视频复核 | 不改变算法，也不修复102秒停车。 |
| 2026-10-16 | [`3912e37`](https://github.com/CQULzz/HT_Explo/commit/3912e37df7541799c354bf568ff8f3d5b0383aab) | 规划执行一致性修复 | 共用motionSupport和扫掠检查、失败运动反馈与6秒冷却 | 修复已复现拒绝循环；仍不保证探索推进。 |
| 2026-10-16 | [`352526b`](https://github.com/CQULzz/HT_Explo/commit/352526b9be0835d28a43e45d8ebf87d9db6efa66) | 回归与视频归档 | 原停止地图C++重规划及第一轮180秒证据 | 57.87米，最长零速1.65秒；不等于完成探索。 |
| 2026-10-16 | [`919d826`](https://github.com/CQULzz/HT_Explo/commit/919d826f340c11e34421a738e80d2a2e85066eb9) | 重复验证归档 | 第二轮180秒、连续零速审计及三轮对比 | 63.45米，最长零速1.50秒；算法仍3912e37。 |
| 2026-10-16 | [`07ab006`](https://github.com/CQULzz/HT_Explo/commit/07ab0067dc7f47dc6eb7e5e2b9924f79f2ed9a24) | 原版对比评测 | 统一自由体积口径、CSV/曲线/对比视频 | 当前HT探索效率落后原版；非完全匹配控制器消融。 |
| 2026-10-16 | [`6bd5407`](https://github.com/CQULzz/HT_Explo/commit/6bd5407b781771b0460ed1533eaee6d500c91bc4) | 长测归档 | 60分钟监测脚本、统计、视频与失败结论 | 无核心规划升级；揭示持续运动下长期探索停滞。 |
| 2026-10-16 | [`d9eabd7`](https://github.com/CQULzz/HT_Explo/commit/d9eabd7b6c91f9c4ff160b9969f1ec7196225742) | 版本文档 | 标注13阶段的改动、功能、验证与问题 | 仅历史说明，无导航功能变更。 |
| 2026-10-16 | [`71a2748`](https://github.com/CQULzz/HT_Explo/commit/71a27484ebda62700aa4466d0f91a46ee9ebbfe0) | 版本发布工具 | 通过仓库限定Actions同步中文Releases | 保留已有标签及附件，无导航功能变更。 |
| 2026-10-16 | [`7f1c253`](https://github.com/CQULzz/HT_Explo/commit/7f1c253feccb1b7ec4b4912f70312d7b308e3a20) | 全局进展与恢复修复 | 引导独立停滞检测、失败冷却、重复访问记忆和恢复评分 | 20分钟探索明显改善，但末尾返航BLOCKED。 |
| 2026-10-16 | [`c85ad1f`](https://github.com/CQULzz/HT_Explo/commit/c85ad1f004bbaceae14cd65351be38c3a9e61273) | 返航与恢复边界修正 | 对齐返航检查点到达容差、移除返航无用探索搜索 | 242核心及20ROS/跟踪测试通过；最新25分钟未触发返航，闭环仍待验。 |
| 2026-10-16 | [`9393e7d`](https://github.com/CQULzz/HT_Explo/commit/9393e7da7d1eeabf04a4325593834304f236e405) | 两轮证据归档 | 等时长比较、CSV、任务审计及可解码视频 | 最新25分钟447.50米、294格；没有把运行定时结束写成完成探索。 |

## 怎样取回指定版本

```bash
git fetch origin --tags
# 在独立目录查看历史快照，保留当前工作区
git worktree add --detach ../HT_Explo-stage11 ht-stage-20261016-swept-check
```

历史快照必须在自己的工作区重新构建；不能借用当前版本已编译的节点来声称复现旧算法。独立CuPy/CMU工作区与模型、配置、控制程序哈希以对应实验manifest为准。Git标签只固定本仓库源码，不会自动固定外部工作区。

## 指标不要混用

- 早期Garage是八方向全0.9的合成地图，后期才有真实HT模型；软风险代价和HT硬门槛不能混作同一算法。
- CMU航点跟踪、只用于观察的影子XYθ搜索、实际输出cmd_vel的XYθ跟踪器是不同阶段。只有后者能证明姿态路线参与实际控制。
- 行驶距离/到访轨迹格、参考表面体素命中、光线累计估计自由空间是不同指标，不能跨报告直接拼成覆盖率曲线。
- 短测能动、指定小场景返回完成、完整车库/校园探索完成、实车验收是不同结论；失败复跑、控制参数差异和未测内容均保留。

机器可读索引：[docs/version_history.json](docs/version_history.json)。各阶段的中文发布说明：[docs/release_notes](docs/release_notes)。

## 后续怎样维护

修改 `docs/version_history.json` 和相应 `docs/release_notes/*.md`，先推送与目录匹配的阶段标签，再推送说明。仓库的 [版本说明发布流程](.github/workflows/version-notes.yml)会验证标签指向并同步中文Releases；它只更新目录中的实验预发布说明，不移动标签、删除附件或修改导航代码。
