# 阶段04：真实HT推理与通过性评测工具

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20260921-real-ht`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20260921-real-ht)。
- 归档标签提交：[`4315dd9deaed24245d6fbdd3c8ebe8726f74b476`](https://github.com/CQULzz/HT_Explo/commit/4315dd9deaed24245d6fbdd3c8ebe8726f74b476)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20260921-real-ht)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

增加固定通过性评测、数据/模型审计、配对推理和真实学生模型山地闭环。

将真实八方向预测接入雷达观测高程，区分模型误放/误拒、路线选择和实际车辆通过。

## 验证与剩余问题

山地各2轮60秒中，HT平均新增表面体素550.5，基线606.5，未显示探索提升；暴露HT提前返回造成返航遗漏。

传感器适配且地形来自训练域；旧软代价、近地盲区和返航问题仍在，不能以离线准确率代替闭环效果。

## 报告及版本证据

- [experiments/traversability/README.md](https://github.com/CQULzz/HT_Explo/blob/main/experiments/traversability/README.md)
- [experiments/traversability/evidence/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/experiments/traversability/evidence/REPORT.md)
- [experiments/results/mountain_live_20260921/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/experiments/results/mountain_live_20260921/REPORT.md)
- 原版本总表记录的控制提交：`df8815c61a22a76d0314d372e4c280ac233ee23c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

没有对应上传回执；不能据此宣称存在完整录包。

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
