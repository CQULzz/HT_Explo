# HT + TARE：仿真验证与规划原理

当前分支：`sim/validation-20261022`。算法基线为 `develop@8b10207`，本轮冻结入口为 `e640c0c`，实测标签为 `ht-sim-20261022-input-contracts`。这是专用仿真验证分支；Scout实车配置另在 [real/scout-helios32](https://github.com/CQULzz/HT_Explo/tree/real/scout-helios32)，未合入本次测试。

- [项目完整报告 PDF](docs/planning/2026-10-22_project_report.pdf)
- [规划原理报告 PDF](docs/planning/2026-10-22_planning_principles.pdf) · [可编辑原文](docs/planning/2026-10-22_planning_principles.md)
- [室内、校园各600秒测试结果与历史对比](docs/results/ht_sim_check_2026-10-22/REPORT.md)
- [完整原始记录与视频 Release](https://github.com/CQULzz/HT_Explo/releases/tag/ht-sim-20261022-input-contracts)
- [构建、实验、分析复现](validation/sim_check_2026-10-22/REPRODUCE.md) · [测试日志与源码哈希](validation/sim_check_2026-10-22)

TARE保留覆盖、TSP和访问顺序的关键函数；HT提供方向相关地形硬约束；XYθ路由连接当前位姿与同分支局部目标，独立跟踪器生成并复检速度命令。运动学和指令限幅不等于完整动力学或实车验证。

探索核心在 [src/tare_planner](src/tare_planner)，HT模型、历史高程与桥接在 [tools/ht_cupy_bridge](tools/ht_cupy_bridge)。本分支包含完整探索源码；实验设施、图表和视频仅为配套记录。

构建使用本工作树的 `build_standalone/install_standalone`：

```bash
bash scripts/build_sim_check.sh
```

测试结果须区分采集完整、进程状态和探索效果；完整计时或内部COMPLETED不等于环境真值全覆盖。原始MCAP放Release分片，仓库保存报告、曲线、参数、必要快照和发布校验回执。

[投递与内存统计的补充边界](validation/sim_check_2026-10-22/SUPPLEMENT.md)：室内缺准确投递检查点，10分钟内存窗口不能外推为长期稳定。
