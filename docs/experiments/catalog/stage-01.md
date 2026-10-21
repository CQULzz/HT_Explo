# 阶段01：八方向HT软代价初版

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20260914-ht8dir`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20260914-ht8dir)。
- 归档标签提交：[`46f9642221ff7e251e601818a45fe041831b928c`](https://github.com/CQULzz/HT_Explo/commit/46f9642221ff7e251e601818a45fe041831b928c)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20260914-ht8dir)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

将HT八方向概率接入有向边代价、最短路与局部TSP；保留TARE覆盖采样和全局引导。

按边的移动方向计算长度、风险和未知长度代价，输出经检查的短航点。

## 验证与剩余问题

初始归档以本地核心检查为主；后续Jazzy构建发现包识别、OR-Tools和起点停滞问题。

低概率仍可能被选中；没有真实XYθ状态搜索、车体朝向连续性或真实HT闭环部署证明。

## 报告及版本证据

- [release_manifest.json](https://github.com/CQULzz/HT_Explo/blob/main/release_manifest.json)
- [VALIDATION.md](https://github.com/CQULzz/HT_Explo/blob/main/VALIDATION.md)
- 原版本总表记录的控制提交：`46f9642221ff7e251e601818a45fe041831b928c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

没有对应上传回执；不能据此宣称存在完整录包。

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
