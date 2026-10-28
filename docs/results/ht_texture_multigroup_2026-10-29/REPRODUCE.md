# 复现说明

本轮已提供全部832对INPUTS.npz、SAMPLES.json、协议及输出，无需重新播放机器人或仿真。

1. 解压selected_data ZIP与contexts ZIP到同一研究目录。后者包含四个数据版本的362张精确输入上下文和对应RESULTS.json。
2. 只复算神经试验时，另建空目录，将infer.py、analyze.py、matched_control.py、plot.py及必要的输入/协议/样本清单复制进去；不要直接覆盖发布的数据。infer.py读取INPUTS.npz、SAMPLES.json、SELECTION_FROZEN.json、PROTOCOL.json、DATASETS.json。matched_control.py还需要PROTOCOL_AMENDMENT_01.json；先执行infer，再analyze，再matched_control，最后plot。
3. 使用PyTorch2.11.0+cu128、NumPy1.26.4环境；GPU为RTX5060Ti，TF32禁用。图表还需要Matplotlib/SciPy/Pillow。原绘图在Matplotlib3.6.3验证。
4. 脚本中R变量是HT源码根目录，本机为/home/lzz/my test/HT_Explo-real-review-20261028；异机请调整R或相应模块路径。runtime_model中提供同SHA的model.py和权重作核对，勿更换训练参数。
5. 如需重新抽样，使用RESTORE_DATASETS.json的相对路径建立DATASETS.json，各contexts/results字段加解压目录前缀；在另一个空工作目录放入prepare.py、PROTOCOL.json、修正路径的DATASETS.json，运行prepare。全上下文已包含，不需要ROS。新生成SELECTION/INPUTS应与发布SHA一致。
6. 如需重做上下文捕获而非仅神经试验，还需恢复此前Release的native_stream及原始录包，并source独立CuPy/ROS环境。capture_stationary.py内的路径需对应实际恢复位置；只会离线调用HT，不运行控制器。

主要复现指标：原图→patch最大概率差3.64e-6；输入重建2.21e-6；新模型实例重复8.34e-7。误差容差1e-4。

图表轮播视频仅为诊断图片播放，不是车辆或RViz录像。原始记录和失败绘图日志均保留。
