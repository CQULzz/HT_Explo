# TARE基线有效性复核与结论更正

用户质疑CMU AEDE中的TARE表现异常。本轮只读核查原始证据、启动入口、已冻结安装参数与上游参考源码，纠正报告解释。历史原始数据、计数和关闭的3/3仿真账本保持原始记录。

## 更正后的结论

循环10测量确认当前HT配置与当前仓库关闭HT后的改装几何配置表现不同。用于衡量原生TARE性能的基线有效性尚未通过，因此原报告3.55倍里程、3.16倍采样体积只能描述这两个接入配置的数值差异。将这些数值用于论证HT优于TARE会超出证据范围，该性能结论撤回。

官方AEDE提供场景、地形分析、局部规划与跟踪等模块，并与TARE及FAR一起发布使用说明。TARE在其配套环境中具有明确的使用路径。仅选用相同indoor模型，无法保证复现了该配套系统。[AEDE原论文](https://arxiv.org/abs/2110.14573)

## 已核实的接入差异

测试启动文件tools/pcd_sim/tare_geometric.launch.py加载ht_scout_bridge安装下的tare_scout.yaml。安装文件与仓库同名文件逐字节一致。该文件是Scout实车配置，参考上游indoor配置共19项顶层参数差异，包含启动和话题映射。下表摘录影响候选与增益计算的参数。

| 参数 | 实测Scout配置 | 上游indoor |
|---|---|---|
| 视点XY间距 | 1.2米 | 0.6米 |
| 视点数量XY | 40×40 | 50×50 |
| 表面点云体素 | 0.5米 | 0.3米 |
| 前沿聚类最少点数 | 30 | 10 |
| 传感范围参数 | 12米 | 7.5米 |
| 使用地形高度 | true | false |

这些差异改变采样与覆盖增益的工作条件。Scout参考高度、碰撞包络等差异还有适配车体的原因，单独某项差异尚无因果隔离实验，不能直接作为错误参数全部恢复。[参数审计与参考文件SHA](BASELINE_AUDIT.json)

ht_enabled=False只关闭HT门控。当前主程序ConcatenateGlobalLocalPath在exploration_finished_后继续使用本项目的keypose图返航检查点，GetLookAheadPoint继续调用checkedLookahead，PublishWaypoint受lookahead有效性和项目完成状态约束。上游固定提交的rush-home分支直接构造ROBOT/HOME路线并发布home目标。这一差异影响返航行为，且与本轮20.23秒返航、36.13秒BLOCKED的阶段相符。具体失败前缀尚未被原日志隔离，不能认定某一条新增检查已被证明导致停车。[上游主程序](https://github.com/caochao39/tare_planner/blob/b6760adb4280b379567c76f4e684ce628e28ef71/src/tare_planner/src/sensor_coverage_planner/sensor_coverage_planner_ground.cpp)

本次prepare_cmu_scene.py复制了完整CMU indoor环境几何和纹理，车辆、激光、物理与定位链沿用Scout仿真，CMU默认vehicle_simulator及sensor_scan_generation链未参加本次采集。传感器几何、数据统计与原生基线仍有适配差异。[场景准备代码](../../../../tools/pcd_sim/prepare_cmu_scene.py)

TARE命令桥几何/路径期限曾从1秒改为3秒并配对重跑。该项修正消除了对应周期性时效拒绝，但没有建立原生TARE算法、配置和输入链等价性。

## 证据及验证边界

上游参考为已保存的官方caochao39/tare_planner固定提交b6760adb4280b379567c76f4e684ce628e28ef71。核查indoor.yaml和主程序的历史来源SHA全部匹配。源码差异保存在PLANNER_DIFF.patch，只读审计脚本可重现19项配置差异。

正确的原生基线验证应先固定上游来源及indoor参数，验证完整AEDE输入与原生目标/返航行为，再将Scout所需的模型/安全适配逐项加入并做对照。现有3次数据仍用于本项目接入诊断，原生TARE成绩仍缺少实测。当前复核未修改导航行为，未产生新仿真成绩。
