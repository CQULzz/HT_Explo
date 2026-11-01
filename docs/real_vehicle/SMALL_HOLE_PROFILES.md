# 小孔填补强度

实车launch默认`small_hole_repair=true`、`ht_small_hole_profile=moderate`。通用节点/函数仍默认strict，实车和仿真配置保持分离。

|条件|strict（原版）|moderate（实车默认）|
|---|---:|---:|
|最近合格测量|≤0.12m|≤0.18m|
|总邻点数|≥12|≥8|
|四象限各自邻点数|≥2|≥1|
|平面RMS|≤6mm|≤10mm|

局部窗口半径仍0.16m（实际格数按地图分辨率取整），坡度≤0.35、测量年龄≤2s、方差≤0.25、当前/历史高度一致≤3cm、已知相邻跳变≤18mm及全部质量/障碍保护保持。仍要求四象限，禁止沿已填点迭代扩张，禁止写回测量历史或扩张支持掩码。原先通过的填补点和其预测高度保留；允许新增填补影响模型概率，0.5门限本身保持。缺少实测的坑不能靠插值证明安全，车底大片盲区中心仍会保留。

需要原来的强度时，在原实车launch参数中添加`ht_small_hole_profile:=strict`；不必改代码。显式关掉仍使用`small_hole_repair:=false`。运行诊断`small_hole_profile`、`small_holes.filled_cells`和`ht_interpolated`可识别实际配置和插值来源，插值不是直接观测。

CUDA上下文和1.5m固定30秒起点策略保持本轮之前的配置。参数选择必须记录进运行清单，部署后查看实际生效值；本轮只有x86离线验证，未在ARM或实车验收。


2026-11-01新增`ht_small_hole_fit_backend=auto/numpy/cuda`（同名实车launch参数）。auto在CUDA设备及4组精确启动自检通过后使用CUDA FP64窗口统计；CPU设备或初始化/自检失败用原CPU统计。numpy强制原统计、保留其他Numba优化；修补开启时显式cuda失败提前报错。候选、阈值、拟合求解、保护、四象限/距离与连通分量仍在原CPU路径，strict/moderate参数不改。网络仍为FP32。auto不按速度自动选择，ARM/GPU竞争需实测，见[报告与回退说明](../results/real_cuda_hole_fit_2026-11-01/REPORT.md)。
