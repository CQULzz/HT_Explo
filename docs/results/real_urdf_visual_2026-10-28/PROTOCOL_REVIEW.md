# 下一候选的离线协议核查

2026-10-28。只读检查源码、配置和原 gzip 的首个 header；本核查未运行 raw 候选脚本、CuPy、HT、规划或设备，也未改生产文件。当前冻结 208 帧实验应先发布，再引入本候选。

## 已确认事实

- 实际读取原 `selected_raw_inputs.pkl.gz` header：`source_calibration` 与现有 9 盒配置逐值相同，包含 2077 条派生 base_link 位姿和 2077 条原 rslidar 里程计 CDR。静态 base_from_lidar 平移为 `[0.1725,0,0.5502]`、旋转为单位矩阵；不是根据图像猜测。
- 候选保留上述变换、原 9 盒和 4 轮柱。新 5 盒由原 DAE POSITION 数据逐部件计算，不是从截断终端输出抄边界。范围已包含一次 0.02m 裕量；当前 `geometry.py` 不再额外套 padding_m。
- `prepare_raw_candidate.py` 将原 `after`（9 盒）重算并逐位核对，然后写作新 `before`；新 `after` 为 14 盒。源 header 的 `source_calibration` 保持旧来源，两个实际变体配置在 `mask_variant_profiles` 中另记。现有独立 CuPy producer 只读点云、mask、R/t、源时间及 odometry，不会错误地再按旧 source_calibration 过滤。
- 该脚本保留原 raw_cdr、R/t、源/接收时间和全部 odometry 字节；输出 gzip 回读会再次检查非 mask 字段及两套 mask。固定 415 帧、额外删 1032 点是与先前审计一致性的验收条件，不是导航效果证据。
- `prepare_xytheta_replay.py` 可用 `--frame-stride 1 --heading-probe-stride 5` 生成 208 个记录起点×8 方位目标，加 43 帧×8 假设朝向诊断，加 3 个人工控制，共 2011 查询。主组保留记录车头；反事实组改变初始条件，不能混入实车导航成功率。

## 风险与不能据此声称的结论

1. **AABB 不等于精确实体表面。**五个盒有重叠，并覆盖部件之间的空角；87098 顶点全覆盖不证明所有被删点都是车体。最大新盒 Y 达约±0.293m，比原 chassis box 的±0.210m宽，底面低到-0.1362019m。模型外48个样本保留只是有限负控制；1032 个点没有逐点真值。
2. **地面验收应是“不新增删除”。**所有新盒最低 Z=-0.1362019m，高于假定平地-0.23479m约0.0986m，因此它们不会碰这个平面。原轮柱带2cm裕量已与平面相交；旧/新90601样本mask相同、均保留89581，不能宣称全平面100%保留。这个平地检查不覆盖真实俯仰、起伏或平台上的物体。
3. **1032 是审计复现，不是有利结果门槛。**如果数量不符应停止查输入/校准/顺序，不能改过滤边界来凑数；即使正好1032，HT或规划结果也可能无改善。
4. **原始mask计时固定先旧后新。**受缓存、分配和温度影响，只能作桌面预处理参考，不能认定 ARM 实时性提升。gzip字节SHA也会受gzip时间头影响；跨次语义复现看原CDR/不可变字段与mask哈希。
5. **CuPy/GPU的原子融合可能有数值非确定性。**应比较本次9盒基线与上轮9盒输出：时间、几何、位姿完全相同；记录有效掩码差异、有限高程最大误差、HT硬门槛翻转数。如基线存在显著漂移，应补同配置重复控制，不能把全部差值都归因于五盒。
6. **新增过滤不保证停车解决。**未知、真实障碍、低T仍按原规则拒绝。禁止修改模型权重、0.5门槛、0.6m物理支撑范围、严格未知规则、起步先验、朝向映射来制造路径。

## 规划比较必须重新配对

本候选是输入过滤变化，不是上一轮“新旧gate代码”变化。两组必须使用**同一份已修复的实际C++二进制**（运行源 a33f78a，GitHub 59179d2 对应者），二进制SHA256相同；分别输入本轮9盒/14盒HT图。

不能直接复用 `docs/results/real_xytheta_full208_2026-10-28/run.py` 的比较语义：它将同一批地图送进旧gate与新gate两个二进制，并要求地图哈希相同，适合上轮方向修复，不适合本轮地图输入变化。不能把旧bug二进制放在本轮before一侧，也不能让PADDING复用工具覆盖真正不同的before/after地形值。

两组按原始map stamp配对208帧，记录相同的(x,y,θ)、目标、参数和排序，允许且预期地图值/哈希不同。成功图少于208或某侧缺帧就应报告失败/不完整，不能只选输出成功的子集。3个人工控制应字段逐位相同，序列化padding差异单独审计，不能只依据CDR SHA判断地形改变。成功路线再次逐段检查硬约束。

统计208个独立记录起点和1664个主组查询，反事实344查询单列。起点INVALID_START的微秒耗时不是A*搜索性能。冻结源图时钟不能验证实时新鲜度、网络、跟踪器、TARE选点或实车运动。

## 建议执行顺序与命令（尚未在本核查中执行）

先设置变量，所有结果用全新目录；`task_old_profile`必须指向已发布9盒配置的精确快照。`task_mapper_package`指向已经验证patch的独立CuPy包目录。

```bash
task_repo='/home/lzz/my test/HT_Explo-real-review-20261028'
task_candidate='/tmp/ht_urdf_visual_candidate_20261028'
task_source='/home/lzz/my test/HT_Explo-real-round2-20261028/raw_rebuild_inputs/selected_raw_inputs.pkl.gz'
# 设置 task_old_profile、task_result、task_archive、task_mapper_package；避免旧结果目录。
source "$task_repo/scripts/source_real_scout.sh"
export ROS_DOMAIN_ID=181 ROS_LOCALHOST_ONLY=1 RMW_IMPLEMENTATION=rmw_fastrtps_cpp
python3 "$task_candidate/prepare_raw_candidate.py" \
  --repo "$task_repo" --source "$task_source" \
  --old-profile "$task_old_profile" \
  --new-profile "$task_candidate/candidate_scout_extrinsics.yaml" \
  --output "$task_result/raw_inputs"
```

验收 INDEX：415帧、2077+2077条odom、所有旧mask精确一致、所有new为old子集、1032额外候选点；原始数据不被覆盖。再在已验证CUDA/CuPy环境中：

```bash
/home/lzz/.venvs/ht_real_gpu_20261028/bin/python \
  "$task_repo/docs/results/real_round2_2026-10-28/rebuild_cupy_maps.py" \
  --input "$task_result/raw_inputs/selected_raw_inputs.pkl.gz" \
  --package-dir "$task_mapper_package" --output "$task_result/cupy"
```

两侧应各208张291×291、0.04m、真实observation_age地图，原始时间一致。保持既有CUDA库与独立CuPy的PYTHONPATH环境。对before/after分别运行相同冻结HT代码：

```bash
for task_variant in before after; do
  /home/lzz/.venvs/ht_real_gpu_20261028/bin/python \
    "$task_repo/docs/results/real_round2_2026-10-28/experiment.py" \
    --stage ht --archive "$task_archive" --device cuda --quality-backend numba \
    --input "$task_result/cupy/${task_variant}_native_maps.pkl" \
    --output "$task_result/ht_$task_variant" --commit "$task_frozen_runtime_commit"
  python3 "$task_repo/tools/ht_cupy_bridge/prepare_xytheta_replay.py" \
    --maps "$task_result/ht_$task_variant/maps" \
    --frame-stride 1 --heading-probe-stride 5 \
    --output "$task_result/queries_$task_variant"
  "$task_fixed_cpp_binary" --batch "$task_result/queries_$task_variant/queries.tsv" \
    --output "$task_result/plan_$task_variant.json"
done
```

`task_frozen_runtime_commit`只是显式版本标识，仍要核对实际源码/模型/依赖/参数与二进制哈希，不能用字符串替代证据。两次Cpp执行之间复核 `sha256sum "$task_fixed_cpp_binary"` 不变。最终报告同时展示改善、不变和退步，并上传原输入、完整负结果、图表与视频；这些都不构成ARM实车闭环验收。
