# 复现

复用已核验的native_stream.pkl和stationary_required_topics.db3，不重复解压。source scripts/source_real_scout.sh，仅加载实车install_real；独立CuPy工作区保持独立。使用原GPU Python环境。

run_validation.py在全新输出目录使用baseline/candidate冻结源码交替三轮，每轮117帧，实际命令、逐帧诊断、输入窗口和全部14层在完整数据归档中。显式后端可用 --parameter ht_context_backend:=cuda；numpy为旧参考路径。模型保持CUDA FP32。

构建：bash scripts/build_real_scout.sh。回归：对tools/ht_cupy_bridge/test_*.py和src/ht_scout_bridge/test/test_*.py显式选取，排除依赖独立CuPy节点的test_cupy_tf_worker_ros.py和test_publication_demand.py；再运行ctest --test-dir build_real/tare_planner --output-on-failure。各进程使用独立本地ROS_DOMAIN_ID。

启动查询辅助程序的原样源码、编译/链接参数及哈希在FIXTURE_V2_BUILD_COMMANDS.json。run_startup_fixture_v2.py使用首帧原样数值生成CDR，查询disabled/unknown/fixed三模式；完整结果声明其覆盖参数。V1辅助程序仅比较关闭/固定先验，保留但不当作原策略对照。整个流程不运行驱动或底盘。
