# 复现说明

本轮是已发布实车录包的离线诊断，生产代码没有修改。依赖ROS2 Jazzy、Python3.12、NumPy、SciPy、PyTorch/CuPy GPU环境；本机Python为/home/lzz/.venvs/ht_real_gpu_20261028/bin/python，独立CuPy安装为ht_cupy_gpu_ws_20261028/install_stable。

1. 原始录包按RAW_SOURCE_ASSETS.json从real-scout-newbags-20261028恢复；上一轮已发布输出位于real-scout-wide-replay-20261029。本轮完整ZIP保存重建、输入上下文、原始回波追踪、全部尝试和图表。
2. run_contexts.sh是实际命令；必须改成新O输出和新的本机POSIX context目录后运行，不能覆盖当前记录。外盘不支持os.link，不能直接作为HT_CONTEXT_DUMP目录；capture_all_contexts.py只延长诊断捕获时窗，不改变模型或地图。
3. verify_and_copy_contexts.py逐元素核对181帧地图/HT并复制输入上下文到外盘，逐文件SHA256核对。更换其L/B/O路径为恢复位置。
4. scan_residuals.py统计完整181帧；trace_raw_points.py回查源回波与源时间TF；trace_map_cells.py追踪同一世界格的模型高度。读取本轮已有文件可跳过重新重建。
5. probe_inputs.py执行6个查询的模型输入干预。使用归档context_*目录时，将L/case文件路径指向恢复的context_moving或context_stationary；其余R模型源码/权重路径按本机恢复。single_cell_fullmap.py独立执行只改1像素的整图对照，保持原占据格强制0规则。
6. plot_audit.py生成6页核心图；append_figures.py增加2页，需全新figures输出目录，不覆盖。所有图仅为诊断，不用于规划。

初版失败/图形修正保存在attempt*，不得当作最终证据。首版全高程拟合的倾斜平面、首版遗漏占据强制0的整图比对均已纠正；最终原始输出核验通过。两段录包均无图像或camera话题，CAMERA_TOPIC_CHECK.json记录检查结果，不能凭模型干预判定真实通行或异常反射的物理成因。
