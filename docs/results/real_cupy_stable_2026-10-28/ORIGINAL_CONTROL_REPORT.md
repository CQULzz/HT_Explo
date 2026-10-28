# 原10月11日录包的控制状态核对

只读原始 `validation/arm_vehicle/results/demo_20261011_225010/rosbag` 全15个SQLite分包。时间均是消息接收时间减去metadata记录起点，不是新版重放时钟。没有重发命令，没有运行车辆。旧节点的完整二进制提交号与全部运行时参数覆写尚未确认，以下只陈述可直接读取的消息及配套配置。

## 旧运行模式与当前实验不同

- 配套 `manifest.json` 明确记录 `policy: best_probability; ground/obstacle checks retained`。
- 配套 `ht.yaml` 订阅 `/ht_traversability/best_policy`，记录 `ht_unknown_policy: geometric_fallback`、`ht_startup_duration: 0.001`、`ht_map_timeout: 1.0`、回退时间预算60s，且原HT有效性半径0.1m/footprint_radius0.6m。
- 当前实验是严格未知、configuration语义的实际C++ XYθ固定目标检查，并非复现旧best_probability闭环。因此不能将当前0/1664直接当作旧实车停车的完整因果证明。

## 实际记录的指令与停止时间

`/cmd_vel` 共4049条；163条线/角至少一个分量非零，其中线速度非零27条、角速度非零163条。非零指令只出现在 **t=50.238–80.702s**，最大|vx|=0.26m/s、|wz|=0.15rad/s；80.702s后直到录包结束，记录的命令一直为零。

停止附近原始状态顺序：

- t80.014s：controller `TRACKING`。
- t80.702s：最后一条非零 `/cmd_vel`。
- t80.802、81.810、82.902s：controller `NO_SAFE_LOCAL_ROUTE`。
- 同一附近 t80.947–81.038s：上层仍发布 `HT_ASSISTED`，导航允许在t80.951/81.037s仍为true。
- t83.249s以后多次出现 `PLANNER_HOLD`，并与 `NO_SAFE_LOCAL_ROUTE`、`HT_MAP_STALE` 等交替。
- 最后上层执行状态 t207.049s 为 `FALLBACK_BUDGET_EXHAUSTED`，mission为 `BLOCKED`，导航允许=false；最后controller状态为 `PLANNER_HOLD`。

这直接表明上层曾允许导航、执行端仍独立拒绝安全局部路线。记录没有在这些状态字符串中给出具体失败约束，不能据字符串断言是哪一个HT像素或哪一种动力学约束所致。

**重要时间反证：** 车后持续高点群在t108.089s之后出现，晚于最后非零指令约27.4s。因此该后半段高点群不能单独解释t80.7s首次停止。此前t11.6–13.1s也曾短暂出现高点群，历史图可能保留其影响，但其对旧控制失败的具体贡献未被隔离。

## 状态消息计数（不是持续时间）

| controller原文 | 条数 |
|---|---:|
| PLANNER_HOLD | 130 |
| NO_SAFE_LOCAL_ROUTE | 74 |
| HT_MAP_STALE | 23 |
| TRACKING | 22 |
| PERMISSION_STALE | 5 |
| POSE_STALE_STAMP | 3 |
| PERMISSION_MISSING | 1 |
| GOAL_REACHED | 1 |

上层执行消息302条：NO_EXECUTABLE_ROUTE133、GEOMETRIC_FALLBACK85、HT_ASSISTED41、HT_MAP_STALE35、FALLBACK_BUDGET_EXHAUSTED5、BASE_SENSOR_FAULT3。导航允许201条：true88、false113。

桥接状态197条：READY193，另4条SCAN_WAIT（源时间较最新TF约0.014–0.020s超前的未来外插等待）。这说明出现过TF等待，但不能将其说成全部停车的唯一原因。

## 不能从这些数据推断什么

- 指令非零不等于车轮实际运动。当前环境未安装 `scout_msgs`，未直接解码 `/scout_status`，未据此验证电机响应。
- `/ht_vehicle/chassis_odometry` 的2078条twist均为零，但其pose/yaw确实变化；它可能是构造的定位参考话题，**不能将这些零twist直接当成“车轮一直不转”证据**。
- 配套旧CSV/摘要还记录了实测底盘速度，属于历史附带报告；本次没有将其和bag时钟强行对齐或作为独立重算结果。
- 状态计数不代表时长占比；状态有重复及变化事件，不能用130/259宣称某状态持续50%。

完整解码记录在 `ORIGINAL_CONTROL_TRACE.json`，汇总与10秒命令分箱在 `ORIGINAL_CONTROL_SUMMARY.json`，复现脚本 `original_control_audit.py`。配套配置/manifest的原路径与SHA见 `SOURCE_MANIFEST.json`。
