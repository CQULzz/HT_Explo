# CMU 上游 TARE + 最小八方向接入

本入口保留官方 TARE 的 indoor 配置、目标选择、覆盖/TSP和返航代码。原生组运行上游 CMU localPlanner/pathFollower；HT组运行 `cmu_local_planner_ht` 中对应源码的副本，仅增加候选路径门禁和实际速度扫掠门禁。两组使用同一个上游 TARE 可执行文件；上游 ROS2漏声明的 kUseFrontier 通过一行声明修正，以读取既有YAML值，补丁单独保存。

HT读取项目现有FP32八方向模型和权重，采用configuration实际车头语义、0.5分数门限、1秒源图龄、与CMU原生路径库一致的0.45米物理支撑半径（另加网格余量）和独立原生碰撞检查。不新增TSP目标重排、Hybrid A*、启动放行、小孔放宽或完成判据。

- `simulation.launch.py`：native/ht 模式；stock/downward 共同传感配置。
- `prepare_sensor.py`：为共同测试生成向下观察雷达与自车射线遮挡处理；保留原生环境/传感文件。
- `collect.py`：实际里程、状态、图龄、采样射线自由体素并集和表面体素统计；起始信号只发仿真ROS域。
- `../../src/cmu_local_planner_ht/src/ht_gate_test.cpp`：生产门禁同位置不同方向、倒车、转向中间方向、未知/障碍/过期/格式错误反例。

实验目录 `/home/lzz/cmu_test_20261110` 保存独立依赖、构建、冻结、原始记录及报告。官方CMU环境模型从官方下载归档按ZIP目录范围提取，8个indoor文件全部通过CRC校验；其余场景未冒充已完整下载。主机为Ubuntu22.04/Humble，MX450 2GB。原有实车工作树与外部工作区未覆盖。

命令门禁采用100ms反应段和有界制动轨迹（平移2.5 m/s²、转向3 rad/s²），替代误使转向超调的一秒恒定命令外推。此包拒绝时立即发送零速度，CMU仿真直接应用速度，因此该停车包络在此仿真接口上为保守检查；实车需要独立标定制动能力。初版停滞的原始记录与旧源码/二进制已保留。

实车Scout的0.6米圆形包络不直接套给CMU简化车体。测试入口给规划和执行共同显式传入0.45米，依据为官方localPlanner.cpp searchRadius及0.6×0.6米规划尺寸（外接圆0.4243米）；神经概率和未知规则不变。

当原跟踪器起步命令不满足HT而当前位姿有效时，只对同一原生线速度尝试0.5/0.25/0.125/0倍转向。每个候选均执行同一概率/物理支撑/碰撞/图龄及停车轨迹检查，无可行候选则零速。投影记录发布在/ht_minimal/command_projection，保留原生及实际选择命令。

本机复跑（会启动新的600秒仿真，只在需要新试验时执行）：source本任务env.sh及install_cmu、install_native、install_gate、install_mapper的setup.bash后，运行`python3 tools/cmu_minimal/run_pair.py --case ht --attempt 7`，使用全新目录，已有尝试不覆盖。仿真数据留在/home/lzz/cmu_test_20261110/runs。
