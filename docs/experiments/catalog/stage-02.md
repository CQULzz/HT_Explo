# 阶段02：Jazzy编译与起点停滞修复

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20260915-jazzy`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20260915-jazzy)。
- 归档标签提交：[`c4b7a41d3ae3466c8b5eb043c8f1f3f81b3c9e8d`](https://github.com/CQULzz/HT_Explo/commit/c4b7a41d3ae3466c8b5eb043c8f1f3f81b3c9e8d)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20260915-jazzy)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

修复包识别、Eigen/GridMap与OR-Tools依赖；跳过过近的起始锚点，补输入校验及故障注入工具。

可在CMU Garage闭环移动，异常地图输入能停车并恢复。

## 验证与剩余问题

约135秒故障注入试跑行驶40.56米；41项核心、9项ROS检查通过。

使用合成八方向地图，未运行真实HT网络；仍是软代价与旧控制链路，未完成全域探索。

## 报告及版本证据

- [VALIDATION.md](https://github.com/CQULzz/HT_Explo/blob/main/VALIDATION.md)
- 原版本总表记录的控制提交：`c4b7a41d3ae3466c8b5eb043c8f1f3f81b3c9e8d`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

没有对应上传回执；不能据此宣称存在完整录包。

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
