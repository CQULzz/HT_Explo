# 室内稀疏高程纹理：候选修正与验证边界

## 原因证据

室内旧批次12个已观测但HT八方向均低分的点切断候选连通图；原TARE因此返航并结束。真实走廊净宽2.8m，未找到对应台阶。详见[原因审计](2026-10-21_indoor_ht_gate.md)。准确触发时刻13.512s没有完整输入，不能假称已复现它。

后续18.137s的完整输入可以数值重放。旧滤波仅允许3×3全观测邻域，孔边厘米纹理处理不足；模型对这些纹理敏感。此为可验证的输入敏感性证据，模型原始训练噪声分布仍待确认。

## 修改

- `tools/ht_cupy_bridge/elevation_quality.py`：3×3邻域至少包含两对互为对称的真实观测邻居时，允许有限滤波；每个参与邻居必须有对侧观测，避免单侧缺测将斜坡拉平。NaN不转成观测，仍使用既有方差权重和每格至多2cm调整。
- 保留7.5cm大跳变保护；增加相邻一侧与中心相差不超过5mm、对侧跳变至少15mm的连贯特征保护。回归覆盖1.5/3/7.5cm台阶、两格窄柱、低方差单格凸点、坡面、孔洞和单侧支持。低置信且孤立的厘米极值仍遵循既有有限滤波策略；单靠高程与方差不能保证区分所有真实细物体和噪声。
- `cupy_to_ht.py`、`inference_context_io.py`：启动和首次TARE运行各45s逐帧保留完整推理上下文，之后每10s；增加原始高程、方差、观测年龄、几何及历史方差，以便下一次早停保留准确触发输入。只在启用诊断输出时订阅运行信号。原有每秒传感器/周期地图录制不冒称全频无损。
- 后处理比较图从冻结job获取当前阶段名称，阶段44不再误标成42；保留阶段42重复实验与43作为独立车库历史记录。

不改模型权重、米制输入、梯度归一化、0.5通行门槛、原TARE六函数/TSP/完成判据、控制速度或几何/动力学检查。

## 已执行验证

证据目录：`docs/fixes/evidence/2026-10-21_sparse_height/`。

ROS及CuPy环境加载后69项桥接回归通过，新增源数据录制检查通过；六项原TARE函数SHA契约通过。最初未加载CuPy工作区造成测试导入失败，原始日志保留，不能把环境失败隐藏或当算法错误。

离线重放同一个后续保存输入，基线输出最大误差3.28e-7。两处平地最大分数约0.327→0.607、0.331→0.595；后者正北方向仍约0.436，另有位置最大分数仍低于0.5。观测、拒绝、物理支持、障碍和模型支持掩码不变。局部分数上升不代表整条车辆路径可走，也不是准确触发帧的证明。

复现：

```bash
source /opt/ros/jazzy/setup.bash
source '/home/lzz/my test/elevation_mapping_cupy_ws/install/local_setup.bash'
OPENBLAS_NUM_THREADS=1 python3 -m unittest discover -s tools/ht_cupy_bridge -p 'test_*.py'
python3 scripts/check_tare_waypoint_contract.py
OPENBLAS_NUM_THREADS=1 python3 presentations/audit_sparse_height_input.py \
  --context docs/fixes/evidence/2026-10-21_sparse_height/later_frame_context.npz \
  --output /tmp/ht-sparse-replay-new
```

输出目录必须不存在。闭环验收按[预先计划](../plans/2026-10-21_sparse_height_denoising_plan.md)进行室内、车库、森林、隧道各600s；该文档建立时尚未新闭环，不能声称提前结束问题已修好。实测冻结提交、结果和剩余问题以后续独立报告/发布回执为准。
