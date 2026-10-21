# 阶段47：原TARE与最新HT同运动上限室内对照

## 改了什么

增加独立对照设施，HT导航保持`07c1abd334f83cb8d602e2234134b4286862c916`，72项运行文件/二进制未改；原TARE ROS2适配代码保持`b6760adb4280b379567c76f4e684ce628e28ef71`。冻结设施提交`1ded85a7b66ad9506bb26b7abe4e1c1def946648`。

## 实现了什么功能

同一室内场景/原生起点，各实际600秒；原CMU参数和透明限幅组件对齐前进/倒车/角速度及常规加速度。保留限幅前后指令、有效参数、视频、MCAP和共同源秒观测指标。原TARE规划/TSP、地形和自身跟踪策略保留，HT导航本轮不改。

## 实验与验证

- 原TARE同运动上限：600秒、188.19m、4116.125m³，末任务EXPLORING，最长完全停车1.600s。
- 最新HT：600秒、190.53m、5027.125m³，末任务EXPLORING，最长完全停车6.400s。

[两组视频、共同指标曲线、轨迹、参数和实际指令审计](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_tare_matched_10min_2026-10-21/REPORT.md)。采集总体状态COMPLETED_WITH_ISSUES。运动限幅四项回归、原TARE六函数SHA通过；采集/视频/冻结检查见逐组JSON。完整已录数据以stage47.json远端大小/SHA回执为准。

## 存在什么问题

- 原TARE组CMU localPlanner/pathFollower在600秒采集结束、收到SIGINT后退出异常，完整指标保留但退出检查失败；整体COMPLETED_WITH_ISSUES，发布不标全项通过。
- 各系统只有一次独立运行、固定测量顺序，不代表统计显著优越，也不是HT单模块消融。
- 对齐运动包络后的原TARE并非CMU默认高速控制链；两个跟踪器、地形与几何规则仍不同。
- 原TARE视点网格50×50/0.6m，HT为100×100/0.3m，名义范围相同但网格数量不同；完整参数差异已记录。
- 观测自由体积是源秒抽样射线体素并集近似，不是覆盖真值；不是全频原始传感器无损录制。
- 本轮不代表森林/隧道问题已解决，也没有实车验证。

[资源图复核版报告与批次CSV](https://github.com/CQULzz/HT_Explo/blob/codex/ht8dir-v1/docs/results/ht_tare_matched_10min_2026-10-21_review/REPORT.md)：修正少量跨5秒分桶造成的CPU/RSS向下尖点，原始数据与封存报告保持不变；比较指标没有改变。
