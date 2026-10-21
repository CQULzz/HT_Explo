# 阶段25：连续位姿几何检查：旧反例修正，仍有HT未知停滞

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261018-continuous-geometry`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-continuous-geometry)。
- 归档标签提交：[`43069a7b11b8028b53f6eae0d6bdc53c13e8affd`](https://github.com/CQULzz/HT_Explo/commit/43069a7b11b8028b53f6eae0d6bdc53c13e8affd)。
- 记录的实验候选：[`43069a7`](https://github.com/CQULzz/HT_Explo/tree/43069a7b11b8028b53f6eae0d6bdc53c13e8affd)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-continuous-geometry)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

实际位置查询实测碰撞点云；保留安全距离并加栅格余量；修正碰撞显示与计时

不再继承邻覆盖视点碰撞标记，真正碰撞根状态仍拒绝

## 验证与剩余问题

390核心、25ROS、11执行器及真实几何回归通过；完整600秒65.80m、1959.875m³，25次晚拒绝均发零

264秒后HT未知导致长期停车；一处融合后有限高度拒绝产生全窗口未知；图龄长尾和覆盖统计耗时仍存在

## 报告及版本证据

- [docs/results/ht_continuous_geometry_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_continuous_geometry_10min_2026-10-18/REPORT.md)
- 原版本总表记录的控制提交：`43069a7b11b8028b53f6eae0d6bdc53c13e8affd`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261018-continuous-geometry-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-continuous-geometry/ht-stage-20261018-continuous-geometry-indoor.mp4) — 6539066 bytes；`sha256:106cfd58e3a723fb62cf31b55feda085351d8d19ec39ebcd083b8d8b10c76c22`。

## 完整数据及上传回执

- [docs/experiments/publications/stage25.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage25.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
