# 额外核验（不修改导航）

本目录记录2026-10-22的测后核验。采集时间和冻结版本保持frozen_job.json所记的2026-10-21。

- `tare_contract.json`：运行`python3 scripts/check_tare_waypoint_contract.py`，六函数体对照通过；参考b6760adb。
- `cleanup_timing_tests.log`：`python3 -m unittest discover -s presentations -p test_matched_tare_cleanup.py -v`，四项通过。
- `runtime_hashes_after_measurement.json`：逐个重算HT manifest.source_hashes的SHA256，72项一致。
- `curve_interpretation.json`：原始observation_volume.csv按相同规则计算每分钟及末60秒新增量；持续领先时刻使用1秒插值曲线，仅作读图辅助。
- `ht_acceleration_exceptions.json`：读取完整MCAP的/cmd_vel，按与motion_envelope_audit.json相同条件复算：0<相邻header间隔<0.3s，排除当前v=w=0，若|Δv|>0.5Δt+0.005或|Δω|>1.2Δt+0.005记超限。保留前后指令与同时间附近状态。
- `complete_report.py`：本次解读脚本快照；对已处理的同一job生成本目录和报告解读，运行前检查后处理完成标记。

原始MCAP在Release完整raw附件；逐组采集/运动/退出审计见上级original和ht目录。一次性后处理入口：先source /opt/ros/jazzy/setup.bash，再执行process_campus_comparison.py --state JOB；JOB格式见frozen_job.json，入口仅接受MEASUREMENTS_COMPLETE且结果目录尚不存在的状态。封存后不要覆盖原证据；复算时使用独立派生目录并按各单步脚本重算，不能直接重复运行一次性入口。RViz是实际窗口离线回放，不是在线延迟或无故障证据。
