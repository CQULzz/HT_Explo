# 可比较实验的种子入口

用户已确认完成判据验收与最多4个候选、含基线/复跑最多8×120秒预算。原状b00已使用1次。本提交仅建立TARE贪心采样流和Gazebo显式种子入口，默认-1保持原random_device行为，不改变阈值、覆盖/完成判据或TSP策略；后续固定42/99的两轮基线与候选分别配对，ROS/GPU调度仍有不确定性。

生产SelectViewPoint两实例同种子30次采样序列一致且非恒定；默认/uint32种子边界验证通过（2项GTest，1组CTest），启动入口5项测试通过。两个包编译通过，已有signedness warnings仍在。正式实验日志必须同时出现TARE_RANDOM配置及Gazebo --seed命令，运行清单记录种子。预算账本在WSL /home/w_lzz/ht-iterations-20261105/cycle2/BUDGET.json，每次启动前计数，失败也占总次数。暂无优化收益结论，不创建Release、不部署。
