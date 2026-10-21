# 阶段07：Campus地图传输与前瞻航点

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261011-campus`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261011-campus)。
- 归档标签提交：[`087c42d45801a34a355cac936488efe19141768d`](https://github.com/CQULzz/HT_Explo/commit/087c42d45801a34a355cac936488efe19141768d)。
- 记录的实验候选：现代发布回执无记录；查下方原始清单，待确认。
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261011-campus)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

HT地图改可靠订阅；只沿已检查且近乎直线的路段跨过近航点；补倒车和探索局限审计。

改善大地图送达和CMU路径末端频繁减速，旧控制器继续实际控车。

## 验证与剩余问题

15分钟367.85米、该轮HT_MAP_STALE为0；另5分钟对照零线速占比11.2%→5.8%。

长测倒车占48.4%，另一短测79.3%；旧长测缺XY轨迹/探索体积。此时没有实际XYθ闭环，不能用里程代表探索效果。

## 报告及版本证据

- [validation/results/HT_long_run_report_2026-10-11.md](https://github.com/CQULzz/HT_Explo/blob/main/validation/results/HT_long_run_report_2026-10-11.md)
- 原版本总表记录的控制提交：`83b44a37c2e905022c1d396a738092eabdaa3aee`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

本Release没有独立视频附件；请查历史目录内的视频及原报告。

## 完整数据及上传回执

没有对应上传回执；不能据此宣称存在完整录包。

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
