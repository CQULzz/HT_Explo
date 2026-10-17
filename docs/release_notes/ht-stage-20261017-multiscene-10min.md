# 阶段18｜五环境各10分钟与15fps录像（已完成记录）

标签固定源码，验证与问题以本说明为准。C++规划仍为bd0c2c2，HT桥接仍为f1c8485。

## 改了什么

参数化仿真/规划场景，串行运行Garage、Campus、Indoor、Forest、Tunnel各600秒；原生相机960×540、15fps，裁剪初始化、编码和完整解码核验。

## 实现了什么功能

各组独立地图与进程，独立视频/数据/资源审计，完成一组退出与编码后才进入下一组；底部状态条显示时间、速度、任务和地图/相机年龄，提供播放列表和预览。

## 实验与验证

五环境均记录600秒，五段H.264完整解码及13项采集/进程验证通过；车库189.57m、校园199.76m、森林168.09m持续推进；室内3.11m与隧道26.33m持续受阻。视频599.933至600秒，允许1帧误差。

## 存在什么问题

室内0.6m候选视点漏掉窄走廊安全区域；隧道返航目标周围足迹含未知格，未到家；地图年龄仍有超过3秒的尾延迟，森林激光平均4.02Hz。10分钟独立重启测试不代表连续一小时、实车或全覆盖通过。

证据：[ht_multiscene_10min.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/experiments/ht_multiscene_10min.md) · [REPORT.md](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_multiscene_10min_2026-10-17/REPORT.md)
