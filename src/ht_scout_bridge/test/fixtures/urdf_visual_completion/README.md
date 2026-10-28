# 底盘视觉几何回归样本

这些样本只验证几何过滤，不启动 ROS、设备、仿真或导航。它们不能证明实车停车或低 HT 概率已经解决。

来源是用户指定的 `CQULzz/eletranskit_scout@cf0b73d7d01b4b6a2718c7ff3124f4b7a3368c36`：

- URDF：`src/ele_scout_kit/urdf/scout_sensor_rack.urdf.xacro`，Git blob `ec5bda24ffb53d8ecb9a97b2155dee0d1993a9c3`，SHA256 `f02ef732ada922d587b9e59810f83e382cbc313af4916271072f2d872b600e30`。
- 底盘视觉模型：`src/ele_scout_kit/meshes/base_link.dae`，Git blob `34799c4925eb67654b31421aad32629f1b4216a2`，SHA256 `002d8911888fb8fe52712dadd3499ae4995568c461c393aa17a859be0d8742b3`。

`base_visual_vertices.npz` 保存 DAE 五个 geometry 的原始 POSITION 数值，共 87098 个米制、Z_UP 顶点，以及旧过滤器的保留 mask。场景节点没有变换；URDF visual 没有 origin 或 scale。不是采样、缩放或从新配置生成的点。新五个盒子分别取各 geometry 的完整边界，再恰好增加一次 0.02m 裕量；此处 padding 已包含在边界里，运行时不能重复增加。

`old_scout_extrinsics.yaml` 从本仓库提交 `16f4b2f` 读取，SHA256 为 `bd3ca2a03461f83e0a17147c0fd16079c62cdae5d383b7ba769782fa4381b7fb`，保存独立对照，避免测试依赖相邻工作区或临时目录。它包含旧 9 个盒、4 个轮柱及外参；新增配置应保持这些值。

`geometry_test_samples.npz` 含 base Z=-0.23479m 平面上的 90601 个点、四个轮接地点和模型外 48 个近地障碍点。旧/新配置均保留 89581 个地面点，mask 应逐点相同。原有带裕量的轮柱已经与地面相交，所以这些测试要求新增几何不额外删地，不能声称全平面 100% 保留。48 个有限障碍样本也不能证明任意实景障碍都不会被误删。

`SOURCE.json` 记录源文件、分部边界及全部三个输入 fixture 的大小和 SHA256。完整 14MB DAE 不放入 Git；输入 NPZ 和旧配置足以独立运行回归。AABB 会覆盖网格的空角，顶点全部过滤不等于精确网格表面过滤或附件真值核验。

验证命令，在仓库根目录执行：

```bash
PYTHONPATH=src/ht_scout_bridge python3 -m pytest -q src/ht_scout_bridge/test/test_visual_geometry.py
```
