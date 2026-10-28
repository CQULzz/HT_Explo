# 复现（离线，不启动设备/仿真/控制）

GitHub实车分支：real/scout-helios32；代码发布提交见CODE_PUBLICATION.json；本机冻结HEAD见CANDIDATE_FREEZE.json。当前工作树有导入历史，不能把本机HEAD的完整祖先直接推向远端。仿真main/develop未修改。

环境：Ubuntu/ROS2 Jazzy，Python3.12，PyTorch2.11.0+cu128，NumPy1.26.4，CuPy，SciPy，Numba，Matplotlib3.6.3，imageio-ffmpeg；RTX5060Ti，TF32关闭。实际使用x86本机Python/CUDA推理，没有运行ARM二进制或实车控制器。

本机初始化：

```bash
source /opt/ros/jazzy/setup.bash
source '/home/lzz/my test/ht_cupy_gpu_ws_20261028/install_stable/setup.bash'
export PYTHONPATH='/home/lzz/my test/ht_cupy_gpu_ws_20261028/src/elevation_mapping_cupy_2204/elevation_mapping_cupy/script':${PYTHONPATH}
```

1. 从本轮Release下载三个ZIP并解压到同一个新目录；从real-scout-newbags-20261028恢复原始两份录包；从real-scout-filter-xy-trials-20261029恢复+20cm基线。RAW_SOURCE_ASSETS.json和BASELINE_SOURCE_INDEX.json给出引用与SHA。上一轮固定抽样的SAMPLES.json等也随audit ZIP提供。
2. 独立CuPy工作区保持独立，使用本轮代码的安装器：`python3 tools/install_elevation_fixes.py --workspace /path/to/independent --surface-registration`。只安装源码和试验配置，不启动节点。此选项会开启trial_core中的功能，原profile是否启用取决于最终合并参数。本机实验后已恢复原trial_core，见RESTORED_DEFAULT_CONFIG.json；不要据源码存在就推断已启用。
3. 使用新的空输出目录：

```bash
/home/lzz/.venvs/ht_real_gpu_20261028/bin/python \
  '/home/lzz/my test/HT_Explo-real-review-20261028/tools/ht_cupy_bridge/replay_newbags_rviz.py' \
  --bag '/path/to/unpacked/bag' --output '/path/to/fresh/output' \
  --cupy-package '/path/to/independent/src/elevation_mapping_cupy_2204/elevation_mapping_cupy' \
  --surface-registration
```

加`--self-filter-horizontal-padding-m .2`复算+20cm条件；省略`--surface-registration`复算原行为。完整五组命令见run_frozen_candidate.sh，其中路径需要对应解压位置、新输出目录。脚本拒绝覆盖现有输出；不要把已发布结果作为新输出路径。

4. 分析脚本analyze_frozen.py/plot_results.py中O从脚本位置取得，但R/B/P/STUDY是本机原路径，异机需改为对应解压位置。不要覆盖归档结果。冻结样本使用原640主样本+192条件对照，不能重新挑选成功案例。所需基线源路径清单见BASELINE_SOURCE_INDEX.json。
5. 对比视频用Matplotlib绘制实际保存的高程和HT字段；ffmpeg通过imageio_ffmpeg.get_ffmpeg_exe()取得。render_comparison.py生成100.5s前后对照，并完整解码验证。不是RViz录像。
6. CPU检查：`python -m pytest -q tools/test_install_elevation_fixes.py tools/elevation_mapping_fixes/test_surface_registration.py`。CUDA检查在本机先import torch，确保pip提供的CUDA动态库已加载，再运行pytest/verify_mapper_registration.py/verify_obstacle_controls.py。未加载时会报libnvrtc.so.12缺失；初次失败日志保留，不能视为算法测试通过。

冻结正式结果均未应用sigma门限、过程方差或时间偏移替代方案。这些诊断试验保留在独立目录；不得把其结果混入正式候选。原门限的新障碍接收迟滞尚未修复。没有ARM性能、完整实车总launch或闭环探索验收。
