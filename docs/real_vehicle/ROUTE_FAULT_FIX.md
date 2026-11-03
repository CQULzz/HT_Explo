# 路线故障误反馈与前沿参数修复

日期：2026-11-02（Asia/Shanghai）。仓库：`/mnt/nvme0n1/autoware/HT_Explo`，分支 `real/scout-helios32`，基线 HEAD `b1b73c77bb49a82c5d667c77ab328c334d32585c`，叠加原有未提交高程证据修正。该修复验证时尚未提交或推送；后续发布以本分支 Git 历史为准。

## 已修复

1. **地图在校验途中到期，会被误记为地形阻塞。** 跟踪器入口检查地图后，还需执行路径/几何及制动弧校验；期间 `motionSupport()` 可返回 `FAULT`。原代码把所有不许可结果统一报成 `HT_PATH_BLOCKED` 或 `HT_COMMAND_BLOCKED`，并可能向规划器发拒绝边。规划器接收后清空当前路径，并加入 6 秒执行失败记忆。现在故障按真实地图状态停车，不发地形拒绝边，同时清除阻塞累计时间；速度发布前再次检查原有地图时效。真实障碍和 strict unknown 仍按原规则拒绝。
2. **`kUseFrontier` 配置未被声明。** YAML 中虽有该参数，主节点只显式声明其他参数，两个消费者的二参数 `get_parameter()` 返回 false，留下未初始化布尔成员；局部规划器又从视点管理器复制这个值。现在主节点声明默认 true，正确接收 true/false 覆盖，两端采用必须成功的类型读取，缺失声明不会静默使用未初始化值。增加标准 NodeOptions 构造参数用于真实参数覆盖回归，默认调用保持兼容。该缺陷能解释前沿标志不可靠，尚不能据此断言它解释了全部历史过早完成。

新增 `HT_MOTION_REJECT` 日志记录支撑结果、路径/命令弧标记、源地图时间、年龄以及两端实际 x/y/yaw。支撑枚举为 KNOWN=0、STARTUP_PRIOR=1、UNKNOWN=2、BLOCKED=3、FAULT=4。故障直接通过原状态话题解释，不作为地形拒绝反馈。

## 证据与验证

- 旧逻辑反例：`baseline_frontier.log` 确认主节点没有声明 kUseFrontier；`baseline_expiry.log` 确认过期地图分别返回错误的 HT_PATH_BLOCKED / HT_COMMAND_BLOCKED。后者还保留测试自身误用 executor 的异常，候选已修正该测试问题；错误状态断言发生在异常前，不将该异常当作产品故障。
- 新增三项回归：默认/true/false 参数传至两个消费者；入口新鲜后确定性推进时钟到过期、路径与命令弧均不发拒绝反馈；停止地图更新时零速停车且无错误反馈，新鲜地图恢复后恢复跟踪。
- Jetson ARM/Humble：`scripts/build_real_scout.sh` 构建、安装两包成功，约 218 秒；现有编译 warning 保留于 candidate_stderr.log。
- CTest **8/8 组通过**，约 84.57 秒；**104 项 GTest 通过，4 项跳过**，另 `ht_core_test` **15,241 项断言通过**。三项新回归已包含于上述计数，未重复加总。跳过项为 CapturedTunnelReturn、CapturedMapSearchResolutionAudit、CapturedSafeRoot、CapturedHeadingBoundary 四项历史样本测试，缺对应 fixture；本轮加载了仓库保留的 mixed_turn_stop fixture。
- 完整跟踪器 25 项均通过，覆盖真实障碍、未知、方向/倒车、命令弧零速、路径拒绝反馈身份、时钟回退与停车。原 TARE 覆盖/TSP/访问顺序契约检查通过。
- 安装程序与构建程序的 `.text/.rodata/.data/.data.rel.ro/.eh_frame` 一致。CMake 安装时修改/移除 RUNPATH，故整文件 SHA 不同；均另存完整 SHA 和 RUNPATH。source 实车环境后 ldd 无缺失依赖。
- 初次构建因沙箱 ccache 临时目录不可写失败，改用 /tmp 的独立缓存后成功；初次 ROS 探测因沙箱禁止 DDS 网络失败，获本机网络权限后在 domain176 / localhost 隔离运行。失败日志均保留。

复跑命令：

```bash
cd /mnt/nvme0n1/autoware/HT_Explo
source scripts/source_real_scout.sh
export ROS_DOMAIN_ID=176 ROS_LOCALHOST_ONLY=1 RMW_IMPLEMENTATION=rmw_fastrtps_cpp
export ROS_LOG_DIR=/tmp/ht_route_fault_ros_logs
export HT_CONFIGURATION_FIXTURE="$PWD/docs/fixes/fixtures/mixed_turn_stop.txt"
unset CYCLONEDDS_URI
ctest --test-dir build_real/tare_planner --output-on-failure
python3 scripts/check_tare_waypoint_contract.py
```

## 历史首停与剩余问题

最新运动摘要首次 HT_PATH_BLOCKED 在约 47.902 秒；当时记录地图年龄约 0.969 秒、起点许可仍剩约 15.277 秒、车身 unknown=13、obstacle=0。此时效缺陷与记录吻合，但没有同一时刻的完整地图/源年龄/路径/TF，不能证明那一次拒绝完全由时效造成，也不能把车身无障碍等同于整条路线安全。对齐只用于缩定历史窗口，采样到达延迟不能恢复为精确源时序。

本次保留 1.5 米/60 秒固定起点许可、0.5 概率阈值、strict unknown、1 秒地图时效、自车过滤、模型和 configuration 实际车体 yaw 语义。HT 推理及原有未跟踪的 height_evidence.py 等文件未改动。本轮未启动设备/车辆/仿真、未发布控制到实车、未做 600 秒验收、未复跑完整原始包，也未改变外部 mapper。HT 约 3Hz 的瓶颈、真实盲区未知、稳定自主探索与完整完成语义仍需后续验证。

## 留存

`validation/route_fault_fix_20261102/` 保存 baseline 源码/原工作区补丁、candidate 源码与二进制、原始及候选失败/成功日志、test_summary.json、cpp_xml、源码/模型/安装 SHA、依赖及 RUNPATH、历史时效审计、仅本次 C++ 修改补丁。原有未提交修改和历史数据均保留。未自动发布或清理。
