# 离线性能实验复现

使用本轮固定tag源码和该Release全部`HT_performance_data.tar.zst.partNNN`分卷。先按发布回执验证每卷大小和SHA256，再在有足够空间的POSIX目录恢复：

```bash
cat HT_performance_data.tar.zst.part* | zstd -d | tar -xf -
```

分卷中保留已校验的3GB选题SQLite输入，无需再次解压原11.4GB数据库。完整原始ZIP仍在`RAW_SOURCE_ASSETS.json`引用的既有Release，不重复上传，也不删除本地未完成复现输入。

主要目录：

- `HT_release_validation_2026-10-30_02-04-25`：本轮六次逐扫描重建、完整地图/模型输入、统计、门槛及视频。`baseline_1/frames`作为逐帧比较基准；每次均643扫描、641输出、2帧缺精确TF。
- `HT_frequency_2026-10-30_01-01-19`：修改前HT源码、117帧组件对照及失败网络布局。
- `HT_input_pipeline_2026-10-30_01-36-43`：修改前输入桥接、641帧字节对照、并发/安装回归、失败CDR填充检查及完整候选源码。
- `HT_acceleration_options_2026-10-30_01-19-09`：CUDA Graph和失败ROI筛选，未并入生产路径。
- `HT_stationary_retest_2026-10-29_22-43-02`：原样22话题子集和输入CDR校验记录。

按照`EXPERIMENT_PLAN.json`把`source_bag`、`baseline_ht`、`baseline_scout`、`baseline_mapper`替换为恢复后的真实绝对路径，写到新的plan文件。**不要修改归档中的原计划、源码或结果，也不要复用旧输出目录。**

HT和CuPy必须保持独立构建。先source本机ROS、HT实车安装及独立CuPy安装；使用安装了CUDA PyTorch、CuPy、Numba、threadpoolctl的Python环境。实验工具不会启动executor、bag play、驱动或控制；严禁将含cmd_vel的输入全话题广播。

```bash
python tools/ht_cupy_bridge/validate_release_pipeline.py \
  --plan /new/path/plan.json --variant baseline --output /new/path/baseline_1
python tools/ht_cupy_bridge/validate_release_pipeline.py \
  --plan /new/path/plan.json --variant candidate --output /new/path/candidate_1 \
  --reference /new/path/baseline_1
```

按`baseline_1,candidate_1,baseline_2,candidate_2,baseline_3,candidate_3`顺序独立进程运行，后续均比较第一次基线。运行时源码/参数冻结；双方BLAS1线程，排除最初10个积分扫描统计，所有数据及其余慢帧保留。当前工具通过ament share解析CuPy权重；与实测脚本的机器路径回退使用相同字节的权重，`VALIDATOR_PORTABILITY_CHECK.json`保存核对结果。原始实测工具也以`validate_release_pipeline_frozen.py`保存，可在实验checkout的原工具位置核验重放。

验收门槛：六次输出均641，地图/输入/掩码/几何及0.5判定无差异，概率误差≤2e-5；中位处理耗时下降≥15%，每次配对≥10%，P95退步≤5%。不要改门槛来使失败实验过关。

这不是车上总launch复刻，drift/overlap/配准候选均关闭；录包车辆参考使用`scout_chassis_link`，不对现车TF做重新标定。不要将服务能力估计、压缩保存速度或约10Hz源时间进度写成实车发布频率。

原生ROS2当前车上诊断仍应分别测原始高程供图、适配器输入、HT发布、消息年龄、队列替换、CPU/GPU状态和实际启动入口；桌面结果不能替代ARM验收。
