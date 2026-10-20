# 室内提前完成：只读根因核对

证据目录：`docs/fixes/evidence/2026-10-21_indoor_ht_gate/`。没有修改源码、配置、提交或启动仿真。
原始记录：`presentations/scheduled_results/ht_tare_native_5scene_10min_2026-10-20_19-39-37/indoor/`。

## 事实

- 测量起点1792497880.2039096。日志1792497893.887463489，即测量13.683554s，首次 `global_return=1 local_complete=1`；仍有uncovered=102/frontier=0，但这单独不足以证明原TARE完成判定错误。该帧原TARE `selected=3 route_nodes=27 route_length=7.813 complete=1`，立即输出“Exploration completed, returning home”。随后路径目标改成home(0,0)。录包mission_state在28.471620s变为COMPLETED。
- t12.688846s实际candidate=509，其中未访问267、原编码收益>=40的211、远端Y到14.85m；t13.684660s骤降到283，其中未访问41、收益>=40的0、Y到4.95m。`viewpoint_vis_cloud`的非负intensity编码为coverage_count + array_index/10000；visited=-1。本分析未将小数部分当真实收益。
- t12.689和t13.685候选并集516个。按照源码实际8邻域(.3m)/高度差<.25m连接，无HT删除时连通516；仅删除HT粗.2m历史中拒绝的12个顶点后连通283，与下一周期实际候选逐点完全相同：0 missing/0 extra。并集中没有点被当前物理collision_vp标碰撞。
- 12个顶点位于x2.25..3.75,y5.25..5.85。最新接收map在t13.511986s，源时间1792497893.335921。12点均ht_valid=1、ht_observation_valid=1、ht_obstacle=0，8方向最大prob在.130..319；粗.2m格内各有效细胞最大值也都低于.5。5个y5.55点ht_elevation为NaN。门禁来自低模型概率，不是unknown或物理obstacle mask。
- 实际sim模型`autonomous_exploration_development_environment/src/vehicle_simulator/mesh/indoor/meshes/indoor.dae`为米、Z_UP、模型identity变换。模型bounds x[-2.052,127.632],y[-29.174,70.11],z[-.1058432,3.794157]，不是小房间。y5.25/5.55/5.85/7/10在z.2/.4/.75/1.0横截面均给出内墙面x1.647968和4.447968，净宽2.8m；本轮ht_validity_radius=.6m。x2.25..3.75,y4.5..6.5的30条mesh vertical probes均只有地面底-.1058432/顶-.0058432，没有台阶。摄像头也显示连续平整走廊。这是离线真值证据，不是在线安全放行依据，也不是完整车辆扫掠证明。
- 同一(3.15,5.55)点粗格maxprob在t11.531~.999，t12.503~.781，t13.512~.218，t19.535~.584；t19.562s候选恢复521，但exploration_finished已经锁存、覆盖不再更新。这不是持续不存在目标的证据，而是先前HT连接切断后完成状态不再重新评估。
- 当前参数kUseFrontier=true、kMinAddPointNumSmall=40、Big=60、Frontier=20、kSensorRange=7.5，与ROS2 baseline indoor.yaml一致。视点分辨率为.3m/100x100；baseline是.6m/50x50，范围同30x30m。HT模式不论kUseTerrainHeight=false仍用HT历史高程设置视点高度，但观察到此次相关视点Z仅.705..767，不能解释.25m高度阈值的断连。

## 已核对源码链路

`src/tare_planner/src/viewpoint_manager/viewpoint_manager.cpp`:
RefreshHTTerrainMask -> HtCostMap::terrainAdmissible -> CheckViewPointConnectivity移除HT不许的顶点 -> GetViewPointCandidate。
`src/tare_planner/src/ht_cost/ht_cost_map.cpp`:
.2m粗格按观测/评分有效细胞聚合，8方向任一prob>=.5可行；当前消息覆盖旧feasible，未知历史格默认允许。
原TARE本体`src/tare_planner/src/local_coverage_planner/tare_original.cpp`:
无足够增益queue、无reused/frontier选点时local_complete=true。
主Execute里global_return && local_complete && >5s锁存exploration_finished；在kNoExplorationReturnHome时随后不再更新覆盖，只导航回家。

## 推测 / 待确认

- 因果链已被反事实BFS充分解释：HT平地连接处低概率 -> 远端高收益候选分量被移除 -> 原TARE只见低收益本地分量 -> 完成返航。没有证据证明应修改原TSP或六个原函数。
- 低概率更上游的直接原因仍需模型输入消融。保存context每10s一张，触发源时间1792497893.335921的完整context没有落盘。不能把后续1792497898.3409157当触发同帧输入。
- 后续context在(3.15,5.55)的51x51 RF中0 occupied/0 rejected，filled高程[-.0472,.0346]m，raw/observed比例.712，梯度m/m的P99=.910/max1.965，输出maxprob=.3305。平地厘米噪声加最近邻缺失填补产生高频梯度，是需要验证的方向。邻点(2.85,5.55)observed比例.699、maxprob=.327。
- ht_observation_valid与NaN高程并不必然数据损坏；源码prepare_ht_context把离known<=.25m视为physical support，ht_elevation发布未填补高度。负责模型输入诊断的代理正在核对该语义。
- 原始目录有FAILURE.json且没有summary.json，录包metadata实际duration596.217s含初始化，结束相对测量起点约569.83s。不要把该目录声称600s已验收；最终捕获/发布状态由父代理核对。

## 最小修复建议

1. 先对真实记录输入做可重复模型消融，判断降噪/填补方式是否导致误拒，保持物理obstacle与拒绝点不被平滑抹掉。真值mesh只供离线验证。
2. 若确认是建图/输入噪声，修高程到HT输入层，保留原TARE六函数、阈值/TSP访问顺序及HT硬门禁。
3. 不以降低.5阈值、延长任意完成计时、无条件跨过红区解决。单纯把NaN改unknown可能只会更早断连，不能声称解决。
4. 加只读逐周期候选/HT拒绝/连通分量/门点统计与完整触发context留存，便于复测严格验收。

## 复现与边界

在仓库根目录运行 `python3 docs/fixes/evidence/2026-10-21_indoor_ht_gate/reproduce_counterfactual.py` 重算516→283逐点匹配。该命令只使用约50KB的必要fixture，不读MCAP、不加载网络、不启动仿真。`probe_mesh.py` 可从实际sim模型重新计算截面/地面，不要在冻结测量期间运行重分析。

完整触发时刻模型输入未保存；最后接收HT输出已单独保留为last_precompletion_map.npz。不能把输出地图当完整291×291神经输入。未修改或修好室内在线算法。

## 文件

- candidate_cycles.json：实际候选数/高度/收益与mission转换。
- terrain_rejection_compare.json：丢失候选中HT直接拒绝/仍允许数量。
- counterfactual_bfs.json：516 -> 删除12 -> 283的逐点对齐证明。
- gate_point_probabilities.json：各接收时刻的12点8prob/高程/valid/obs/obstacle/粗格最大概率。
- mesh_ground_probe.json、mesh_section_z*.npy：真值地面/墙面几何。
- inference_patch_statistics.json：邻近完整context输入实际统计，非触发同帧。
- indoor_completion_evidence.png/.pdf：真实墙线/候选骤减/HT红带/切断分量对照。
