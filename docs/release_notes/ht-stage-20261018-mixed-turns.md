# 阶段22｜混合转角与旋转跟踪：室内仍停滞

实测代码`12d85d871ce84bcab1191a20bbea6e1748449cd5`，结果归档`68746de`。此标签固定候选代码，不表示稳定验收。

## 改了什么

32航向保留11.25°与22.5°两种原地转向；跟踪器锁定旋转终点，完成旋转并降至角速度阈值后才平移。

## 实现了什么功能

保留细转向逃离路线与较快粗转向，执行器完成旋转后才切换平移。

## 实验与验证

390项核心、21地图/规划、10跟踪器回归通过，四个历史快照均参与；完整600秒记录；17.82m、778.000m³，最终BLOCKED，约74秒后无持续推进。

[通俗报告](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_mixed_turns_10min_2026-10-18/REPORT.md) · [同条件对比图](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_mixed_turns_10min_2026-10-18/comparison/comparison.png) · [视频](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-mixed-turns/ht-stage-20261018-mixed-turns-indoor.mp4)

本页附件提供完整本轮记录目录的raw.tar、精选结果results.tar、逐文件SHA256与录像。录制范围为全频已发布HT/控制/位姿/状态、按源秒抽样激光和周期地图快照，不能表述为全部原始激光/CuPy输入。tar分卷时先按part编号合并再解包。本地原件与失败记录均保留。

## 存在什么问题

比单转角6.64m有所推进，但未解决起点/出口拒绝；同一停止快照54次查询全部无路，不能称为稳定通过。

后续stage23对接口语义做独立修改，这一版作为失败对照保留。
