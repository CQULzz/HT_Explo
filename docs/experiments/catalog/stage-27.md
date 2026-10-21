# 阶段27：等价连续碰撞查询提速：仍因执行进入几何边界停滞

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261018-geometry-index`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-geometry-index)。
- 归档标签提交：[`4721764fa77eb634f4a0ba50b1381a05b3790195`](https://github.com/CQULzz/HT_Explo/commit/4721764fa77eb634f4a0ba50b1381a05b3790195)。
- 记录的实验候选：[`4721764`](https://github.com/CQULzz/HT_Explo/tree/4721764fa77eb634f4a0ba50b1381a05b3790195)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-geometry-index)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

固定高度XY索引与边界3D回退；逐搜索终止原因、可靠几何录包

6561真实查询输出一致/微基准3.68倍；800边界及搜索退出回归

## 验证与剩余问题

完整600秒41.9m/815.625m³；最终BLOCKED；最后60秒480次几何INVALID_START；59份模型上下文一致

比上一轮里程与体积退步；136.5s后停滞；规划几何/HT与执行只检查HT不一致；贴边余量不足、图龄长尾

## 报告及版本证据

- [docs/results/ht_geometry_index_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_geometry_index_10min_2026-10-18/REPORT.md)
- 原版本总表记录的控制提交：`4721764fa77eb634f4a0ba50b1381a05b3790195`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261018-geometry-index-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-geometry-index/ht-stage-20261018-geometry-index-indoor.mp4) — 4838161 bytes；`sha256:08eec3542748319b519144e2fe0a2d80bf1f89fc1dba97e0c74eed453aa4717f`。

## 完整数据及上传回执

- [docs/experiments/publications/stage27.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage27.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
