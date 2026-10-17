# HT 多环境各10分钟录像

使用最新HT控车栈，依次运行Garage、Campus、Indoor、Forest、Tunnel。
每个环境独立启动并记录600秒，场景切换时清空建图/探索历史；上一组
退出、统计及编码完成后才启动下一组，避免同时仿真抢占资源。

相机从原生320×180改为960×540，保持15Hz；录像为960×600（底部
60像素用于状态）。H.264/yuv420p/faststart，裁去初始化并完整解码，
核验600秒、15fps，允许1帧时长误差。收到图像较慢时会重复已有帧，不会把未来画面填到
过去的时间。画面显示场景、时间、线/角速度、任务状态及地图/相机年龄。

```bash
python3 presentations/run_ht_multiscene.py --duration 600 \
  --scenarios garage campus indoor forest tunnel \
  --encoder /path/to/ffmpeg
```

默认在`presentations/scheduled_results/ht_multiscene_10min_<时间>`保存：

- `REPORT.md`：每组状态、实际里程、近似观测体积、视频链接；
- `videos.m3u`：已经完成的视频播放列表；
- `overview.jpg`：各场景前/中/后期实拍预览；
- 每个场景的`camera_h264.mp4`、`suite_validation.json`、CSV、曲线、
  地图快照、MCAP证据、CPU/GPU/内存与消息新鲜度记录。

`latest_multiscene.json`记录任务根目录，`suite.json`持续更新。相机图像
不用于HT规划，因此提高画质不改变地图或控制接口，但会增加录像负载。
五组使用对应场景的TARE参数，速度上限均0.5m/s；车库沿用配对起点，
其余使用各场景原生起点。跨场景体积不作为算法优劣排名。

10分钟记录完成不等于探索完成，也不能证明更长时间或实车稳定。
若出现BLOCKED或中途错误，保留记录并在报告中明确标注。

结果归档使用以下命令（默认必须收齐五环境，逐段视频已解码通过）：

```bash
python3 presentations/archive_ht_multiscene.py /path/to/completed_suite \
  --output docs/results/my_multiscene_results
# 单环境补测必须明确指定预期场景，不能假冒五组完成
python3 presentations/archive_ht_multiscene.py /path/to/indoor_followup \
  --scenarios indoor --output docs/results/my_indoor_followup
```

归档包括录像、曲线、源时间戳检查点、配置原件和哈希、末段原始HT及足迹硬门槛图。
[2026-10-17实际五环境结果](../results/ht_multiscene_10min_2026-10-17/REPORT.md)
保留室内和隧道的失败，记录完整与导航成功分别判断。
