# 阶段23：HT配置得分与物理障碍分层：恢复推进，仍有短停

[返回总索引](INDEX.md)

- 阶段标签：[`ht-stage-20261018-configuration-gate`](https://github.com/CQULzz/HT_Explo/tree/ht-stage-20261018-configuration-gate)。
- 归档标签提交：[`149566de09c48a528140b6ec950c08c5fa29539c`](https://github.com/CQULzz/HT_Explo/commit/149566de09c48a528140b6ec950c08c5fa29539c)。
- 记录的实验候选：[`149566d`](https://github.com/CQULzz/HT_Explo/tree/149566de09c48a528140b6ec950c08c5fa29539c)
- [GitHub Release：完整数据及附件](https://github.com/CQULzz/HT_Explo/releases/tag/ht-stage-20261018-configuration-gate)。

归档提交、实验设施提交与实际导航代码可能不同。运行时源码快照、补丁、参数及二进制哈希以原实验清单为准；视频不是另一个代码版本的验收证据。

## 改动及实现

新增独立ht_obstacle层；HT参考位置/车头方向得分按0.5硬门槛查询，实测障碍和缺测仍保留0.6m足迹检查；修正启动先验混用观测支持的额外漏洞。

新增独立ht_obstacle层；HT参考位置/车头方向得分按0.5硬门槛查询，实测障碍和缺测仍保留0.6m足迹检查；修正启动先验混用观测支持的额外漏洞。

## 验证与剩余问题

390项核心、25地图/规划、11跟踪器回归及5实际快照通过；室内完整600秒134.00m、3170.500m³，BLOCKED抽样7.8%，212次晚拦截均发零。

最终约2秒BLOCKED，未观察其未来恢复；最长全零6.20s，HT地图年龄最大约5.996s，规划P95 1.616s。无探索完成或多场景/实车稳定性结论。

## 报告及版本证据

- [docs/results/ht_configuration_gate_10min_2026-10-18/REPORT.md](https://github.com/CQULzz/HT_Explo/blob/main/docs/results/ht_configuration_gate_10min_2026-10-18/REPORT.md)
- 原版本总表记录的控制提交：`149566de09c48a528140b6ec950c08c5fa29539c`。这是历史字段，不能替代运行时快照/补丁核对。

## 可直接下载的视频

- [ht-stage-20261018-configuration-gate-indoor.mp4](https://github.com/CQULzz/HT_Explo/releases/download/ht-stage-20261018-configuration-gate/ht-stage-20261018-configuration-gate-indoor.mp4) — 13241032 bytes；`sha256:6e2424a5863c6c1d93e1ad40fdf202c9de936db5350bf27afcdad2d5999b78fa`。

## 完整数据及上传回执

- [docs/experiments/publications/stage23.json](https://github.com/CQULzz/HT_Explo/blob/main/docs/experiments/publications/stage23.json)

完整附件名、大小、SHA256、下载URL见[index.json](index.json)中本阶段的`release_assets`；历史分片按`content_key`分组，不能把同一Release内不同目录的分片混合。

## 早期历史目录与包内视频

以下为研究阶段关联，不保证阶段标签等于实际测量源码。没有提交记录的保持待确认；下载匹配的归档包后按包内路径查找视频。

无早期历史目录关联。
