# HT_Explo 版本说明

更新时间：2026-10-18。维护分支：`codex/ht8dir-v1`。本页按功能阶段整理，并逐条标注全部历史提交；阶段标签是实验里程碑，不代表稳定版。

## 当前版本先看这里

**阶段24诊断复跑仍失败：同导航规则600秒23.86m/993.125m³，约80秒后几何层拒绝根状态。** HT图仍允许当前位姿，不能用阶段23单轮134米宣称稳定。已保存碰撞输入并发现粗视点与实际车位查询不一致；下一轮按同源证据修改。[诊断报告](docs/results/ht_latency_diagnosis_10min_2026-10-18/REPORT.md) · [逐轮总表](docs/experiments/ITERATIONS.md)。

**阶段23：HT车辆配置得分与实测障碍分层，修正旧图出口被统一膨胀封死的接口问题。** 测试代码`149566d`；室内完整600秒134.00m、3170.500m³，最后60秒仍前进10.93m；没有复现旧版数百秒不推进。仍有短暂停车：最长全零指令6.20秒、地图年龄抽样7次超过3秒；最后约2秒BLOCKED，定时结束后是否恢复未验证，未完成探索。

[原因、修改与同图对照](docs/fixes/2026-10-18_configuration_gate.md) · [视频、全部结果及剩余问题](docs/results/ht_configuration_gate_10min_2026-10-18/REPORT.md) · [四轮对比图](docs/results/ht_configuration_gate_10min_2026-10-18/comparison/comparison.png)。HT保持0.5硬门槛，物理障碍/缺测仍检查0.6m车体范围；新接口强制独立障碍层。另修启动先验分支混用神经预测与物理观测的漏洞。单轮结果不作为全环境稳定性或实车安全证明。

**阶段22：混合转弯动作与细角度旋转跟踪，室内完整600秒仍阻塞。** 测试代码`12d85d8`，实际17.82m、778.000m³；相比上一轮32航向单转角的6.64m/432.875m³增加，但低于此前16航向那轮40.34m/1000.125m³，三轮均未完成探索。单次不同轨迹不作普遍优劣或单项因果结论。

[修改内容](docs/fixes/2026-10-18_mixed_turns.md) · [600秒数据、视频与停滞复核](docs/results/ht_mixed_turns_10min_2026-10-18/REPORT.md) · [三轮对比图](docs/results/ht_mixed_turns_10min_2026-10-18/comparison/comparison.png)。保留32档搜索航向，同时提供11.25°/22.5°动作；旋转按整段目标跟踪并确认角速度下降。HT八通道、阈值和足迹未变；模型语义与足迹接口仍未解决。每轮行为修改至少600秒，规范写入AGENTS.md和[实验约定](docs/experiments/ht_iteration_protocol.md)。

**阶段21：修正HT晚拦截仍发非零速度；细化为32航向以解决真实冻结地图中的漏路，闭环仍需逐例核查。**

[通俗修复说明](docs/fixes/2026-10-18_late_hold_zero_twist.md) · [原因核查、反例、原始数据和回归](docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md)。

- 控制消息修正`8e8d2b7`；评估重复分秒修正`37f0d42`；32航向与真实快照回归`67ade71`。HT仍是8通道，硬阈值、未知区和地图时效要求保持不变。
- 旧候选试验发现146次晚拦截仍发非零速度；只修消息后的600秒对照37次晚拦截全部发零，但仍有另一类规划停滞，不能将单项修复说成稳定性通过。
- 原215秒收尾未复现；5.01秒地图最坏延迟出现在收尾以后，不能作为该收尾的原因。单轮体积差异不是配对因果结论。
- [阶段20历史两场景返航记录](docs/results/ht_recovery_10min_2026-10-17/REPORT.md) · [历史五环境与室内细采样](docs/results/ht_multiscene_10min_2026-10-17/REPORT.md) · [历史60分钟记录](docs/results/ht_endurance_progress_2026-10-17/REPORT.md)。阶段9至20的发布说明已补记后来发现的晚拦截消息缺陷，保留旧标签与原记录。

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
| [14 全局停滞恢复与返航容差修正](#stage-14) | [`9393e7d`](https://github.com/CQULzz/HT_Explo/tree/9393e7da7d1eeabf04a4325593834304f236e405) | 局部目标完成不再掩盖全局停滞；零收益主目标不能压住所有恢复候选；保留HT硬门槛、严格未知和速度上限。 | 第一轮返航BLOCKED；补容差回归后，25分钟轮未触发返航。后续阶段15的60分钟记录验证了一次返回完成，但活动期仍有低增益回访、短时地图过期和关停清理报错；无实车或真值全覆盖验收。 |
| [15 60分钟复测：返回完成但仍有回访](#stage-15) | [`3fe5b9b`](https://github.com/CQULzz/HT_Explo/tree/3fe5b9b5ee23c7a3cc8ec7a0243cdd2d09891a38) | 首次在本次最新规划代码的长测中观察到TARE触发返航并通过到家、低速和停稳条件，任务完成后保持停车；明确区分末尾正常等待与中途低收益回访。 | 活动约44.5分钟，余下15.5分钟为完成后等待，不是主动探索60分钟。中途7.38分钟行驶106.17米仅增2.125m³；地图年龄最高3.37秒，1Hz检查3次超过3秒。主动SIGINT后CMU部分节点关停异常；无运行期意外退出记录。单场景一轮、非真值全覆盖或实车证明。 |
| [16 跨目标记忆与正常关停修复（短测验证）](#stage-16) | [`bd0c2c2`](https://github.com/CQULzz/HT_Explo/tree/bd0c2c24f7eac383a3d8120b312fa4eb499c3199) | 跨目标停滞记忆、零收益回访限制，修复发布调度与正常关停。 | 短回归通过；首轮复测发现BLAS争用，主动中止后进入阶段17。 |
| [17 限制BLAS空转线程与分段计时（数值回归）](#stage-17) | [`f1c8485`](https://github.com/CQULzz/HT_Explo/tree/f1c84854ccc147d40d7f9120c9713ba5e11c736c) | 限制独立BLAS线程池，保留PyTorch2线程，补HT处理分段计时。 | 数值和硬门槛一致性通过；用户改为阶段18的五环境各10分钟。 |
| [18 五环境各10分钟与15fps录像（已完成记录）](#stage-18) | [`6d6998f`](https://github.com/CQULzz/HT_Explo/tree/6d6998f00f5fa9358a7c212b41da6f395ba492a5) | 五环境各600秒，原生15fps录像、裁剪/解码校验和独立报告。 | 五段视频与采集验证通过，但室内原参数/隧道返航受阻；保留延迟、失败诊断与原始配置。 |
| [19 室内视点细化：恢复推进，仍有停顿回访](#stage-19) | [`f3d1eee`](https://github.com/CQULzz/HT_Explo/tree/f3d1eeedae814f99d0db94673c7abadc8eaf7439) | 室内视点从50×50、0.6m改为100×100、0.3m，保持30×30m范围；原HT分辨率、概率阈值、足迹半径、运动学搜索和控制速度不变。 | 仍有最长39.80秒停车和2.3%倒车；第6至7.5分钟行驶22.94m仅增8.375m³，低收益回访未消失。活跃搜索耗时P95为1.576秒、HT年龄最大4.67秒。隧道返航未知足迹问题未解决；每配置一次，不能视为所有场景通过。 |
| [20 观测支撑与停滞恢复：返航通过，探索仍有退步](#stage-20) | [`dee873d`](https://github.com/CQULzz/HT_Explo/tree/dee873db9a25778eb67060100025bea2f619c0ee) | 避免网络缺测重复膨胀及旧方差反复否定历史；保留HT硬阈值、真实未知和碰撞检查，支持安全回退及实际返航。 | 室内约215秒触发返航，总近似观测1900.250→1106.750m³（下降41.8%）；任务收尾不是全覆盖证明。室内HT年龄最大5.01秒，两场景各8个1Hz样本超过3秒。森林约4Hz本轮未重测，其他三场景未重跑。保留约195秒失败诊断；每配置仅一次、无实车或长期稳定性验收。 |
| [21 拦截命令归零与32航向：修正缺陷，仍有停滞](#stage-21) | [`67ade71`](https://github.com/CQULzz/HT_Explo/tree/67ade71c10caa8a8923b9fe9c663d10a9ec75568) | 实际待发速度归零；32航向快照回归；体积评估不重复分秒。 | 已确认消息缺陷修正，但最终室内600秒仅6.64m、432.875m³且BLOCKED；不称为稳定性通过。 |

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
- **存在问题：** 第一轮返航BLOCKED；补容差回归后，25分钟轮未触发返航。后续阶段15的60分钟记录验证了一次返回完成，但活动期仍有低增益回访、短时地图过期和关停清理报错；无实车或真值全覆盖验收。
- **证据：** [两轮报告与视频](docs/results/ht_progress_fix_2026-10-16/REPORT.md)。

<a id="stage-15"></a>

### 15｜60分钟复测：返回完成但仍有回访

标签：[`ht-stage-20261017-endurance-return`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-endurance-return)；归档：[`3fe5b9b`](https://github.com/CQULzz/HT_Explo/commit/3fe5b9b5ee23c7a3cc8ec7a0243cdd2d09891a38)；核心仍为`c85ad1f`。

- **改动：** 对阶段14核心代码进行同Garage连续60分钟记录，补活动/等待分段控制、返航、低收益回访、地图时效及主动关停审计；不新增导航算法。
- **实现功能：** 首次在本次最新规划代码的长测中观察到TARE触发返航并通过到家、低速和停稳条件，任务完成后保持停车；明确区分末尾正常等待与中途低收益回访。
- **验证结果：** 44分28秒左右COMPLETED，距记录起点0.291米；共768.57米、371个轨迹格、6513.750m³近似观测，对照旧60分钟为3296.375m³。7201个轨迹采样、72000条录包控制指令；14项哈希不变，视频完整解码通过。
- **存在问题：** 活动约44.5分钟，余下15.5分钟为完成后等待，不是主动探索60分钟。中途7.38分钟行驶106.17米仅增2.125m³；地图年龄最高3.37秒，1Hz检查3次超过3秒。主动SIGINT后CMU部分节点关停异常；无运行期意外退出记录。单场景一轮、非真值全覆盖或实车证明。
- **证据：** [长测报告与视频](docs/results/ht_endurance_progress_2026-10-17/REPORT.md)。

<a id="stage-16"></a>

### 16｜跨目标记忆与正常关停修复（短测验证）

标签：[`ht-stage-20261017-crossguide-lifecycle`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-crossguide-lifecycle)；核心/短回归归档：`bd0c2c2`。

- **改动：** 全局引导进展跨目标切换保留；零收益到达目标暂缓回访；拆分CuPy发布调度，修复CMU/CuPy/Gazebo关停及完成状态显示。
- **实现功能：** A→B→A不再重置A的停滞预算；新收益可绕过恢复目标冷却；工作区独立，HT硬门槛、严格未知、3秒时效和0.5m/s上限保留。
- **验证结果：** 260核心、15 ROS、6跟踪器、8 CuPy/调度及2关停集成测试通过；第四轮仿真关停回归所有子节点正常退出，无残留。首轮复测发现BLAS线程争用后主动中止；新测试见阶段17。
- **存在问题：** 短测不证明7.4分钟低收益回访已消除；新长测早期仍采样到超过3秒的地图年龄峰值。远端引导仍是距离启发，无完整全局可执行图；未做实车验证。
- **证据：** [修改说明](docs/fixes/2026-10-17_endurance_followup.md) · [四次短回归](docs/results/ht_followup_smoke_2026-10-17/REPORT.md)。

<a id="stage-17"></a>

### 17｜限制BLAS空转线程与分段计时（数值回归）

标签：[`ht-stage-20261017-blas-threads`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-blas-threads)；控制/诊断归档：`f1c8485`。

- **改动：** 单独限制HT桥接的BLAS库为1线程，保留PyTorch2线程；记录实际线程池和融合/支撑准备/网络/发布耗时。
- **实现功能：** 消除周期性小矩阵拟合唤醒28个BLAS工作线程后大量空转的争用；不修改网络权重、HT门槛、未知策略和速度。
- **验证结果：** 诊断默认配置0.653墙钟秒消耗7.695 CPU秒；BLAS单线程0.611墙钟秒消耗0.0105 CPU秒。地面参考最大差0；固定权重HT联合回归硬门槛逐格一致，另有3项参考面与6项融合回归通过。原60分钟按用户新要求改为五环境各10分钟，见阶段18。
- **存在问题：** 该CPU诊断不等于整张HT地图提速700倍，也不是整车长测通过；约17分钟诊断轮主动中止，不作为完成60分钟记录。新长测的探索效率、地图尾延迟和返回完成仍待结果。
- **证据：** [CPU争用诊断](docs/results/ht_blas_contention_2026-10-17/REPORT.md)。

<a id="stage-18"></a>

### 18｜五环境各10分钟与15fps录像（已完成记录）

标签：[`ht-stage-20261017-multiscene-10min`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-multiscene-10min)；源码提交：`6d6998f`。

- **改动：** 参数化仿真/规划场景，串行运行Garage、Campus、Indoor、Forest、Tunnel各600秒；原生相机960×540、15fps，裁剪初始化、编码和完整解码核验。
- **实现功能：** 各组独立地图与进程，独立视频/数据/资源审计，完成一组退出与编码后才进入下一组；底部状态条显示时间、速度、任务和地图/相机年龄，提供播放列表和预览。
- **验证结果：** 五环境均记录600秒，五段H.264完整解码及13项采集/进程验证通过；车库189.57m、校园199.76m、森林168.09m持续推进；室内3.11m与隧道26.33m持续受阻。视频599.933至600秒，允许1帧误差。
- **存在问题：** 室内0.6m候选视点漏掉窄走廊安全区域；隧道返航目标周围足迹含未知格，未到家；地图年龄仍有超过3秒的尾延迟，森林激光平均4.02Hz。10分钟独立重启测试不代表连续一小时、实车或全覆盖通过。
- **证据：** [ht_multiscene_10min.md](docs/experiments/ht_multiscene_10min.md) · [REPORT.md](docs/results/ht_multiscene_10min_2026-10-17/REPORT.md)

<a id="stage-19"></a>

### 19｜室内视点细化：恢复推进，仍有停顿回访

标签：[`ht-stage-20261017-indoor-viewpoints`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-indoor-viewpoints)；源码提交：`f3d1eee`。

- **改动：** 室内视点从50×50、0.6m改为100×100、0.3m，保持30×30m范围；原HT分辨率、概率阈值、足迹半径、运动学搜索和控制速度不变。
- **实现功能：** 为窄HT支撑带提供候选端点，保留原参数失败视频；新增实际栅格、足迹硬门槛、时间戳与配置归档。
- **验证结果：** 独立600秒补测、9000帧完整解码及13项采集/进程核验通过。里程3.11→145.28m，近似观测347.875→1900.25m³，全零指令98.2%→23.0%；运行中实际参数读取与源哈希证明仅室内视点配置不同。
- **存在问题：** 仍有最长39.80秒停车和2.3%倒车；第6至7.5分钟行驶22.94m仅增8.375m³，低收益回访未消失。活跃搜索耗时P95为1.576秒、HT年龄最大4.67秒。隧道返航未知足迹问题未解决；每配置一次，不能视为所有场景通过。
- **证据：** [REPORT.md](docs/results/ht_indoor_sampling_comparison_2026-10-17/REPORT.md) · [REPORT.md](docs/results/ht_indoor_viewpoint_10min_2026-10-17/REPORT.md) · [README.md](docs/results/ht_multiscene_10min_2026-10-17/indoor/diagnostics/README.md)

<a id="stage-20"></a>

### 20｜观测支撑与停滞恢复：返航通过，探索仍有退步

标签：[`ht-stage-20261017-context-recovery`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261017-context-recovery)；实测整栈源码：`dee873d`；C++修改：`73cae0b`；归档：`9fb2b63`。

- **改动：** 区分网络上下文与车体观测支撑；按实际观测时间保留拒绝，有限坏高度仅作八方向禁行上下文；增加12秒原地停滞释放、有限回退和0.35秒共享搜索预算，CPU改4线程channels-last。
- **实现功能：** 避免网络缺测重复膨胀及旧方差反复否定历史；保留HT硬阈值、真实未知和碰撞检查，支持安全回退及实际返航。
- **验证结果：** 311核心、17ROS、6跟踪及53Python回归通过；隧道/室内各600秒、两段15fps视频完整解码及各13项采集核验通过。均COMPLETED；等长前缀最长全零指令145.95→4.30秒、39.80→4.65秒；室内规划P95 1.576→1.004秒。
- **存在问题：** 室内约215秒触发返航，总近似观测1900.250→1106.750m³（下降41.8%）；任务收尾不是全覆盖证明。室内HT年龄最大5.01秒，两场景各8个1Hz样本超过3秒。森林约4Hz本轮未重测，其他三场景未重跑。保留约195秒失败诊断；每配置仅一次、无实车或长期稳定性验收。
- **证据：** [2026-10-17_context_recovery.md](docs/fixes/2026-10-17_context_recovery.md) · [REPORT.md](docs/results/ht_recovery_comparison_2026-10-17/REPORT.md) · [REPORT.md](docs/results/ht_recovery_10min_2026-10-17/REPORT.md) · [REPORT.md](docs/results/ht_context_diagnostics_2026-10-17/REPORT.md)

<a id="stage-21"></a>

### 21｜拦截命令归零与32航向：修正缺陷，仍有停滞

标签：[`ht-stage-20261018-zero-hold`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-zero-hold)；实测源码`67ade71`，归档`b15c06a`；控制消息修复`8e8d2b7`，评估修正`37f0d42`。

- **改动：** 晚HT拦截后清零实际Twist全部六个速度分量；增加真实快照回归并使用32航向搜索；长测按绝对源秒评估已采样激光，避免重复分秒。额外退路和航向余量仍默认关闭。
- **实现功能：** 拒绝命令真正发零；同一真实快照中32航向找到16漏掉的HT路线。HT仍为8通道，未放宽概率、未知区、碰撞或3秒时效要求。
- **验证：** 晚拦截回归旧实现失败、新实现通过；384核心检查、21ROS用例及8跟踪用例通过，4个真实快照均参与。只修消息的600秒对照37次拒绝全部发零，但仍有另一类停滞；最终两环境各600秒，19次晚拒绝全部配对、非零0次；隧道79.00m、621.375m³，约230.53秒返航完成，室内失败。
- **问题：** 冻结图可规划不保证闭环探索成功。最新室内600秒为6.64m、432.875m³，末尾BLOCKED，不能称为改善或稳定通过。原215秒收尾未复现，完成条件未改。旧候选失败和部分场景主动中止分别标记，未充作600秒通过。
- **证据：** [通俗修复说明](docs/fixes/2026-10-18_late_hold_zero_twist.md) · [原因、反例与数据](docs/results/ht_completion_cause_audit_2026-10-18/REPORT.md) · [最终两环境记录及视频](docs/results/ht_zero_twist_fine_heading_10min_2026-10-18/REPORT.md)。

阶段9至20后来复核发现同一晚拦截消息缺陷，已在各阶段发布说明补记；旧记录仍保留，未将所有历史失败统一归因于它。

## 全部历史提交逐条说明

下表覆盖截至b15c06a的59个归档提交，包括资料、方案和数据格式提交，避免把每一次push都误认为算法升级。点击提交可查看当时源码和差异。当前补充版本说明本身属于文档维护，不新增导航功能。

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
| 2026-10-16 | [`2fcf5d2`](https://github.com/CQULzz/HT_Explo/commit/2fcf5d2b741b43313f7f1b9b3c9fe98fd46c518d) | 版本说明 | 标注全局进展与返航修正及20/25分钟证据 | 仅文档维护，无导航变更。 |
| 2026-10-16 | [`0a2d544`](https://github.com/CQULzz/HT_Explo/commit/0a2d5440021117da39ee21abe9b89fba02250c4e) | 目录修正 | 更新历史覆盖范围和提交数量 | 仅文档维护；本轮60分钟运行树。 |
| 2026-10-17 | [`3fe5b9b`](https://github.com/CQULzz/HT_Explo/commit/3fe5b9b5ee23c7a3cc8ec7a0243cdd2d09891a38) | 修复后60分钟归档 | 返航完成、回访、资源和主动关停审计、图与视频 | 验证一次返回闭环；中途低增益回访和关停报错仍保留。 |
| 2026-10-17 | [`a8fdc8c`](https://github.com/CQULzz/HT_Explo/commit/a8fdc8c7f6848ae78d4d3c6eeab9de94e54f1e61) | 实验解读 | 补60分钟返回、低收益回访及主动关停问题说明 | 仅文档修改，未改变上一轮控制程序。 |
| 2026-10-17 | [`bd0c2c2`](https://github.com/CQULzz/HT_Explo/commit/bd0c2c24f7eac383a3d8120b312fa4eb499c3199) | 规划与生命周期修复 | 全局引导进展跨目标切换保留；零收益到达目标暂缓回访；拆分CuPy发布调度，修复CMU/CuPy/Gazebo关停及完成状态显示。 | 短回归通过；新长测正在运行，不宣称绕圈或过期全部消失。 |
| 2026-10-17 | [`5ca71da`](https://github.com/CQULzz/HT_Explo/commit/5ca71da93bd358a1bfc6c713eb8618ed77b88549) | 实验工具 | 自动核验冻结哈希、子进程关停、完整视频解码和回访区间 | 只处理实验完成后的数据，不修改控制路径。 |
| 2026-10-17 | [`b5ec87e`](https://github.com/CQULzz/HT_Explo/commit/b5ec87e17bcd3875a02387474e0dfcfddea3ac96) | 版本说明 | 标注跨目标与关停修复及长测待验边界 | 不修改控制程序。 |
| 2026-10-17 | [`f1c8485`](https://github.com/CQULzz/HT_Explo/commit/f1c84854ccc147d40d7f9120c9713ba5e11c736c) | CPU线程争用修复 | 单独限制HT桥接的BLAS库为1线程，保留PyTorch2线程；记录实际线程池和融合/支撑准备/网络/发布耗时。 | 该CPU诊断不等于整张HT地图提速700倍，也不是整车长测通过；约17分钟诊断轮主动中止，不作为完成60分钟记录。新长测的探索效率、地图尾延迟和返回完成仍待结果。 |
| 2026-10-17 | [`6b5d432`](https://github.com/CQULzz/HT_Explo/commit/6b5d4321d8ca47d1fc03fb62d0e1a9d1ac76b598) | 版本与审计工具 | 标注BLAS争用修复，增加等待/导出审计脚本 | 不改变已冻结的控制程序；原60分钟后被用户调整。 |
| 2026-10-17 | [`6d6998f`](https://github.com/CQULzz/HT_Explo/commit/6d6998f00f5fa9358a7c212b41da6f395ba492a5) | 多场景实验与录像 | 参数化仿真/规划场景，串行运行Garage、Campus、Indoor、Forest、Tunnel各600秒；原生相机960×540、15fps，裁剪初始化、编码和完整解码核验。 | 室内0.6m候选视点漏掉窄走廊安全区域；隧道返航目标周围足迹含未知格，未到家；地图年龄仍有超过3秒的尾延迟，森林激光平均4.02Hz。10分钟独立重启测试不代表连续一小时、实车或全覆盖通过。 |
| 2026-10-17 | [`c086bb1`](https://github.com/CQULzz/HT_Explo/commit/c086bb1ab21ca88e54e8ed0bf4797892fa6de74d) | 版本说明 | 标注五环境十分钟录像协议及被替代的小时任务。 | 文档维护，无规划升级。 |
| 2026-10-17 | [`f3d1eee`](https://github.com/CQULzz/HT_Explo/commit/f3d1eeedae814f99d0db94673c7abadc8eaf7439) | 室内视点参数与证据归档 | 室内视点从50×50、0.6m改为100×100、0.3m，保持30×30m范围；原HT分辨率、概率阈值、足迹半径、运动学搜索和控制速度不变。 | 仍有最长39.80秒停车和2.3%倒车；第6至7.5分钟行驶22.94m仅增8.375m³，低收益回访未消失。活跃搜索耗时P95为1.576秒、HT年龄最大4.67秒。隧道返航未知足迹问题未解决；每配置一次，不能视为所有场景通过。 |
| 2026-10-17 | [`2d74d9c`](https://github.com/CQULzz/HT_Explo/commit/2d74d9c7d4e2d68f9fef9fe653a94aa8aa0196a8) | 五环境及室内补测证据归档 | 归档五环境各600秒及室内细采样600秒，共六段通过完整解码的视频、曲线、配置、日志和诊断。 | 采集/进程核验通过不等于探索成功；室内改善但仍有低收益回访和最长39.8秒停车，隧道返航仍受阻。 |
| 2026-10-17 | [`deb5d14`](https://github.com/CQULzz/HT_Explo/commit/deb5d140cb8e47ef58a279914cd21948791c75aa) | 版本说明 | 标注已完成五环境及室内补测结果和遗留问题。 | 无控制改动，记录阶段18/19结果。 |
| 2026-10-17 | [`73cae0b`](https://github.com/CQULzz/HT_Explo/commit/73cae0b24e72575b8592e772fd818f85ab91a9a6) | HT语义与规划恢复修复 | 区分网络上下文与车体观测支撑；按实际观测时间保留拒绝，有限坏高度仅作八方向禁行上下文；增加12秒原地停滞释放、有限回退和0.35秒共享搜索预算，CPU改4线程channels-last。 | 第一版诊断仍遇墙面质量拒绝导致上下文失效，约195秒主动停止；由dee873d继续修正，未算600秒通过。 |
| 2026-10-17 | [`dee873d`](https://github.com/CQULzz/HT_Explo/commit/dee873db9a25778eb67060100025bea2f619c0ee) | 观测溯源与禁行上下文修复 | 区分真实新观测拒绝与旧方差老化；实际有限坏高度仅作禁行上下文，不融合成地面。 | 室内约215秒触发返航，总近似观测1900.250→1106.750m³（下降41.8%）；任务收尾不是全覆盖证明。室内HT年龄最大5.01秒，两场景各8个1Hz样本超过3秒。森林约4Hz本轮未重测，其他三场景未重跑。保留约195秒失败诊断；每配置仅一次、无实车或长期稳定性验收。 |
| 2026-10-17 | [`9fb2b63`](https://github.com/CQULzz/HT_Explo/commit/9fb2b63ca50a059e4c184f223aaa97e896b185b6) | 两场景复测与证据归档 | 归档两段600秒视频、原始失败、等长任务停车统计、完整前后曲线及播放脚本；补全后续实验SDF冻结清单。 | 不改变已测控制程序；返航成功而室内观测下降的结果均保留。 |
| 2026-10-17 | [`f8a3aa2`](https://github.com/CQULzz/HT_Explo/commit/f8a3aa22129aa00e5c258c0ff8e3db899cf9765d) | 版本目录维护 | Label stage 20 recovery fixes with returned-home validation and remaining coverage regression | 仅文档说明，不改变控制算法。 |
| 2026-10-17 | [`d51cfb5`](https://github.com/CQULzz/HT_Explo/commit/d51cfb53a86e2e849a087dc7fa74e766beb83026) | 版本目录维护 | Update historical catalogue coverage count through the recovery evidence archive | 仅文档说明，不改变控制算法。 |
| 2026-10-18 | [`9fec037`](https://github.com/CQULzz/HT_Explo/commit/9fec0375f8caec2b07a7c0c268f197e1800f5fab) | 只读完成决策审计 | 记录全局与局部队列、HT实际目标收益，不改完成条件。 | 600秒未复现提前完成，反而遇到HT约束停滞；不能据此确认原215秒收尾错误。 |
| 2026-10-18 | [`fde3736`](https://github.com/CQULzz/HT_Explo/commit/fde37365232f8af219488cafd7d1d6e9f6bf73d8) | 退路规则候选 | 可选同弧正反运动硬检查与全频HT入包。 | 室内600秒仍卡住；后查存在晚拒绝发非零命令，不能单独归因于退路规则，现默认关闭。 |
| 2026-10-18 | [`966f3ff`](https://github.com/CQULzz/HT_Explo/commit/966f3ff1921be2eaeee3a4d7b40bf152abbecebc) | 航向余量候选 | 在后继姿态上检查额外角度余量并使用32航向，保留合法根状态回转。 | 单项约212秒中止，未算600秒；候选有混杂且失败，余量现默认关闭。 |
| 2026-10-18 | [`77cd87c`](https://github.com/CQULzz/HT_Explo/commit/77cd87cef62bccc35949deef40dd2c156ef3d112) | 联合约束候选 | 联合航向余量与同弧退路要求。 | 室内600秒仍卡住，发现146次拒绝状态旁有非零速度；隧道314.5秒中止，不算600秒。 |
| 2026-10-18 | [`8e8d2b7`](https://github.com/CQULzz/HT_Explo/commit/8e8d2b768a2e8e347ba4de315df1c68c9079c8ad) | 实际停车消息修复 | 清零待发Twist，新增晚拒绝分支回归并关闭未验证额外约束。 | 旧回归失败、新回归通过；单独修消息仍有另一类规划停滞。 |
| 2026-10-18 | [`37f0d42`](https://github.com/CQULzz/HT_Explo/commit/37f0d42f75220a7098baf2167da61bf38e47fa59) | 评估一致性与控制审计 | 避免对已按绝对秒采样的激光再次分秒；审计实际拒绝指令。 | 同包576恢复600帧，体积仅增加1m³；该评估错误不能解释停车或此前41.8%差异。 |
| 2026-10-18 | [`67ade71`](https://github.com/CQULzz/HT_Explo/commit/67ade71c10caa8a8923b9fe9c663d10a9ec75568) | 有现场依据的航向细化 | 用真实冻结快照证明16漏路、32可找HT合法出口，设32搜索航向。 | 不增加HT通道、不代表所有路径可执行；完整闭环仍有新的禁止起点情形待记录分析。 |
| 2026-10-18 | [`b15c06a`](https://github.com/CQULzz/HT_Explo/commit/b15c06a9d4c476c1e5f6b8e04ad5bcbe9988ecdd) | 原因审计与六段600秒视频归档 | 归档确定的晚拒绝非零命令证据、同图方向边界、两种快照分辨率反例、新有效8格足迹触发及完整失败/成功视频。 | 只读诊断、退路候选、联合候选、单项发零修复各一段室内600秒，最终室内/隧道各600秒；不把技术采集通过当作探索成功。仅更新离线分析与播放器，不改变已测控制源码。 |

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
