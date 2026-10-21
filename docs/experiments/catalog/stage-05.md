# 阶段05：起点先验、降级预算与返航状态

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20260922-return`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20260922-return)。
- 归档标签提交：[`29f80bc76789a7075f4dfb987cb2e51bfbb56add`](https://github.com/CQULzz/HT_Explo/commit/29f80bc76789a7075f4dfb987cb2e51bfbb56add)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20260922-return)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

固定起点并限制缺测先验，累计未知降级预算；补任务状态、到家停车确认、返航拼接和单调检查点。

区分探索结束与真正返航完成；地图故障时停车，恢复后继续；提供可复用回归验证。

## 验证与剩余问题

限定山地小场景中一组基线/HT均到家完成；另有地图暂停6秒恢复检查。

小样本且HT运行有约52秒几何降级，不能称为纯HT或全域完成；仍是软风险代价与CMU控制器，非当前XYθ。

## 报告及版本证据

- [docs/HT_TARE_REMEDIATION_IMPLEMENTED.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/HT_TARE_REMEDIATION_IMPLEMENTED.md)
- [experiments/results/remediation_stock_20260922/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/experiments/results/remediation_stock_20260922/REPORT.md)
- [experiments/results/remediation_map_outage_20260922/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/experiments/results/remediation_map_outage_20260922/REPORT.md)
- 原版本总表记录的控制提交：`b8477101476bfbff09c97f22190fa0c7c40ee54c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

没有对应上传回执；不能据此宣称存在完整录包。

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
