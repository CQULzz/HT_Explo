# 复现说明

从本轮Release解压完整科学数据到新目录。原117帧`native_stream.pkl`和22话题SQLite输入在`RAW_SOURCE_ASSETS.json`引用的旧完整数据附件中；优先复用已下载并校验的输入，勿再解压或覆盖旧结果。

HT只source ROS与本工作区`install_real`，独立CuPy保持独立。使用已有CUDA PyTorch/Numba环境。新输出目录必须不存在。

```bash
python tools/ht_cupy_bridge/benchmark_ht_stream.py \
  --stream /verified/native_stream.pkl --bag /verified/stationary_required_topics.db3 \
  --module-dir /frozen/baseline/tools/ht_cupy_bridge --device cuda \
  --capture-context --save-frames --output /new/baseline_1

python tools/ht_cupy_bridge/benchmark_ht_stream.py \
  --stream /verified/native_stream.pkl --bag /verified/stationary_required_topics.db3 \
  --module-dir /frozen/candidate/tools/ht_cupy_bridge --device cuda \
  --reference /new/baseline_1 --capture-context --save-frames --output /new/candidate_1
```

按baseline_1/candidate_1/baseline_2/candidate_2/baseline_3/candidate_3交替运行；不要同时运行编译、绘图或其他本轮测量进程。最初5帧不计统计但保存；其余慢帧全部保留。CPU不绑核、不改调频/功耗/GC，线程与参数见冻结计划。参数和源码全程固定，不因失败改门槛。

`run_final_validation.py`记录最终实际命令及输入/模型窗口对照；`run_validation.py`是退出修正前的V2实验，不能把二者结果混合。`screen_root_cause.py`是基线上的GC/线程筛选反例，未采用其干预。`probe_all_frequency.py`仅额外逐帧观察系统报告，不参与最终性能门槛。

逐帧原因采样附加`--capture-reasons --parameter ht_reason_interval_s:=0.0`。普通性能对照保持默认1秒原因抽样。单格追溯见[诊断使用说明](../../real_vehicle/HT_LATENCY_DIAGNOSTICS.md)。

原始接口时钟为源时间+30ms，服务时间为真实单调墙钟；该离线模型不测真实DDS排队、ARM或车上频率，不启动驱动、控制或车辆。
