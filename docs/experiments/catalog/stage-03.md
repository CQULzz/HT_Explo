# 阶段03：旧有向图拐角修复与重复实验

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20260920-corner`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20260920-corner)。
- 归档标签提交：[`a6c015a3a3f703d0b0acb880ed0230e08d49f9bd`](https://github.com/CQULzz/HT_Explo/commit/a6c015a3a3f703d0b0acb880ed0230e08d49f9bd)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20260920-corner)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

增加gridEdgeSupported和共用连通检查，拒绝切角；保留修复前失败轮并归档复测。

修复旧图允许而执行端拒绝的特定对角边，具备重复运行、统计及绘图工具。

## 验证与剩余问题

修复后3轮各300秒未见原219秒持续停滞；52项核心、9项ROS、3项统计检查通过。

HT为80×80米、0.5米栅格、八方向全0.9的合成输入；不是学习模型收益，9轮均未完成全域探索。

## 报告及版本证据

- [EXPERIMENT_REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/EXPERIMENT_REPORT.md)
- [experiments/results/garage_corner_fix_20260920/README.md](https://github.com/CQULzz/HT_Explo/blob/main/experiments/results/garage_corner_fix_20260920/README.md)
- 原版本总表记录的控制提交：`df8815c61a22a76d0314d372e4c280ac233ee23c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

没有对应上传回执；不能据此宣称存在完整录包。

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
