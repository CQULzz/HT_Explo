# 点云QoS、观测原点和诊断

2026-11-01离线候选；[报告与限制](../results/real_tare_input_fix_2026-11-01/REPORT.md)。URDF、静态TF及1696对定位转换一致；修正的是TARE中车体/雷达观测原点混用，未改标定。规划车辆参考点仍为base_link；雷达原点从同一标定派生，按扫描时刻的完整姿态计算。通用入口`sensor_origin_offset`默认零，实车launch传入[0.1725,0,0.5502]。

原始点云接收默认`cloud_reliability:=reliable`；TARE和跟踪器的注册点云接收同为RELIABLE。原包writer支持此策略。若外部writer只提供BEST_EFFORT，可靠订阅无法匹配，应先检查`ros2 topic info /rslidar_points -v`及输入诊断中的兼容性。适配器可显式选`cloud_reliability:=best_effort`，但应单独验证输入率；它只涉及ROS传输，规划状态仍是XYθ。

`/ht_real/input_performance`每秒输出JSON：源码/标定SHA、RMW、publisher QoS、兼容性、各输入计数、队列/静默和最近200次耗时。`cloud_qos_compatible=null`表示尚未发现writer，false表示发现writer但无法按请求可靠性匹配。计数中TF等待/取出是尝试，可重复；processed转换完成后还会再次检查时效/故障，因此不必等于published。diagnostic的累计计数只表示本进程生命周期。

`TARE_SELECTION`日志解释原生候选/队列；visited、other_cell、preselected按顺序互斥排除，eligible为剩余候选。raw_gain/raw_frontier在eligible中独立计数，可能重合；queue为扣除虚拟覆盖后通过门限的队列。原覆盖/TSP/访问顺序和门限保留。

可选共享内存配置位于包内`config/fastdds_large_clouds.xml`。使用Fast DDS时，`dds_profile:=/绝对路径/fastdds_large_clouds.xml`会在本launch的子进程中设置`FASTRTPS_DEFAULT_PROFILES_FILE`；默认空，不改当前DDS配置。独立雷达、配准、CuPy进程不继承这个launch的环境，应在各自启动环境分别设置同一文件，才能比较整条链路。不改内核或全局网络。本机16MiB补充测试两次160/160；车上实际FastDDS版本和配置仍未验收。

构建/部署继续使用实车分支和独立工作区。该版本仅代码/离线验证，不能把一次良好输入率或观测原点修正视为已经解决提前完成、所有近车未知或车上吞吐问题。


安装补丁`real-scout-tare-input-fix-20261101-r1`补齐XML的data_files规则；全新安装的share/ht_scout_bridge/config/fastdds_large_clouds.xml已逐字节核对。原实验tag保持不动，算法与数据沿用原候选，见[安装核对](../results/real_tare_input_fix_2026-11-01/PACKAGING_FIX.md)。
