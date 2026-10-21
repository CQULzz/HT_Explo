# 阶段40：原TARE覆盖/TSP访问顺序 + HT航点XYθ路由

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261020-tare-waypoint`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261020-tare-waypoint)。
- 归档标签提交：[`42966cb22b0f719df035391f3850b9a654f161e1`](https://github.com/CQULzz/HT_Explo/commit/42966cb22b0f719df035391f3850b9a654f161e1)。
- 记录的实验候选：[`42966cb`](https://github.com/CQULzz/HT_Explo/tree/42966cb22b0f719df035391f3850b9a654f161e1)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261020-tare-waypoint)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

六个核心函数体与原ROS2基线一致，保留多视点TSP与原航点延伸；HT只规划当前航点/原路线前缀

同源历史高程供视点高度；隔离模拟器地形；记录TSP顺序、原航点、局部前缀与实际XYθ路线

## 验证与剩余问题

完整车库600秒192.93m/8467.000m³；13项采集、4项CTest；接口检查True

XYθ搜索超时42次；最长完全停车0.75s，末60秒新增731.724m³/移动20.80m；末尾EXPLORING。 单次运行；未补齐同运动约束新原版配对；不保证全局SE2可达或实车安全 构造回归另有失败：HT删点后原BFS仍标记另一侧连通/候选，但实际最短路为空。近家rush-home也存在前视无输出时被包装层错误拦住的源条件反例；本轮没有触发返航。

## 报告及版本证据

- [docs/results/ht_tare_waypoint_10min_2026-10-20/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_tare_waypoint_10min_2026-10-20/REPORT.md)
- 原版本总表记录的控制提交：`42966cb22b0f719df035391f3850b9a654f161e1`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261020-tare-waypoint-garage.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261020-tare-waypoint/ht-stage-20261020-tare-waypoint-garage.mp4) — 10176893 bytes；`sha256:515e067a8f14a208e498fa23e508d6da970b32e99e0237e2ad152bd357660c4f`。

## 完整数据及上传回执

- [docs/experiments/publications/stage40.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage40.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
