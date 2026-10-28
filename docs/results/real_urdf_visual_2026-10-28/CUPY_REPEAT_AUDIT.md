# CuPy 同输入重复不一致审计（只读）

日期：2026-10-28，Asia/Shanghai。仅阅读源码、已存在参数/输入检查和原生GridMap输出；未运行新的CuPy/HT重建、仿真、硬件或电机，也未修改生产源码。以下JSON均是对既有输出的CPU逐数组比较，不以pickle/CDR文件哈希代替语义比较。

## 结论与界限

**事实：不一致首先发生在原生CuPy高程/方差/观测年龄，HT之前；不只是最终HT浮点概率微差。实际启用的CUDA点融合内核存在共享状态读写竞争，因而没有“相同点列表必得相同地图”的保证。** 该竞争机制由源码直接可见；已完成的同进程、同9盒、同扫描负控制也出现明显高程与接受观测年龄分歧。不能把本轮9盒→视觉几何新增的全部差异解释为几何改进。

**推测/尚未量化：** 各类竞争各贡献了多少个1m级高度差、以及是否还叠加其他CUDA/CuPy/PyTorch数值因素。没有记录逐线程调度或每个kernel中间状态，故不能把某个具体单元差异唯一归因到某一行。

## 直接原生输出证据

旧9盒：`/home/lzz/my test/HT_Explo-real-round2-20261028/cupy_rebuild/after_native_maps.pkl`。
新9盒：`/media/lzz/My Passport/HT_Explo_urdf_visual_candidate_2026-10-28/run_data/cupy_rebuild/before_native_maps.pkl`。
两侧208张原生GridMap，逐层数值比较：

| 帧 | source stamp ns | elevation最大差/m | variance最大差/m² | observation_age差异单元/最大差s |
|---|---|---:|---:|---|
| 0 | 1791730211723889589 | 2.3841858e-7 | 7.4505806e-9 | 0 / 0 |
| 1（第三个输入扫描） | 1791730212820775509 | 0.15938181 | 0.32015705 | 8 / 1.09688592 |
| 2 | 1791730213720233440 | 0.44972107 | 0.29926625 | 6 / 1.99634385 |

原生观测年龄由直接接收的观测决定，源码 `elevation_mapping.py:382–390` 仅在 `new_map[2]>0 && map_valid>.5` 时更新source stamp。因此帧1年龄不同是接受观测路径已经不同的证据；不是仅在序列化字节、HT卷积输出或通道排列上的差别。

更强的既有负控制：`run_data/same_filter_control/CONTROL.json` 声明415扫描两侧mask每帧完全一致，两个独立CuPy实例同在一个固定顺序循环中。只读比较其已完成的 `cupy/{before,after}_native_maps.pkl`：

- 帧0：高程650单元数值不同，最大2.3841858e-7m；年龄完全一致。
- 帧1：高程最大0.13672793m；方差最大0.21001808m²；年龄12单元不同，最大1.09688592s。
- 全208帧：高程差异659847个逐帧单元、NaN位置差3614，最大1.56186998m；方差最大差9.99968529m²；年龄差异8680个逐帧单元，最大26.49948311s。

逐帧证据见本目录 `CUPY_NATIVE_REPEAT.json` 和 `CUPY_SAME_INPUT_NATIVE_CONTROL.json`。这些是累计逐帧计数，不是唯一世界格数量。

## 实际执行顺序与初始化检查

使用脚本：`/home/lzz/my test/HT_Explo-real-review-20261028/docs/results/real_round2_2026-10-28/rebuild_cupy_maps.py`。

- 第24–35行依次为before/after构造新的 `Parameter` 和 `ElevationMap`，没有加载历史地图或缓存状态。
- 第39–49行用pickle顺序读取扫描，NumPy布尔mask切片保留原始点顺序，依次 `move_to → update_time/update_variance → input_pointcloud`。时间增量来自source stamp差值，不是处理耗时。
- 第50–55行每两个扫描发布，且每个变体末尾显式同步当前CUDA stream。脚本本身没有ROS订阅队列、异步计时器或并行扫描顺序。
- `elevation_mapping.py:62–90`：中心/旋转固定初始化；地图和normal buffer为zeros，观测stamp为NaN；方差设置同一initial_variance。第243–251行临时数组同样为zeros。
- 两次参数差异只有plugin文件路径字符串，文件字节相同，内容仅 `min_filter: enable: false`。`plugin_manager.py:139–150` 仅加载enable=true条目，本次没有启用随机插件。
- 实际参数 `enable_visibility_cleanup=true`、`enable_edge_sharpen=true`、`enable_drift_compensation=false`、`enable_overlap_clearance=false`。漂移补偿/重叠清理不是此次启用的处理分支。
- 主融合/重建路径未发现随机采样；文件末尾测试用random语句位于 `if __name__ == '__main__'`，不能据搜索命中就说生产随机采样。没有证据支持“设seed就能解决”。

## 源码中可核对的竞争机制

源码根目录（下述行号均指此目录）：
`/home/lzz/my test/ht_cupy_gpu_ws_20261028/src/elevation_mapping_cupy_2204/elevation_mapping_cupy/script/elevation_mapping_cupy/`

1. **共享方差参与实时接收/拒绝分支。** `kernels/custom_kernels.py:144–146` 建立逐点ElementwiseKernel；第170–174行点线程读取 `map_h/map_v`，按 `abs(map_h-z)>map_v*threshold` 判定离群后atomicAdd共享map方差。另一个线程可以在该加法之前或之后读同一map_v，从而对本帧相同高度差作出不同判定。第181–185行卡尔曼候选计算也使用读到的map_v，原子加到newmap。这里不止浮点求和顺序问题，接收集合和滤波权重本身可能变化。
2. **本帧点融合和本帧射线清理共用可变地图。** 第187–192行直接写valid/time/upper_bound；第198–255行每条射线读取相同map的高度、方差、valid、最近更新时间，按分支原子减valid/加方差，并非原子地写upper_bound。不同点/射线线程可以交错影响彼此。第229–255行upper_bound的“读旧值→比较→普通写”也没有全局最小值原子归约保证。
3. **浮点原子归约本身顺序未固定。** 第183–185行归约候选高度/方差/计数，第375–377行再除以计数；即使接收集合不变，也可能产生首帧观察到的1e-7级差异。后续第173/177/239等离散分支可能放大微小差异；本审计未测出各机制贡献比例。
4. **主机锁不解决点线程竞争。** `elevation_mapping.py:339–381` 在Python map_lock内启动error_counting、add_points和average kernels；它可以隔离主机调用，却不会为同一个add_points kernel中的点线程规定执行顺序。

CUDA kernel源码 SHA256：`b2b34821f8c605af872c355665f729915b2aaf9c5d9c0c6720a54cc841ee064c`。
核心Python SHA256：`4339f73035bfed02d9855b97792cb8b4f5d106a09beac6e679740bb8cd44d6ad`。
全部审阅文件与hash见 `CUPY_REPEAT_SOURCES.json`；本轮FREEZE.json也记录相同两项hash。

## 不该在本轮做的归因与修改

- 不把9盒负控制波动当作新增视觉几何的提升或退步；先发布候选及负控制，明确混淆。
- 不靠多加一次Python lock、设随机种子或放宽HT概率阈值掩盖共享状态竞争。
- 不直接在当前候选里关闭射线清理或修改融合数学；这会改变地图行为，应作为另一个冻结候选和独立测试。
- 不声称float atomic竞争单独解释了所有1.56m差异；当前只有机制证据和观测分叉证据，没有逐kernel消融归因。

## 下一轮可验证控制方案（未在本任务执行）

1. 保持同415扫描、同9盒mask、同逐点顺序、同source timestamps/poses、同参数/源码/权重/环境，分别启动全新实例，至少3组同输入控制；每扫描保存CPU可读的各状态层，不只隔帧最终输出。已有同进程负控制是第一组证据，不能用一组确认普遍差异范围。
2. 记录每次add_points前后及average后的map、新接受计数、outlier计数、visibility撤销量、observation stamps。找首个接收集合分歧，区分“浮点求和误差”与“读写分支分歧”。诊断同步单列开销，不混入生产性能数字。
3. 在独立实验分支比较基于不可变旧图的分阶段处理：先固定每点接收/卡尔曼候选，再按cell稳定归约，射线清理决策基于固定快照并独立归约，最后统一提交valid/variance/upper_bound。upper_bound用明确定义的min/priority归约，避免最后写者获胜。是否保持现有数学语义须单独设计，不能称简单排序就完全修好。
4. 验收先比较原生地图，再相同HT推理和同一规划器。至少报告高程/方差/年龄/valid/NaN差异、HT硬阈值翻转、规划成功数的控制波动区间。确定性目标/容差必须提前明确；“两次看起来差不多”不足以验收。
