# 阶段38：全局待办与局部委派交接保持，减少目标反复切换

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261019-guide-handoff`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261019-guide-handoff)。
- 归档标签提交：[`16bdbe4cb1fddd632d061a5710c3e7b294971891`](https://github.com/CQULzz/HT_Explo/commit/16bdbe4cb1fddd632d061a5710c3e7b294971891)。
- 记录的实验候选：[`16bdbe4`](https://github.com/CQULzz/HT_Explo/tree/16bdbe4cb1fddd632d061a5710c3e7b294971891)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261019-guide-handoff)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

按全局单元任务ID及EXPLORING状态保留引导，不把退出巡游列表当作任务完成；原进展超时与硬约束保留

交替tour委派、任务真实解除、无进展超时与旧行为回退回归通过；新增逐周期任务日志

## 验证与剩余问题

完整车库600秒202.58m/5807.000m³，末分钟新增553.750m³；13项采集及4项CTest通过

对比37体积+28.4%、转向27%→20.3%、重复进入29.2%→14.7%；但低于36的7900.375m³，超时47→81、最长停车1.15→1.40s。仅单轮，整体效率/跨场景/实车仍未解决

## 报告及版本证据

- [docs/results/ht_guide_handoff_10min_2026-10-19/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_guide_handoff_10min_2026-10-19/REPORT.md)
- 原版本总表记录的控制提交：`16bdbe4cb1fddd632d061a5710c3e7b294971891`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261019-guide-handoff-garage.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261019-guide-handoff/ht-stage-20261019-guide-handoff-garage.mp4) — 8982784 bytes；`sha256:f6943e419baf3f564c016f5b37e5887a1fa0704148fae5e939d7890aba07adba`。

## 完整数据及上传回执

- [docs/experiments/publications/stage38.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage38.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
