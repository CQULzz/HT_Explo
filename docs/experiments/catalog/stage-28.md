# 阶段28：执行几何与跟踪余量：600秒内部完成并返航，覆盖待核验

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261018-execution-geometry`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-execution-geometry)。
- 归档标签提交：[`65efef749493fdfac0960f7b98013ec666d4efff`](https://github.com/CQULzz/HT_Explo/commit/65efef749493fdfac0960f7b98013ec666d4efff)。
- 记录的实验候选：[`65efef7`](https://github.com/CQULzz/HT_Explo/tree/65efef749493fdfac0960f7b98013ec666d4efff)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-execution-geometry)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

执行端检查同一实测几何，平移预留0.12m跟踪余量，显式共享场景安全参数

几何缺失/过期/碰撞实际发零并反馈对应计划；HT保持硬约束

## 验证与剩余问题

全部CTest及16项控制器ROS回归通过；600秒117.66m/2292.75m³；352.425秒返航完成；307份几何样本无半径重叠；58份上下文一致

内部完成不证明全场景覆盖；体积低于阶段23约27.7%；图龄最大3.563s；几何拦截闭环未触发，多环境/重复/动力学仍待测

## 报告及版本证据

- [docs/results/ht_execution_geometry_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_execution_geometry_10min_2026-10-18/REPORT.md)
- 原版本总表记录的控制提交：`65efef749493fdfac0960f7b98013ec666d4efff`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261018-execution-geometry-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-execution-geometry/ht-stage-20261018-execution-geometry-indoor.mp4) — 8952464 bytes；`sha256:2de04936ffacb7b1c77b744ec94ae46ddb066c9d432757d5caf059cb73c3c0d7`。

## 完整数据及上传回执

- [docs/experiments/publications/stage28.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage28.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
