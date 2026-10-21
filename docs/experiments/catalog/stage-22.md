# 阶段22：混合转角与旋转跟踪：室内仍停滞

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261018-mixed-turns`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-mixed-turns)。
- 归档标签提交：[`12d85d871ce84bcab1191a20bbea6e1748449cd5`](https://github.com/CQULzz/HT_Explo/commit/12d85d871ce84bcab1191a20bbea6e1748449cd5)。
- 记录的实验候选：[`12d85d8`](https://github.com/CQULzz/HT_Explo/tree/12d85d871ce84bcab1191a20bbea6e1748449cd5)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-mixed-turns)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

32航向保留11.25°与22.5°两种原地转向；跟踪器锁定旋转终点，完成旋转并降至角速度阈值后才平移。

32航向保留11.25°与22.5°两种原地转向；跟踪器锁定旋转终点，完成旋转并降至角速度阈值后才平移。

## 验证与剩余问题

390项核心、21地图/规划、10跟踪器回归通过，四个历史快照均参与；完整600秒记录；17.82m、778.000m³，最终BLOCKED，约74秒后无持续推进。

比单转角6.64m有所推进，但未解决起点/出口拒绝；同一停止快照54次查询全部无路，不能称为稳定通过。

## 报告及版本证据

- [docs/results/ht_mixed_turns_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_mixed_turns_10min_2026-10-18/REPORT.md)
- 原版本总表记录的控制提交：`12d85d871ce84bcab1191a20bbea6e1748449cd5`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261018-mixed-turns-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-mixed-turns/ht-stage-20261018-mixed-turns-indoor.mp4) — 3566350 bytes；`sha256:51584f325f94e34c6e9988e8b1952086ca041175c9d86d17c270bcead5bc0325`。

## 完整数据及上传回执

- [docs/experiments/publications/stage22.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage22.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
