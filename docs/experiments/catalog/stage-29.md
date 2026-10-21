# 阶段29：逐单元审计：正收益任务未登记/移出邻域被核销

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261018-cell-audit`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-cell-audit)。
- 归档标签提交：[`b6010156cc26431cc23bac33ac543982f7d5e4c1`](https://github.com/CQULzz/HT_Explo/commit/b6010156cc26431cc23bac33ac543982f7d5e4c1)。
- 记录的实验候选：[`b601015`](https://github.com/CQULzz/HT_Explo/tree/b6010156cc26431cc23bac33ac543982f7d5e4c1)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-cell-audit)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

覆盖状态分支记录，修正vector遍历删除的迭代器失效

重建单元状态与内部完成触发的时间线；保存实际C++两个最小失败复现

## 验证与剩余问题

完整600秒133.17m/2025.125m³，517.244秒内部返航完成；(24,0)正收益移出邻域核销紧接触发结束；13项采集通过

正收益任务遗漏规则尚待修正；体积比阶段28少11.7%；图龄4.096s，16次路径不连续，多环境/真值覆盖未验收

## 报告及版本证据

- [docs/results/ht_cell_audit_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_cell_audit_10min_2026-10-18/REPORT.md)
- 原版本总表记录的控制提交：`b6010156cc26431cc23bac33ac543982f7d5e4c1`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261018-cell-audit-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-cell-audit/ht-stage-20261018-cell-audit-indoor.mp4) — 10644284 bytes；`sha256:c25e29203e6e031ef0af647ee02294a6d121ab11692fa97ef26884d63f68b8c2`。

## 完整数据及上传回执

- [docs/experiments/publications/stage29.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage29.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
