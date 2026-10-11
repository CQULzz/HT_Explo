# Campus HT 长测记录工具

这些脚本用于记录运行中的 ROS 2 话题并画图。仿真器、CuPy 建图节点和桥接节点在各自独立的工作空间启动；这里不复制它们的源码。

在已 source ROS 2 环境、仿真和 HT/TARE 都运行的终端中：

```bash
python3 validation/campus_long_run/long_run_diagnostics.py --output validation/results/new_run --duration 900
python3 validation/campus_long_run/path_stutter_probe.py --output validation/results/new_run/path_stutter.csv --duration 300 --wait-healthy
python3 validation/campus_long_run/plot_long_run.py --run validation/results/new_run
```

`long_run_diagnostics.py` 写出地图年龄、里程计、速度指令和状态的 `timing.csv`、`summary.json`。`path_stutter_probe.py` 记录 CMU `/path` 长度与底层速度。绘图脚本需要 `matplotlib` 和 `numpy`。

2026-10-11 的记录、图和视频见 [测试报告](../results/HT_long_run_report_2026-10-11.md)。
