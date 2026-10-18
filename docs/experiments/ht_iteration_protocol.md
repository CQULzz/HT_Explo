# 每轮修改至少10分钟的验证约定

每一轮影响系统行为的候选修改都必须做完整600秒小测，保留失败结果。编译和回归期间的修正属于同一候选；未经完整小测，不标为已验证版本。文档、图表和只读分析不改变导航行为，但也须保留数据来源。

1. 说明本轮改动、预期效果和仍未解决的问题；完成针对性回归。
2. 提交代码，冻结运行源码、配置、权重和二进制。独立启动同一场景，起点、速度、建图和指标口径与对照一致。测试期间不调整参数。
3. 记录从首个具备激光和里程计的TARE运行周期起的600秒。提前BLOCKED仍继续记录；提前COMPLETED则注明停车原因。异常退出不计作完整600秒。
4. 保留原始MCAP（全部控制、位姿、状态、发布的HT图；激光按源秒采样）、10秒地图快照、有效参数、源文件/二进制哈希、资源监控、CSV与视频。这里不是全频原始激光或CuPy输入的无损录制。
5. 检查记录时长、节点退出、文件冻结和视频完整解码。记录完整与导航成功分别判断。
6. 用 presentations/compare_ht_iterations.py 比较同场景版本，画累计观测自由体积、里程、速度和实际轨迹；保留提交号、指标定义、状态和对照来源。

运行例：

```bash
python3 presentations/run_ht_multiscene.py --duration 600 --scenarios indoor \
  --domain 226 --encoder /path/to/ffmpeg --output /path/to/new_suite
python3 presentations/compare_ht_iterations.py \
  --run '上一版=/path/to/previous/indoor' \
  --run '本轮=/path/to/new_suite/indoor' --output /path/to/new_comparison
```

原始数据保存在运行目录，精选结果另行归档。每轮必须明确哪些数据已归档、哪些仅在本机，不把视频或汇总表当成全部原始数据。单次高体积也可能伴随最终卡死；不能据此称为稳定修复。
