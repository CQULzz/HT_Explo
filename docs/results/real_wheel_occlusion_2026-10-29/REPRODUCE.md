# 复现与部署范围

代码位于real/scout-helios32；本轮源码提交映射见CODE_PUBLICATION.json，本机冻结HEAD见CANDIDATE_FREEZE.json。独立CuPy工作区仍独立，未使用相邻HT工作区。

本机x86 / ROS2 Jazzy / Python3.12 / NumPy1.26.4 / SciPy / PyTorch2.11.0+cu128 / CuPy / RTX5060Ti。推理关闭TF32。本轮没有执行ARM二进制、仿真或控制器。本机install_real验证了安装内容，但不应把这些x86构建产物直接复制到ARM；在目标机从源码构建。

1. 下载本轮三个Release ZIP并解压到同一新目录。原始两段ZIP从real-scout-newbags-20261028恢复；未配准基线也在那里。已配准基线在real-scout-surface-registration-20261029的frozen_replays ZIP。BASELINE_SOURCE_INDEX.json给出逐文件SHA，RAW_SOURCE_ASSETS.json给出原输入附件SHA。
2. source `/opt/ros/jazzy/setup.bash` 和自己的独立CuPy `install_stable/local_setup.bash`，使用本机GPU Python环境。PYTHONPATH包含独立CuPy的`elevation_mapping_cupy/script`。本机完整命令见run_frozen.sh；复制到新输出目录运行，脚本拒绝覆盖旧结果。
3. 默认车体过滤已在scout_extrinsics.yaml启用，不需要额外20cm膨胀。记录重放：

```bash
python tools/ht_cupy_bridge/replay_newbags_rviz.py \
  --bag /path/to/raw/bag --output /path/to/fresh/output \
  --cupy-package /path/to/independent/elevation_mapping_cupy
```

加`--surface-registration`单独启用上一轮配准候选，去掉该参数可验证本轮默认过滤独立效果。加`--calibration-file /path/to/baseline_scout_extrinsics.yaml`可精确恢复旧过滤；不能覆盖已发布目录。两个功能不是同一开关。

4. 几何回归：source ROS后把本工作树`src/ht_scout_bridge`加入PYTHONPATH，运行：

```bash
python -m pytest -q src/ht_scout_bridge/test/test_geometry.py \
  src/ht_scout_bridge/test/test_visual_geometry.py \
  src/ht_scout_bridge/test/test_wheel_occlusion.py \
  src/ht_scout_bridge/test/test_horizontal_padding.py
```

本轮46项通过。构建命令为`colcon build --base-paths src/ht_scout_bridge --build-base build_real --install-base install_real --packages-select ht_scout_bridge`。INSTALLED_DEFAULT_VERIFY.json包含源码/安装目录一致性SHA。

5. `audit_points.py`保存全部1001帧点云原始顺序的旧/新压位掩码。POINT_MASKS.npz的bitorder=big，按source_point_count截取解包。该脚本不使用世界TF，缺TF的原始扫描也可审计；地图重放仍按原规则跳过缺TF扫描。
6. `analyze_formal.py`读取4个候选与历史基线。O由脚本目录确定，R/B/L为本机绝对路径，异机请对应恢复。`plot_and_video.py`生成6页对照图和36s放大视频，`append_rviz.py`附第7页实际RViz截图。图中车体坐标旋转只用于显示。
7. 实际RViz录制入口`record_rviz.py`只在自建Xephyr :98和私有ROS域188中显示MarkerArray，退出关闭自己启动的4个RViz和Xephyr。需要真实的已记录输出，不会启动设备或车辆。视频已完整H264解码验证。对比视频是Matplotlib绘图，二者标注不同。

未验证实车闭环、真实孤立小物体、复杂坡面和ARM时延。静止包中心未知、末段残余低分及旧融合的新障碍接收迟滞没有在本轮修复。实际更新后应重新启动输入/建图/HT链并从干净历史核验；不要把旧污染地图的遗留红块误当成新过滤没有生效，也不要把未知涂成可通行。
