# HT延迟与红区诊断（2026-10-31）

本轮保留模型、阈值和全部执行检查，仅减少小孔修复中的重复计算并增加诊断。实际效果与未完成项见[实验报告](../results/real_ht_latency_2026-10-31/REPORT.md)。HT与独立CuPy仍分别构建，不复制本机Numba缓存或x86二进制到ARM。

## 新增启动参数

标准`scout_real.launch.py`支持：

| 参数 | 默认 | 用途 |
|---|---|---|
| `ht_small_hole_backend` | `auto` | 可用时预热并使用Numba候选检查；`numpy`保留参考路径；`numba`要求编译成功 |
| `ht_profile_runtime` | `true` | 记录本进程CPU、上下文切换、页错误、GC与RSS峰值；不修改GC或硬件设置 |
| `ht_reason_interval_s` | `1.0` | 按单调墙钟抽样原因统计；0表示逐个成功输出采样，适合离线诊断 |

`auto`与`numba`共享同一个预热选择器，正式处理前完成编译。Numba不可用时，auto明确告警并回到参考路径；运行身份记录实际后端。12cm邻近、四象限、平面拟合、坡度/残差/边缘等全部原条件保持。

## 延迟与资源字段

`/ht_real/ht_performance`继续限速发布，并新增：

- `queue_wait_s`：本HT进程接收后在最新输入槽中的等待，使用单调时钟。直接调用回调时为null，不捏造排队时间。
- `input_queue`：接收、接受、取出、替换、乱序与退出丢弃计数。`receive_interval_s`是本节点收到消息的间隔，不是源节点发布间隔；`taken`是出队数，不等于成功输出数。
- `stages`：解码、源质量、历史融合、表面参考、历史窗口、最终质量、小孔、上下文、网络、原因计算和发布耗时。
- `runtime_profile`：当前回调的线程CPU/进程CPU、开始/结束CPU编号、进程内GC、页错误、上下文切换及Linux RSS峰值。跨线程GC可能计入，只是相关证据。
- `history_resources`：历史瓦片数量、上限和科学数组实际字节数，不包含整个进程、GPU、临时数组和Python对象；明确标记`eviction_enabled: false`。

超过100ms时尝试读取结束CPU的系统报告频率与累计节流计数。它是回调结束后的OS报告，不是完整频率轨迹，不能单独当作根因证明。无权限/不支持时为null；不读取任意环境变量、凭据或浏览器资料。

`source_age_at_publish_s`在主HT地图实际发布后立即采样；不会把之后的原因显示或资源记录时间混入该字段。逐帧记录还包含`post_publish_diagnostics_s`。实验的`direct_callback_s`包含完整回调开销，不因诊断移到发布后而排除它。

源消息年龄、进程内排队与处理服务时间有不同口径，不能直接相加再称为实际链路延迟。独立mapper、外部TF、规划与执行仍需各自诊断；本机离线结果不代表车上总链路或ARM性能。

历史容量不足会报告`HISTORY_CAPACITY_EXCEEDED`并拒绝本次更新；没有自动清空旧证据或把区域改成自由。正常的地图过期拒绝规则不变。历史换出、恢复及长期RSS治理尚未实现。

## 红区原因话题

独立`/ht_real/ht_reasons`为可选GridMap显示话题，仅有订阅且达到采样间隔时发布；直接脚本话题为`/ht_reasons`。它不接入规划许可，原HT地图层数与内容保持。

| 层 | 定义 |
|---|---|
| `reason_flags` | 下表原因位的组合；多种原因可以同时存在 |
| `raw_model_low_direction_bits` | 有上下文且原始网络分数低于0.5的方向位，方向k对应`1<<k` |
| `raw_model_min_probability` | 施加占据硬约束前的原始八方向最小值；上下文不足时保持NaN |

| 原因位 | 名称 | 含义 |
|---:|---|---|
| 1 | physical_unsupported | 既有物理支持层不成立 |
| 2 | context_unsupported | 网络感受野支持不足 |
| 4 | measured_occupied | 既有占据/保留拒绝高度层成立，不是物理类别真值 |
| 8 | model_low_with_context | 有上下文且至少一个方向原始分数低于0.5 |
| 16 | input_rejected_center | 中心输入被已有质量/历史选择规则拒绝 |
| 32 | interpolated_center | 中心模型输入来自已批准的局部插补，不是新观测 |
| 64 | model_nonfinite_with_context | 有上下文但某方向网络输出非有限值 |

物理支持层沿用已有25cm邻近支持定义，不等于该中心有直接激光回波。学习低分、缺支持和占据可以重叠；统计数之和可能超过格子数。原始网络高分也不会覆盖占据或未知的执行否决。

## 保存数据中的单格追溯

基准工具新增`--capture-reasons`保存诊断图；逐帧诊断可在离线设`ht_reason_interval_s:=0.0`，配合已有`--capture-context --save-frames`。默认实车抽样间隔仍为1秒。

使用同一帧的三份文件：

```bash
python tools/ht_cupy_bridge/inspect_ht_reason.py \
  --frame /new/run/frames/frame_0060.npz \
  --reason /new/run/reason_0060.npz \
  --context /new/run/context_0060.npz \
  --x WORLD_X --y WORLD_Y --direction 0 --output /new/query
```

工具核对源时间戳、几何和尺寸，使用与规划器相同的floor索引，输出原因JSON及未经修改的51×51模型输入窗口。它只适用于当前已检查的轴对齐HT图；方向参数是通道索引，不代替真实地形方向标定。不覆盖旧查询目录。

## 退出顺序

停止接收/取出新图并取消本节点定时器后，先等待已进入的计算和写盘结束，再销毁执行器的唤醒对象、保存历史并关闭节点。这样避免Jazzy退出时排队任务访问已销毁对象的竞态。该顺序仅作用于本节点，不终止其他进程。
