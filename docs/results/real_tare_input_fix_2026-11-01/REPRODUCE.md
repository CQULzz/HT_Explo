# 复现与数据索引

本轮只做离线，没有启动设备、仿真、控制或车辆。完整科学附件保留四个目录：HT_drive_audit_20261031_170105（全包解码/审计，不重复打包input中的MCAP）、HT_input_cause_audit_20261101（TF逐帧与传输因果探针/全部失败）、HT_tare_reference_review_20261101（固定上游源码对照）、HT_tare_input_fix_20261101（冻结基线/候选/实际二进制/本轮输出）。另一个附件是完整原始ZIP，SHA见报告。路径仍记录本次绝对输入来源；在新机器复现需按归档位置映射路径，不要直接运行硬件launch。

- 源码：BASELINE_FREEZE.json、CANDIDATE_FREEZE.json、candidate.patch；源快照baseline、candidate、candidate_v1_precheck保留。
- 依赖/TF：urdf_audit原URDF/launch/SOURCE.json、CHAIN_CHECK.json及RECORDED_ORIGINS；原始metadata见输入ZIP。
- 构建/检查：build_v1.log、build_final.log，tested_binaries、BINARY_FREEZE.json；regression_frozen.log325项，ctest_frozen.log8组；REGRESSION_SELECTION.json注明未混入独立CuPy的两项。独立CPU用例见isolated_cpu_identity_v2.log。
- 原点分量：observation_inputs含81帧原CDR、1696定位、网格原点和固定查询集；observation_probe.cpp使用生产滚动栅格/LiDARModel，compile_observation_probe.py及命令JSON保留实际编译方式。先构建冻结源码，将源码路径替换到新目录，再运行probe。命令的offset=0或1分别生成独立新输出目录，拒绝覆盖。传入冻结tare_scout.yaml参数，localhost隔离ROS域，仅组件，无完整规划器/控制器。原始源时间不变。
- 传输：transport/run_formal.py在baseline/candidate冻结源码上交替3次，160帧/10Hz；样本来自HT_input_cause_audit_20261101/samples。run_probe.py限定localhost隔离ROS域；所有硬件/命令接口改名为诊断命名空间，不向实车播放录包。FakeTf/当前内存时间戳用于隔离传输，不是原TF回放。transport_instrumented额外2次默认、2次16MiB，仅补充，不能覆盖正式异常。
- 分量输出：observation_baseline、observation_candidate每帧float32[x,y,z,intensity]的_cells.bin和_frontier.bin、metrics.csv。GetVisualizationCloud中intensity0=occupied、1=free；这是该可视化API约定，不是内部滚动云API约定。
- 图表：observation_comparison.png、transport_comparison.png；cumulative_ray_free_volume.csv是射线自由体素并集，不是真值；recorded_wheel_travel.csv和recorded_task_events.json来自原记录。
- 视频：offline_origin_comparison.mp4，81实际组件帧，6fps，13.5秒，原始不均匀源时间逐帧标注，完整解码见VIDEO_CHECK.json。analyze_and_render.py首次因ffmpeg不在PATH而失败；render_video_v2.py使用现有imageio_ffmpeg二进制完成，不需新安装。

失败尝试全部保留。科学归档仅排除可再建的build/install/colcon中间件、Python/Numba缓存和原ZIP已有的重复MCAP；实际测试二进制、冻结源码、原始CDR、全部结果/日志不排除。完整归档文件逐项SHA在FULL_DATA_MANIFEST.json，原ZIP为另一个独立附件。发布是否完成须以PUBLICATION_RECEIPT/FINAL_REMOTE_CHECK为准。
